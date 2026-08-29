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


class WSTest(unittest.TestCase):

    def test_encode_ws(self):
        result = netius.common.encode_ws(b"Hello World", mask=False)

        # a short payload is announced by the seven bits of the second byte,
        # the first one carrying the final flag together with the opcode
        self.assertEqual(result[:2], b"\x81\x0b")
        self.assertEqual(result[2:], b"Hello World")

    def test_encode_ws_masked(self):
        result = netius.common.encode_ws(b"Hello World", mask=True)

        # the mask flag is the highest bit of the second byte and the four
        # bytes of the mask are placed before the payload that they cover
        self.assertEqual(netius.legacy.ord(result[1:2]) & 0x80, 0x80)
        self.assertEqual(len(result), 2 + 4 + 11)
        self.assertNotEqual(result[6:], b"Hello World")

    def test_encode_ws_extended(self):
        result = netius.common.encode_ws(b"x" * 200, mask=False)

        # a payload that does not fit the seven bits is announced by the
        # sentinel of 126 followed by the length in two bytes
        self.assertEqual(result[:4], b"\x81\x7e\x00\xc8")

    def test_encode_ws_extended_long(self):
        result = netius.common.encode_ws(b"x" * 70000, mask=False)

        # a payload that does not fit two bytes is announced by the sentinel
        # of 127 followed by the length in eight bytes
        self.assertEqual(result[:2], b"\x81\x7f")
        self.assertEqual(result[2:10], b"\x00\x00\x00\x00\x00\x01\x11\x70")

    def test_decode_ws(self):
        frame = netius.common.encode_ws(b"Hello World", mask=False)
        decoded, remaining = netius.common.decode_ws(frame)

        # the payload is recovered as it was encoded and nothing is left
        # pending, as the frame carried a single message
        self.assertEqual(decoded, b"Hello World")
        self.assertEqual(remaining, b"")

    def test_decode_ws_masked(self):
        frame = netius.common.encode_ws(b"Hello World", mask=True)
        decoded, remaining = netius.common.decode_ws(frame)

        # the unmasking of the payload recovers the original one, the mask
        # being carried by the frame itself
        self.assertEqual(decoded, b"Hello World")
        self.assertEqual(remaining, b"")

    def test_decode_ws_extended(self):
        for size in (200, 70000):
            frame = netius.common.encode_ws(b"x" * size, mask=False)
            decoded, remaining = netius.common.decode_ws(frame)

            # both of the extended forms of the length are understood, so a
            # payload of any size is recovered as it was encoded
            self.assertEqual(decoded, b"x" * size)
            self.assertEqual(remaining, b"")

    def test_decode_ws_pending(self):
        first = netius.common.encode_ws(b"first", mask=False)
        second = netius.common.encode_ws(b"second", mask=False)

        decoded, remaining = netius.common.decode_ws(first + second)

        # a payload is bounded by the length that the frame announces, so
        # the frame that follows it is left pending instead of being taken
        # as part of the one that precedes it
        self.assertEqual(decoded, b"first")

        decoded, remaining = netius.common.decode_ws(remaining)
        self.assertEqual(decoded, b"second")
        self.assertEqual(remaining, b"")

    def test_decode_ws_pending_masked(self):
        first = netius.common.encode_ws(b"first", mask=True)
        second = netius.common.encode_ws(b"second", mask=True)

        decoded, remaining = netius.common.decode_ws(first + second)

        # the very same bounding applies to a masked frame, so that the two
        # directions of a connection behave in the same way
        self.assertEqual(decoded, b"first")
        self.assertEqual(netius.common.decode_ws(remaining)[0], b"second")

    def test_decode_ws_insufficient(self):
        # a frame that does not carry the two bytes of its header, or the
        # payload that it announces, cannot be decoded yet
        self.assertRaises(netius.DataError, netius.common.decode_ws, b"\x81")
        self.assertRaises(netius.DataError, netius.common.decode_ws, b"\x81\x0bHello")

    def test_decode_ws_insufficient_extended(self):
        # the extended forms of the length need their own bytes to be read
        # before the length that they carry may be known
        self.assertRaises(netius.DataError, netius.common.decode_ws, b"\x81\x7e\x00")
        self.assertRaises(netius.DataError, netius.common.decode_ws, b"\x81\x7f\x00")

    def test_assert_ws(self):
        # the assertion passes for a buffer that carries at least the size
        # that is required and fails for one that does not
        self.assertEqual(netius.common.assert_ws(4, 2), None)
        self.assertRaises(netius.DataError, netius.common.assert_ws, 1, 2)
