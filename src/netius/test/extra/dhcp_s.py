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

import netius.common
import netius.extra

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class DHCPServerSTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.pool = netius.common.AddressPool("192.168.0.61", "192.168.0.69")
        self.server = netius.extra.DHCPServerS(pool=self.pool)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        server = netius.extra.DHCPServerS()

        try:
            # the default pool covers the small range of addresses that
            # the server is able to hand out, none of them taken yet
            self.assertEqual(server.pool.start_addr, "192.168.0.61")
            self.assertEqual(server.pool.end_addr, "192.168.0.69")
            self.assertEqual(server.options, {})
            self.assertEqual(server.lease, 3600)
        finally:
            server.cleanup()

    def test_init_values(self):
        server = netius.extra.DHCPServerS(
            pool=self.pool,
            options=dict(subnet=dict(subnet="255.255.255.0"), lease=dict(time=60)),
        )

        try:
            self.assertEqual(server.pool, self.pool)
            self.assertEqual(
                server.options,
                {
                    netius.common.SUBNET_DHCP: dict(subnet="255.255.255.0"),
                    netius.common.LEASE_DHCP: dict(time=60),
                },
            )
            self.assertEqual(server.lease, 60)
        finally:
            server.cleanup()

    def test_get_type(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        request = self._make_request(type=0x01)

        # a discovery is always answered with an offer, as there's no
        # address associated with the client at that point
        self.assertEqual(self.server.get_type(request), netius.common.OFFER_DHCP)

        addr = self.pool.reserve(owner="00:00:00:00:00:01")
        request = self._make_request(type=0x03, mac="00:00:00:00:00:01")

        # the address is owned by the client that requests it, so the
        # request is acknowledged instead of being refused
        self.assertEqual(self.server.get_type(request), netius.common.ACK_DHCP)

        request = self._make_request(type=0x03, mac="00:00:00:00:00:02", requested=addr)

        # the address that is requested belongs to another client, which
        # makes the request an invalid one
        self.assertEqual(self.server.get_type(request), netius.common.NAK_DHCP)

    def test_get_options(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.options[netius.common.SUBNET_DHCP] = dict(subnet="255.255.255.0")

        options = self.server.get_options(self._make_request(type=0x01))

        self.assertEqual(
            options, {netius.common.SUBNET_DHCP: dict(subnet="255.255.255.0")}
        )

        # the options are copied before being given away, so that the
        # response of a request does not change the ones of the server
        options[netius.common.NAME_DHCP] = dict(name="hive")

        self.assertEqual(netius.common.NAME_DHCP in self.server.options, False)

    def test_get_yiaddr(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        request = self._make_request(type=0x01, mac="00:00:00:00:00:01")

        addr = self.server.get_yiaddr(request)

        # the discovery reserves the first address of the pool for the
        # client, associating the two of them
        self.assertEqual(addr, "192.168.0.61")
        self.assertEqual(self.pool.assigned("00:00:00:00:00:01"), addr)

        request = self._make_request(type=0x03, mac="00:00:00:00:00:01")

        # the request that follows the discovery confirms the very same
        # address, as it is the one that is assigned to the client
        self.assertEqual(self.server.get_yiaddr(request), addr)

    def test__build(self):
        self.server.options = {}
        self.server._build(dict(router=dict(routers=["192.168.0.1"])))

        self.assertEqual(
            self.server.options,
            {netius.common.ROUTER_DHCP: dict(routers=["192.168.0.1"])},
        )

        # a lease that is not part of the options keeps the default value
        # of one hour, as there's nothing to take the time from
        self.assertEqual(self.server.lease, 3600)

        self.server.options = {}
        self.server._build(dict(invalid=dict(value="dummy"), lease=dict(time=60)))

        # an option whose name is not a known one is skipped, only the
        # ones that map to an integer taking part in the result
        self.assertEqual(self.server.options, {netius.common.LEASE_DHCP: dict(time=60)})
        self.assertEqual(self.server.lease, 60)

    def test__reserve(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        request = self._make_request(type=0x01, mac="00:00:00:00:00:01")

        addr = self.server._reserve(request)

        self.assertEqual(addr, "192.168.0.61")
        self.assertEqual(self.pool.is_owner("00:00:00:00:00:01", addr), True)

        # a second client takes the address that follows, as the first
        # one is already leased and so no longer available
        request = self._make_request(type=0x01, mac="00:00:00:00:00:02")

        self.assertEqual(self.server._reserve(request), "192.168.0.62")

    def test__confirm(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the lease of the reserve is a short one when set against the one
        # of the server, but still long enough for the address to be valid
        # by the time that the confirmation reaches it
        addr = self.pool.reserve(owner="00:00:00:00:00:01", lease=60)
        target = self.pool.map[addr]
        request = self._make_request(type=0x03, mac="00:00:00:00:00:01")

        self.assertEqual(self.server._confirm(request), addr)

        # the confirmation renews the lease of the address, extending it
        # from the short one of the reserve to the one of the server
        self.assertEqual(self.pool.map[addr] > target, True)
        self.assertEqual(self.pool.is_valid(addr), True)

        # an address that is not part of the pool is given back unchanged,
        # as there's no lease of it that may be renewed
        request = self._make_request(
            type=0x03, mac="00:00:00:00:00:02", requested="10.0.0.1"
        )

        self.assertEqual(self.server._confirm(request), "10.0.0.1")
        self.assertEqual(self.pool.exists("10.0.0.1"), False)

    def _make_request(self, type=0x01, mac="00:00:00:00:00:00", requested=None):
        request = mock.MagicMock()
        request.get_type.return_value = type
        request.get_mac.return_value = mac
        request.get_requested.return_value = requested
        return request
