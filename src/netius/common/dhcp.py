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
import heapq

import netius

SUBNET_DHCP = 1
ROUTER_DHCP = 2
DNS_DHCP = 3
NAME_DHCP = 4
BROADCAST_DHCP = 5
REQUESTED_DHCP = 6
LEASE_DHCP = 7
DISCOVER_DHCP = 8
OFFER_DHCP = 9
REQUEST_DHCP = 10
DECLINE_DHCP = 11
ACK_DHCP = 12
NAK_DHCP = 13
IDENTIFIER_DHCP = 14
RENEWAL_DHCP = 15
REBIND_DHCP = 16
PROXY_DHCP = 17
END_DHCP = 18

OPTIONS_DHCP = dict(
    subnet = SUBNET_DHCP,
    router = ROUTER_DHCP,
    dns = DNS_DHCP,
    name = NAME_DHCP,
    broadcast = BROADCAST_DHCP,
    lease = LEASE_DHCP,
    discover = DISCOVER_DHCP,
    offer = OFFER_DHCP,
    request = REQUEST_DHCP,
    decline = DECLINE_DHCP,
    ack = ACK_DHCP,
    nak = NAK_DHCP,
    identifier = IDENTIFIER_DHCP,
    renewal = RENEWAL_DHCP,
    rebind = REBIND_DHCP,
    proxy = PROXY_DHCP,
    end = END_DHCP
)
""" The map of option names that associates
a string based name with the integer based
counter-part for resolution """

TYPES_DHCP = {
    0x01 : "discover",
    0x02 : "offer",
    0x03 : "request",
    0x04 : "decline",
    0x05 : "ack",
    0x06 : "nak"
}

VERBS_DHCP = {
    0x01 : "discovering",
    0x02 : "offering",
    0x03 : "requesting",
    0x04 : "declining",
    0x05 : "acknowledging",
    0x06 : "not acknowledging"
}

class AddressPool(object):

    def __init__(self, start_addr, end_addr):
        self.start_addr = start_addr
        self.end_addr = end_addr
        self.map = dict()
        self.owners = dict()
        self.owners_i = dict()
        self.addrs = list()

        self._populate()

    @classmethod
    def get_next(cls, current):
        current_l = current.split(".")
        current_l.reverse()
        current_l = [int(value) for value in current_l]

        for index, value in enumerate(current_l):
            if value == 255: current_l[index] = 0
            else: current_l[index] = value + 1; break

        current_l.reverse()

        next = ".".join([str(value) for value in current_l])
        return next

    def peek(self):
        addr = None
        current = time.time()

        while True:
            target, addr = heapq.heappop(self.addrs)

            _target = self.map.get(addr, 0)
            if not target == _target: continue

            if target > current:
                heapq.heappush(self.addrs, (target, addr))
                raise netius.NetiusError("No address available")

            break

        return addr

    def reserve(self, owner = None, lease = 3600):
        current = time.time()
        target = int(current + lease)
        addr = self.peek()
        self.map[addr] = target
        self.owners[addr] = owner
        self.owners_i[owner] = addr
        heapq.heappush(self.addrs, (target, addr))
        return addr

    def touch(self, addr, lease = 3600):
        is_valid = self.is_valid(addr)
        if not is_valid: raise netius.NetiusError(
            "Not possible to touch address"
        )

        current = time.time()
        target = int(current + lease)
        self.map[addr] = target
        heapq.heappush(self.addrs, (target, addr))

    def exists(self, addr):
        return addr in self.map

    def assigned(self, owner):
        return self.owners_i.get(owner, None)

    def is_valid(self, addr):
        current = time.time()
        target = self.map.get(addr, 0)
        return target > current

    def is_owner(self, owner, addr):
        is_valid = self.is_valid(addr)
        if not is_valid: return False
        _owner = self.owners.get(addr, None)
        return owner == _owner

    def _populate(self):
        addr = self.start_addr

        while True:
            self.map[addr] = 0
            self.owners[addr] = None
            heapq.heappush(self.addrs, (0, addr))
            if addr == self.end_addr: break
            addr = AddressPool.get_next(addr)
