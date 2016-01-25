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

FILE_WORK = 10

ERROR_ACTION = -1
OPEN_ACTION = 1
CLOSE_ACTION = 2
READ_ACTION = 3
WRITE_ACTION = 4

import os
import ctypes
import threading

import netius

from . import common

class FileThread(common.Thread):

    def execute(self, work):
        type = work[0]
        if not type == FILE_WORK: netius.NotImplemented(
            "Cannot execute type '%d'" % type
        )

        try:
            self._execute(work)
        except BaseException as exception:
            self.owner.push_event((ERROR_ACTION, exception, work[-1]))

    def open(self, path, mode, data):
        file = open(path)
        self.owner.push_event((OPEN_ACTION, file, data))

    def close(self, file, data):
        file.close()
        self.owner.push_event((CLOSE_ACTION, file, data))

    def read(self, file, count, data):
        result = file.read(count)
        self.owner.push_event((READ_ACTION, result, data))

    def write(self, file, buffer, data):
        file.write(buffer)
        self.owner.push_event((WRITE_ACTION, len(buffer), data))

    def _execute(self, work):
        action = work[1]
        if action == OPEN_ACTION: self.open(*work[2:])
        elif action == CLOSE_ACTION: self.close(*work[2:])
        elif action == READ_ACTION: self.read(*work[2:])
        elif action == WRITE_ACTION: self.read(*work[2:])
        else: netius.NotImplemented("Undefined file action '%d'" % action)

class FilePool(common.ThreadPool):

    def __init__(self, base = FileThread, count = 10):
        common.ThreadPool.__init__(self, base = base, count = count)
        self.events = []
        self.event_lock = threading.RLock()
        self._libc = None
        self._eventfd = None

    def open(self, path, mode = "r", data = None):
        work = (FILE_WORK, OPEN_ACTION, path, mode, data)
        self.push(work)

    def close(self, file, data = None):
        work = (FILE_WORK, CLOSE_ACTION, file, data)
        self.push(work)

    def read(self, file, count = -1, data = None):
        work = (FILE_WORK, READ_ACTION, file, count, data)
        self.push(work)

    def write(self, file, buffer, data = None):
        work = (FILE_WORK, WRITE_ACTION, file, buffer, data)
        self.push(work)

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
        os.write(self._eventfd.fileno(), ctypes.c_ulonglong(1))

    def denotify(self):
        if not self._eventfd: return
        os.write(self._eventfd.fileno(), ctypes.c_ulonglong(0))

    def eventfd(self, init_val = 0, flags = 0):
        if self._eventfd: return self._eventfd
        try: self._libc = self._libc or ctypes.cdll.LoadLibrary("libc.so.6")
        except: return None
        fileno = self._libc.eventfd(init_val, flags)
        self._eventfd = EventFile(fileno)
        return self._eventfd

class EventFile(object):

    def __init__(self, fileno):
        self._fileno = fileno

    def fileno(self):
        return self._fileno
