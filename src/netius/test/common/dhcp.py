#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius
import netius.common


class AddressPoolTest(unittest.TestCase):

    def test_init(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.3")

        # the pool is populated with the complete range that it spans, the
        # bounds of it included, and none of the addresses is yet valid
        self.assertEqual(pool.exists("192.168.0.1"), True)
        self.assertEqual(pool.exists("192.168.0.3"), True)
        self.assertEqual(pool.exists("192.168.0.4"), False)
        self.assertEqual(pool.is_valid("192.168.0.1"), False)

    def test_get_next(self):
        self.assertEqual(
            netius.common.AddressPool.get_next("192.168.0.1"), "192.168.0.2"
        )

        # the last octet rolls over into the one that precedes it, so that
        # the sequence walks the complete range of a network
        self.assertEqual(
            netius.common.AddressPool.get_next("192.168.0.255"), "192.168.1.0"
        )
        self.assertEqual(
            netius.common.AddressPool.get_next("192.168.255.255"), "192.169.0.0"
        )

    def test_peek(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.2")

        # the peeking of an address does not reserve it, so the very same
        # address is offered again by a second peek
        self.assertEqual(pool.peek(), "192.168.0.1")
        self.assertEqual(pool.peek(), "192.168.0.2")

    def test_peek_exhausted(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.1")
        pool.reserve(owner="joe")

        # a pool whose only address has been reserved has nothing left to
        # offer, which is reported as an error instead of an empty value
        self.assertRaises(netius.NetiusError, pool.peek)

    def test_peek_touched(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.1")
        addr = pool.reserve(owner="joe", lease=1)
        pool.touch(addr, lease=3600)

        # the touching of an address leaves the entry of the previous lease
        # behind, which the peeking skips instead of taking it for a free
        # address and handing the very same one out twice
        self.assertRaises(netius.NetiusError, pool.peek)

    def test_reserve(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.2")

        addr = pool.reserve(owner="joe")

        # the reserved address becomes a valid one, bound to the owner that
        # asked for it and resolvable from that owner alone
        self.assertEqual(addr, "192.168.0.1")
        self.assertEqual(pool.is_valid(addr), True)
        self.assertEqual(pool.is_owner("joe", addr), True)
        self.assertEqual(pool.is_owner("mary", addr), False)
        self.assertEqual(pool.assigned("joe"), addr)
        self.assertEqual(pool.assigned("mary"), None)

    def test_is_owner_invalid(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.2")

        # an address whose lease was never taken belongs to nobody, so the
        # ownership of it is denied even to the owner that asks for it
        self.assertEqual(pool.is_owner("joe", "192.168.0.1"), False)

    def test_touch(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.2")
        addr = pool.reserve(owner="joe", lease=1)

        pool.touch(addr, lease=3600)

        # the touching of a valid address extends the lease that it carries,
        # keeping it out of the addresses that may be offered
        self.assertEqual(pool.is_valid(addr), True)

    def test_touch_invalid(self):
        pool = netius.common.AddressPool("192.168.0.1", "192.168.0.2")

        # an address whose lease has never been taken cannot be extended, as
        # there is no lease for it to prolong
        self.assertRaises(netius.NetiusError, pool.touch, "192.168.0.1")
