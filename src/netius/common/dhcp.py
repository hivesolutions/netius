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
import heapq

import netius

class AddressPool(object):

    def __init__(self, start_addr, end_addr):
        self.start_addr = start_addr
        self.end_addr = end_addr
        self.map = dict()
        self.addrs = list()
        self.times = list()

        self._populate()

    @classmethod
    def get_next(cls, current):
        current_l = current.split(".")
        current_l.reverse()
        current_l = [int(value) for value in current_l]

        for index in xrange(len(current_l)):
            value = current_l[index]
            if value == 255: current_l[index] = 0
            else: current_l[index] = value + 1; break

        current_l.reverse()

        next = ".".join([str(value) for value in current_l])
        return next

    def peek(self):
        current = time.time()

        target, addr = heapq.heappop(self.addrs)
        if target > current:
            heapq.heappush(self.addrs, (target, addr))
            raise netius.NetiusError("No address available")

        return addr

    def reserve(self, lease = 3600):
        current = time.time()
        target = current + lease
        addr = self.peek()
        heapq.heappush(self.addrs, (target, addr))
        return addr

    def _populate(self):
        addr = self.start_addr
        index = 0

        while True:
            self.map[addr] = index
            heapq.heappush(self.addrs, (0, addr))
            if addr == self.end_addr: break
            addr = AddressPool.get_next(addr)
            index += 1
