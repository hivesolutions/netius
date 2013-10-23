#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import time
import select

SELECT_TIMEOUT = 0.25
""" The timeout to be used under the select poll method
this should be considered the maximum amount of time a
thread waits for a poll request """

class Poll(object):

    def open(self):
        pass

    def close(self):
        pass

    def poll(self):
        return []

    def is_empty(self):
        return False

    def sub_all(self, socket, owner = None):
        self.sub_read(socket, owner = owner)
        self.sub_write(socket, owner = owner)
        self.sub_error(socket, owner = owner)

    def unsub_all(self, socket):
        self.unsub_read(socket)
        self.unsub_write(socket)
        self.unsub_error(socket)

    def sub_read(self, socket, owner = None):
        pass

    def sub_write(self, socket, owner = None):
        pass

    def sub_error(self, socket, owner = None):
        pass

    def unsub_read(self, socket, owner = None):
        pass

    def unsub_write(self, socket, owner = None):
        pass

    def unsub_error(self, socket, owner = None):
        pass

class SelectPoll(Poll):

    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self._open = False

    def open(self):
        if self._open: return
        self._open = True

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
        # verifies if the current selection list is empty
        # in case it's sleeps for a while and then continues
        # the loop (this avoids error in empty selection)
        is_empty = self.is_empty()
        if is_empty: time.sleep(SELECT_TIMEOUT); return ([], [], [])

        # runs the proper select statement waiting for the desired
        # amount of time as timeout at the end a tuple with three
        # list for the different operations should be returned
        return select.select(
            self.read_l,
            self.write_l,
            self.error_l,
            SELECT_TIMEOUT
        )

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

    def is_empty(self):
        return not self.read_l and not self.write_l and not self.error_l

    def is_sub_read(self, socket):
        return socket in self.read_o

    def is_sub_write(self, socket):
        return socket in self.write_o

    def is_sub_error(self, socket):
        return socket in self.error_o

    def sub_read(self, socket, owner = None):
        if socket in self.read_o: return
        self.read_l.append(socket)
        self.read_o[socket] = owner

    def sub_write(self, socket, owner = None):
        if socket in self.write_o: return
        self.write_l.append(socket)
        self.write_o[socket] = owner

    def sub_error(self, socket, owner = None):
        if socket in self.error_o: return
        self.error_l.append(socket)
        self.error_o[socket] = owner

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
