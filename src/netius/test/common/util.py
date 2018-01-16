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

import unittest

import netius.common

class UtilTest(unittest.TestCase):

    def test_is_ip4(self):
        result = netius.common.is_ip4("127.0.0.1")
        self.assertEqual(result, True)

        result = netius.common.is_ip4("172.16.0.0/16")
        self.assertEqual(result, False)

    def test_is_ip6(self):
        result = netius.common.is_ip6("::1")
        self.assertEqual(result, True)

        result = netius.common.is_ip6("127.0.0.1")
        self.assertEqual(result, False)

    def test_assert_ip4(self):
        allowed = ("127.0.0.1", "192.168.0.1", "172.16.0.0/16")

        result = netius.common.assert_ip4("127.0.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("192.168.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("192.168.0.2", allowed)
        self.assertEqual(result, False)

        result = netius.common.assert_ip4("172.16.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("172.16.1.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("172.17.0.1", allowed)
        self.assertEqual(result, False)

    def test_in_subnet_ip4(self):
        result = netius.common.in_subnet_ip4("127.0.0.1", "127.0.0.0/24")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.2", "127.0.0.0/24")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.1", "127.0.0.0/31")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.2", "127.0.0.0/31")
        self.assertEqual(result, False)

        result = netius.common.in_subnet_ip4("127.0.0.1", "128.0.0.0/24")
        self.assertEqual(result, False)

    def test_addr_to_ip4(self):
        result = netius.common.addr_to_ip4(2130706433)
        self.assertEqual(result, "127.0.0.1")

        result = netius.common.addr_to_ip4(3232235521)
        self.assertEqual(result, "192.168.0.1")

        result = netius.common.addr_to_ip4(3627733678)
        self.assertEqual(result, "216.58.210.174")

    def test_addr_to_ip6(self):
        result = netius.common.addr_to_ip6(1)
        self.assertEqual(result, "0000:0000:0000:0000:0000:0000:0000:0001")

        result = netius.common.addr_to_ip6(338288524927261089654018896841347694593)
        self.assertEqual(result, "fe80:0000:0000:0000:0000:0000:0000:0001")

        result = netius.common.addr_to_ip6(55827987829222246039918918277097594894)
        self.assertEqual(result, "2a00:1450:4003:0801:0000:0000:0000:200e")

    def test_bytes_to_integer(self):
        result = netius.common.bytes_to_integer(b"Hello World")
        self.assertEqual(result, 87521618088882533792115812)

    def test_integer_to_bytes(self):
        result = netius.common.integer_to_bytes(87521618088882533792115812)
        self.assertEqual(result, b"Hello World")

    def test_size_round_unit(self):
        result = netius.common.size_round_unit(209715200, space = True)
        self.assertEqual(result, "200 MB")

        result = netius.common.size_round_unit(20480, space = True)
        self.assertEqual(result, "20 KB")

        result = netius.common.size_round_unit(2048, reduce = False, space = True)
        self.assertEqual(result, "2.00 KB")

        result = netius.common.size_round_unit(2500, space = True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(2500, reduce = False, space = True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(1)
        self.assertEqual(result, "1B")

        result = netius.common.size_round_unit(2048, minimum = 2049, reduce = False)
        self.assertEqual(result, "2048B")

        result = netius.common.size_round_unit(2049, places = 4, reduce = False)
        self.assertEqual(result, "2.001KB")

        result = netius.common.size_round_unit(2048, places = 0, reduce = False)
        self.assertEqual(result, "2KB")

        result = netius.common.size_round_unit(2049, places = 0, reduce = False)
        self.assertEqual(result, "2KB")
