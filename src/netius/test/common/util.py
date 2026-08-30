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


class UtilTest(unittest.TestCase):

    def test_cstring(self):
        # the value is cut at the first of the null bytes, which is what
        # ends a string under the C conventions
        self.assertEqual(netius.common.cstring("value\0rest"), "value")

        # a value that carries no null byte at all is already a complete
        # one, so it is given back as it is
        self.assertEqual(netius.common.cstring("value"), "value")
        self.assertEqual(netius.common.cstring(""), "")

    def test_is_ip4(self):
        result = netius.common.is_ip4("127.0.0.1")
        self.assertEqual(result, True)

        result = netius.common.is_ip4("172.16.0.0/16")
        self.assertEqual(result, False)

    def test_is_ip4_invalid(self):
        # every one of the four parts of an address stands for a single
        # byte, so neither a negative nor a larger value names one
        self.assertEqual(netius.common.is_ip4("192.168.1.-1"), False)
        self.assertEqual(netius.common.is_ip4("192.168.1.256"), False)
        self.assertEqual(netius.common.is_ip4("192.168.1.value"), False)

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

    def test_integer_to_bytes_length(self):
        result = netius.common.integer_to_bytes(1, length=4)

        # the length that is asked for is filled with the bytes that are
        # missing, which are placed in front of the value
        self.assertEqual(result, b"\x00\x00\x00\x01")

        # a length that is smaller than the one of the value changes
        # nothing, as no byte of it may be dropped
        self.assertEqual(netius.common.integer_to_bytes(256, length=1), b"\x01\x00")

    def test_integer_to_bytes_invalid(self):
        # only an integer carries the bytes that the conversion reads,
        # so a value of another kind is refused
        self.assertRaises(netius.DataError, lambda: netius.common.integer_to_bytes("1"))

    def test_bytes_to_integer_invalid(self):
        # only a byte sequence carries the value that the conversion
        # reads, so one of another kind is refused
        self.assertRaises(netius.DataError, lambda: netius.common.bytes_to_integer(1))

        # a text value is not a byte one either, whichever of the two
        # runtimes is the one that runs the case
        self.assertRaises(
            netius.DataError,
            lambda: netius.common.bytes_to_integer(netius.legacy.u("value")),
        )

    def test_hostname(self):
        result = netius.common.hostname()

        # the name of the machine is a string of its own, whatever the
        # value that the runtime gives for it
        self.assertEqual(netius.legacy.is_string(result), True)
        self.assertEqual(len(result) > 0, True)

    def test_size_round_unit(self):
        result = netius.common.size_round_unit(209715200, space=True)
        self.assertEqual(result, "200 MB")

        result = netius.common.size_round_unit(20480, space=True)
        self.assertEqual(result, "20 KB")

        result = netius.common.size_round_unit(2048, reduce=False, space=True)
        self.assertEqual(result, "2.00 KB")

        result = netius.common.size_round_unit(2500, space=True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(2500, reduce=False, space=True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(1)
        self.assertEqual(result, "1B")

        result = netius.common.size_round_unit(2048, minimum=2049, reduce=False)
        self.assertEqual(result, "2048B")

        result = netius.common.size_round_unit(2049, places=4, reduce=False)
        self.assertEqual(result, "2.001KB")

        result = netius.common.size_round_unit(2048, places=0, reduce=False)
        self.assertEqual(result, "2KB")

        result = netius.common.size_round_unit(2049, places=0, reduce=False)
        self.assertEqual(result, "2KB")

    def test_size_round_unit_justify(self):
        result = netius.common.size_round_unit(2048, justify=True)

        # the justification pads the value so that a column of them may
        # be aligned, the unit coming right after the padded value
        self.assertEqual(result.startswith(" "), True)
        self.assertEqual(result.strip(), "2KB")

        # without it the value carries no padding at all, which is the
        # whole of the difference that the flag makes
        self.assertEqual(netius.common.size_round_unit(2048), "2KB")

    def test_verify(self):
        result = netius.common.verify(1 == 1)
        self.assertEqual(result, None)

        result = netius.common.verify("hello" == "hello")
        self.assertEqual(result, None)

        self.assertRaises(netius.AssertionError, lambda: netius.common.verify(1 == 2))

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify(1 == 2, exception=netius.NetiusError),
        )

    def test_verify_equal(self):
        result = netius.common.verify_equal(1, 1)
        self.assertEqual(result, None)

        result = netius.common.verify_equal("hello", "hello")
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_equal(1, 2)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_equal(1, 2, exception=netius.NetiusError),
        )

    def test_verify_not_equal(self):
        result = netius.common.verify_not_equal(1, 2)
        self.assertEqual(result, None)

        result = netius.common.verify_not_equal("hello", "world")
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_not_equal(1, 1)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_not_equal(1, 1, exception=netius.NetiusError),
        )

    def test_verify_type(self):
        result = netius.common.verify_type("hello", str)
        self.assertEqual(result, None)

        result = netius.common.verify_type(1, int)
        self.assertEqual(result, None)

        result = netius.common.verify_type(None, int)
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_type(1, str)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_type(1, str, exception=netius.NetiusError),
        )

        self.assertRaises(
            netius.AssertionError,
            lambda: netius.common.verify_type(None, str, null=False),
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_type(
                None, str, null=False, exception=netius.NetiusError
            ),
        )

    def test_verify_many(self):
        result = netius.common.verify_many((1 == 1, 2 == 2, 3 == 3))
        self.assertEqual(result, None)

        result = netius.common.verify_many(("hello" == "hello",))
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_many((1 == 2,))
        )

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_many((1 == 1, 1 == 2))
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_many(
                (1 == 1, 1 == 2), exception=netius.NetiusError
            ),
        )
