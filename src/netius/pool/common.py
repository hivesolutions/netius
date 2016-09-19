#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Netius System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import ctypes
import socket
import threading

import netius

CALLABLE_WORK = 1

class Thread(threading.Thread):

    def __init__(self, identifier, owner = None, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.identifier = identifier
        self.owner = owner
        self._run = False

    @classmethod
    def available(self):
        return True

    def stop(self):
        self._run = False

    def run(self):
        threading.Thread.run(self)
        self._run = True
        while self._run: self.tick()

    def tick(self):
        self.owner.condition.acquire()
        while not self.owner.peek() and self._run:
            self.owner.condition.wait()
        try:
            if not self._run: return
            work = self.owner.pop()
        finally:
            self.owner.condition.release()
        self.execute(work)

    def execute(self, work):
        type = work[0]
        if type == CALLABLE_WORK: work[1]()
        else: raise netius.NotImplemented("Cannot execute type '%d'" % type)

class ThreadPool(object):

    def __init__(self, base = Thread, count = 30):
        self.base = base
        self.count = count
        self.instances = []
        self.queue = []
        self.condition = threading.Condition()
        self._built = False

    def start(self):
        self.build()
        for instance in self.instances:
            instance.start()

    def stop(self, join = True):
        for instance in self.instances: instance.stop()
        self.condition.acquire()
        try: self.condition.notify_all()
        finally: self.condition.release()
        if not join: return
        for instance in self.instances: instance.join()

    def build(self):
        if self._built: return
        for index in range(self.count):
            instance = self.base(index, owner = self)
            self.instances.append(instance)
        self._built = True

    def peek(self):
        if not self.queue: return None
        return self.queue[0]

    def pop(self, lock = True):
        lock and self.condition.acquire()
        try: value = self.queue.pop(0)
        finally: lock and self.condition.release()
        return value

    def push(self, work, lock = True):
        lock and self.condition.acquire()
        try:
            value = self.queue.append(work)
            self.condition.notify()
        finally:
            lock and self.condition.release()
        return value

    def push_callable(self, callable):
        work = (CALLABLE_WORK, callable)
        self.push(work)

class EventPool(ThreadPool):

    def __init__(self, base = Thread, count = 30):
        ThreadPool.__init__(self, base = base, count = count)
        self.events = []
        self.event_lock = threading.RLock()
        self._eventfd = None

    def stop(self, join = True):
        ThreadPool.stop(self, join = join)
        if self._eventfd: self._eventfd.close()

    def push_event(self, event):
        self.event_lock.acquire()
        try: self.events.append(event)
        finally: self.event_lock.release()
        self.notify()

    def pop_event(self):
        self.event_lock.acquire()
        try: event = self.events.pop(0)
        finally: self.event_lock.release()
        return event

    def pop_all(self, denotify = False):
        self.event_lock.acquire()
        try:
            events = list(self.events)
            del self.events[:]
            if events and denotify: self.denotify()
        finally:
            self.event_lock.release()
        return events

    def notify(self):
        if not self._eventfd: return
        self._eventfd.notify()

    def denotify(self):
        if not self._eventfd: return
        self._eventfd.denotify()

    def eventfd(self):
        if self._eventfd: return self._eventfd
        if UnixEventFile.available():
            self._eventfd = UnixEventFile()
        elif PipeEventFile.available():
            self._eventfd = PipeEventFile()
        else:
            self._eventfd = SocketEventFile()
        return self._eventfd

class EventFile(object):

    def __init__(self, *args, **kwargs):
        self._rfileno = None
        self._wfileno = None
        self.closed = False

    def close(self):
        self.closed = True

    def fileno(self):
        return self.rfileno()

    def rfileno(self):
        return self._rfileno

    def wfileno(self):
        return self._wfileno

    def notify(self):
        raise netius.NotImplemented("Missing implementation")

    def denotify(self):
        raise netius.NotImplemented("Missing implementation")

class UnixEventFile(EventFile):

    _LIBC = None

    def __init__(self, *args, **kwargs):
        EventFile.__init__(self, *args, **kwargs)
        cls = self.__class__
        init_val = kwargs.get("init_val", 0)
        flags = kwargs.get("flags", 0)
        libc = cls.libc()
        self._rfileno = libc.eventfd(init_val, flags)
        self._wfileno = self._rfileno

    @classmethod
    def available(cls):
        if not os.name == "posix": return False
        return True if cls.libc() else False

    @classmethod
    def libc(cls):
        if cls._LIBC: return cls._LIBC
        try: cls._LIBC = ctypes.cdll.LoadLibrary("libc.so.6")
        except: return None
        return cls._LIBC

    def close(self):
        EventFile.close(self)
        os.close(self._wfileno)

    def notify(self):
        self._write(1)

    def denotify(self):
        self._write(0)

    def _write(self, value):
        os.write(self._wfileno, ctypes.c_ulonglong(value))

class PipeEventFile(EventFile):

    def __init__(self, *args, **kwargs):
        import fcntl
        EventFile.__init__(self, *args, **kwargs)
        self._rfileno, self._wfileno = os.pipe()
        fcntl.fcntl(self._rfileno, fcntl.F_SETFL, os.O_NONBLOCK) #@UndefinedVariable
        fcntl.fcntl(self._wfileno, fcntl.F_SETFL, os.O_NONBLOCK) #@UndefinedVariable
        self._read_file = os.fdopen(self._rfileno, "rb", 0)
        self._write_file = os.fdopen(self._wfileno, "wb", 0)

    @classmethod
    def available(cls):
        if not os.name == "posix": return False
        if not hasattr(os, "pipe"): return False
        return True

    def close(self):
        EventFile.close(self)
        self._read_file.close()
        self._write_file.close()

    def notify(self):
        self._write(b"1")

    def denotify(self):
        self._read()

    def _read(self, length = 4096):
        return self._read_file.read(length)

    def _write(self, data):
        self._write_file.write(data)

class SocketEventFile(EventFile):

    def __init__(self, *args, **kwargs):
        EventFile.__init__(self, *args, **kwargs)
        temp_socket = socket.socket()
        temp_socket.bind(("127.0.0.1", 0))
        temp_socket.listen(1)
        hostname = temp_socket.getsockname()
        self._read_socket = socket.create_connection(hostname)
        self._write_socket, _port = temp_socket.accept()
        self._rfileno = self._read_socket.fileno()
        self._wfileno = self._write_socket.fileno()
        temp_socket.close()

    def close(self):
        EventFile.close(self)
        self._read_socket.close()
        self._write_socket.close()

    def notify(self):
        self._write(b"1")

    def denotify(self):
        self._read()

    def _read(self, length = 4096):
        return self._read_socket.recv(length)

    def _write(self, data):
        self._write_socket.send(data)
