#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import time
import select

POLL_TIMEOUT = 0.25
""" The timeout to be used under the all the poll methods
this should be considered the maximum amount of time a
thread waits for a poll request """

class Poll(object):
    """
    The top level abstract implementation of a poll object
    should be used for inheritance and reference on the
    various methods that are part of the api.
    """

    def __init__(self):
        self._open = False
        self.timeout = POLL_TIMEOUT
        self.read_o = {}
        self.write_o = {}
        self.error_o = {}

    @classmethod
    def name(cls):
        name = cls.__name__
        name = name[:-4]
        name = name.lower()
        return name

    @classmethod
    def test(cls):
        return True

    def open(self, timeout = POLL_TIMEOUT):
        if self._open: return
        self._open = True
        self.timeout = timeout

        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def close(self):
        if not self._open: return
        self._open = False

        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def poll(self):
        return []

    def poll_owner(self):
        reads, writes, errors = self.poll()

        result = dict()

        for read in reads:
            base = self.read_o[read]
            value = result.get(base, None)
            if not value:
                value = ([], [], [])
                result[base] = value
            value[0].append(read)

        for write in writes:
            base = self.write_o[write]
            value = result.get(base, None)
            if not value:
                value = ([], [], [])
                result[base] = value
            value[1].append(write)

        for error in errors:
            base = self.error_o[error]
            value = result.get(base, None)
            if not value:
                value = ([], [], [])
                result[base] = value
            value[2].append(error)

        return result

    def is_open(self):
        return self._open

    def is_edge(self):
        return False

    def is_empty(self):
        return not self.read_o and not self.write_o and not self.error_o

    def sub_all(self, socket, owner = None):
        self.sub_read(socket, owner = owner)
        self.sub_write(socket, owner = owner)
        self.sub_error(socket, owner = owner)

    def unsub_all(self, socket):
        self.unsub_error(socket)
        self.unsub_write(socket)
        self.unsub_read(socket)

    def is_sub_read(self, socket):
        return socket in self.read_o

    def is_sub_write(self, socket):
        return socket in self.write_o

    def is_sub_error(self, socket):
        return socket in self.error_o

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        self.read_o[socket] = owner

    def sub_write(self, socket, owner = None):
        if socket in self.write_o: return
        self.write_o[socket] = owner

    def sub_error(self, socket, owner = None):
        if socket in self.error_o: return
        self.error_o[socket] = owner

    def unsub_read(self, socket):
        if not socket in self.read_o: return
        del self.read_o[socket]

    def unsub_write(self, socket):
        if not socket in self.write_o: return
        del self.write_o[socket]

    def unsub_error(self, socket):
        if not socket in self.error_o: return
        del self.error_o[socket]

class EpollPoll(Poll):

    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self._open = False

    @classmethod
    def test(cls):
        return hasattr(select, "epoll")

    def open(self, timeout = POLL_TIMEOUT):
        if self._open: return
        self._open = True
        self.timeout = timeout

        self.epoll = select.epoll() #@UndefinedVariable

        self.fd_m = {}

        self.read_o = {}
        self.write_o = {}
        self.error_o = {}

    def close(self):
        if not self._open: return
        self._open = False

        for fd in self.fd_m: self.epoll.unregister(fd)
        self.epoll.close()
        self.epoll = None

        self.fd_m.clear()

        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def poll(self):
        result = ([], [], [])

        events = self.epoll.poll(self.timeout)
        for fd, event in events:
            if event & select.EPOLLIN: #@UndefinedVariable
                socket = self.fd_m.get(fd, None)
                socket and result[0].append(socket)
            if event & select.EPOLLOUT: #@UndefinedVariable
                socket = self.fd_m.get(fd, None)
                socket and result[1].append(socket)
            if event & select.EPOLLERR or event & select.EPOLLHUP:  #@UndefinedVariable
                socket = self.fd_m.get(fd, None)
                socket and result[2].append(socket)

        return result

    def is_edge(self):
        return True

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        socket_fd = socket.fileno()
        self.fd_m[socket_fd] = socket
        self.read_o[socket] = owner
        self.write_o[socket] = owner
        self.error_o[socket] = owner
        self.epoll.register( #@UndefinedVariable
            socket_fd,
            select.EPOLLIN | select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP | select.EPOLLET #@UndefinedVariable
        )

    def sub_write(self, socket, owner = None):
        pass

    def sub_error(self, socket, owner = None):
        pass

    def unsub_read(self, socket):
        if not socket in self.read_o: return
        socket_fd = socket.fileno()
        self.epoll.unregister( #@UndefinedVariable
            socket_fd
        )
        del self.fd_m[socket_fd]
        del self.read_o[socket]
        del self.write_o[socket]
        del self.error_o[socket]

    def unsub_write(self, socket):
        pass

    def unsub_error(self, socket):
        pass

class KqueuePoll(Poll):

    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self._open = False

    @classmethod
    def test(cls):
        return hasattr(select, "kqueue")

    def open(self, timeout = POLL_TIMEOUT):
        if self._open: return
        self._open = True
        self.timeout = timeout
        if self.timeout < 0: self.timeout = None

        self.kqueue = select.kqueue() #@UndefinedVariable

        self.fd_m = {}

        self.read_o = {}
        self.write_o = {}
        self.error_o = {}

    def close(self):
        if not self._open: return
        self._open = False

        self.kqueue.close()
        self.kqueue = None

        self.fd_m.clear()

        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def poll(self):
        result = ([], [], [])

        events = self.kqueue.control(None, 32, self.timeout)
        for event in events:
            if event.flags & select.KQ_EV_ERROR: #@UndefinedVariable
                socket = self.fd_m.get(event.udata, None)
                socket and result[2].append(socket)
            elif event.filter == select.KQ_FILTER_READ: #@UndefinedVariable
                socket = self.fd_m.get(event.udata, None)
                index = 2 if event.flags & select.KQ_EV_EOF else 0 #@UndefinedVariable
                socket and result[index].append(socket)
            elif event.filter == select.KQ_FILTER_WRITE: #@UndefinedVariable
                socket = self.fd_m.get(event.udata, None)
                index = 2 if event.flags & select.KQ_EV_EOF else 1 #@UndefinedVariable
                socket and result[index].append(socket)

        return result

    def is_edge(self):
        return True

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        socket_fd = socket.fileno()
        self.fd_m[socket_fd] = socket
        self.read_o[socket] = owner
        self.write_o[socket] = owner
        self.error_o[socket] = owner
        event = select.kevent( #@UndefinedVariable
            socket_fd,
            filter = select.KQ_FILTER_READ, #@UndefinedVariable
            flags = select.KQ_EV_ADD | select.KQ_EV_CLEAR, #@UndefinedVariable
            udata = socket_fd
        )
        self.kqueue.control([event], 0)
        event = select.kevent( #@UndefinedVariable
            socket_fd,
            filter = select.KQ_FILTER_WRITE, #@UndefinedVariable
            flags = select.KQ_EV_ADD | select.KQ_EV_CLEAR, #@UndefinedVariable
            udata = socket_fd
        )
        self.kqueue.control([event], 0)

    def sub_write(self, socket, owner = None):
        pass

    def sub_error(self, socket, owner = None):
        pass

    def unsub_read(self, socket):
        if not socket in self.read_o: return
        socket_fd = socket.fileno()
        event = select.kevent( #@UndefinedVariable
            socket_fd,
            filter = select.KQ_FILTER_READ, #@UndefinedVariable
            flags = select.KQ_EV_DELETE #@UndefinedVariable
        )
        self.kqueue.control([event], 0)
        event = select.kevent( #@UndefinedVariable
            socket_fd,
            filter = select.KQ_FILTER_WRITE, #@UndefinedVariable
            flags = select.KQ_EV_DELETE #@UndefinedVariable
        )
        self.kqueue.control([event], 0)
        del self.fd_m[socket_fd]
        del self.read_o[socket]
        del self.write_o[socket]
        del self.error_o[socket]

    def unsub_write(self, socket):
        pass

    def unsub_error(self, socket):
        pass

class PollPoll(Poll):

    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self._open = False

    @classmethod
    def test(cls):
        return hasattr(select, "poll")

    def open(self, timeout = POLL_TIMEOUT):
        if self._open: return
        self._open = True
        self.timeout = timeout

        self._poll = select.poll() #@UndefinedVariable

        self.read_fd = {}
        self.write_fd = {}

        self.read_o = {}
        self.write_o = {}
        self.error_o = {}

    def close(self):
        if not self._open: return
        self._open = False

        for fd in self.read_fd: self._poll.unregister(fd)
        self._poll = None

        self.read_fd.clear()
        self.write_fd.clear()

        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def poll(self):
        result = ([], [], [])

        events = self._poll.poll(self.timeout * 1000)
        for fd, event in events:
            if event & select.POLLIN: #@UndefinedVariable
                socket = self.read_fd.get(fd, None)
                socket and result[0].append(socket)
            if event & select.POLLOUT: #@UndefinedVariable
                socket = self.write_fd.get(fd, None)
                socket and result[1].append(socket)
            if event & select.POLLERR or event & select.POLLHUP: #@UndefinedVariable
                socket = self.read_fd.get(fd, None)
                socket and result[2].append(socket)

        return result

    def is_edge(self):
        return False

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        socket_fd = socket.fileno()
        self.read_fd[socket_fd] = socket
        self.read_o[socket] = owner
        self._poll.register( #@UndefinedVariable
            socket_fd,
            select.POLLIN #@UndefinedVariable
        )

    def sub_write(self, socket, owner = None):
        if socket in self.write_o: return
        socket_fd = socket.fileno()
        self.write_fd[socket_fd] = socket
        self.write_o[socket] = owner
        self._poll.modify( #@UndefinedVariable
            socket_fd,
            select.POLLIN | select.POLLOUT #@UndefinedVariable
        )

    def sub_error(self, socket, owner = None):
        if socket in self.error_o: return
        self.error_o[socket] = owner

    def unsub_read(self, socket):
        if not socket in self.read_o: return
        socket_fd = socket.fileno()
        self._poll.unregister( #@UndefinedVariable
            socket_fd
        )
        del self.read_fd[socket_fd]
        del self.read_o[socket]

    def unsub_write(self, socket):
        if not socket in self.write_o: return
        socket_fd = socket.fileno()
        self._poll.modify( #@UndefinedVariable
            socket_fd,
            select.POLLIN #@UndefinedVariable
        )
        del self.write_fd[socket_fd]
        del self.write_o[socket]

    def unsub_error(self, socket):
        if not socket in self.error_o: return
        del self.error_o[socket]

class SelectPoll(Poll):

    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self._open = False

    def open(self, timeout = POLL_TIMEOUT):
        if self._open: return
        self._open = True
        self.timeout = timeout
        if self.timeout < 0: self.timeout = None

        self.read_l = []
        self.write_l = []
        self.error_l = []

        self.read_o = {}
        self.write_o = {}
        self.error_o = {}

    def close(self):
        if not self._open: return
        self._open = False

        # removes the contents of all of the loop related structures
        # so that no extra selection operations are issued
        del self.read_l[:]
        del self.write_l[:]
        del self.error_l[:]

        # removes the complete set of elements from the map that associated
        # a socket with the proper owner
        self.read_o.clear()
        self.write_o.clear()
        self.error_o.clear()

    def poll(self):
        # "calculates" the amount of time the select method is going
        # to be sleeping for empty polls based on the fact that the
        # current timeout value may be unset
        sleep_timeout = self.timeout or POLL_TIMEOUT

        # verifies if the current selection list is empty
        # in case it's sleeps for a while and then continues
        # the loop (this avoids error in empty selection)
        is_empty = self.is_empty()
        if is_empty: time.sleep(sleep_timeout); return ([], [], [])

        # runs the proper select statement waiting for the desired
        # amount of time as timeout at the end a tuple with three
        # list for the different operations should be returned
        return select.select(
            self.read_l,
            self.write_l,
            self.error_l,
            self.timeout
        )

    def is_edge(self):
        return False

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        self.read_o[socket] = owner
        self.read_l.append(socket)

    def sub_write(self, socket, owner = None):
        if socket in self.write_o: return
        self.write_o[socket] = owner
        self.write_l.append(socket)

    def sub_error(self, socket, owner = None):
        if socket in self.error_o: return
        self.error_o[socket] = owner
        self.error_l.append(socket)

    def unsub_read(self, socket):
        if not socket in self.read_o: return
        self.read_l.remove(socket)
        del self.read_o[socket]

    def unsub_write(self, socket):
        if not socket in self.write_o: return
        self.write_l.remove(socket)
        del self.write_o[socket]

    def unsub_error(self, socket):
        if not socket in self.error_o: return
        self.error_l.remove(socket)
        del self.error_o[socket]
