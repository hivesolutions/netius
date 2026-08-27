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

from netius.base import legacy


class LegacyTest(unittest.TestCase):

    def test_eager(self):
        result = legacy.eager(iter([1, 2, 3]))

        # the eager operation materializes any iterable into a list, so
        # that it may be indexed and traversed more than once
        self.assertEqual(result, [1, 2, 3])
        self.assertEqual(legacy.eager([1, 2, 3]), [1, 2, 3])

    def test_items(self):
        result = legacy.items(dict(first=1))

        self.assertEqual(list(result), [("first", 1)])

    def test_keys(self):
        result = legacy.keys(dict(first=1))

        # the keys are materialized into a sequence, so that they may be
        # indexed, which the view of the newer runtimes does not allow
        self.assertEqual(result[0], "first")

    def test_values(self):
        result = legacy.values(dict(first=1))

        self.assertEqual(result[0], 1)

    def test_xrange(self):
        self.assertEqual(list(legacy.xrange(5)), [0, 1, 2, 3, 4])
        self.assertEqual(list(legacy.xrange(1, 5)), [1, 2, 3, 4])
        self.assertEqual(list(legacy.xrange(1, 10, 2)), [1, 3, 5, 7, 9])

    def test_xrange_zero(self):
        # a stop of zero is a valid bound and not the absence of one, so
        # the sequence must be an empty one instead of counting up to the
        # value that has been given as the start
        self.assertEqual(list(legacy.xrange(5, 0)), [])
        self.assertEqual(
            list(legacy.xrange(10, 0, -1)), [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        )

    def test_range(self):
        self.assertEqual(legacy.range(5), [0, 1, 2, 3, 4])
        self.assertEqual(legacy.range(1, 5), [1, 2, 3, 4])
        self.assertEqual(legacy.range(1, 10, 2), [1, 3, 5, 7, 9])

    def test_range_zero(self):
        self.assertEqual(legacy.range(5, 0), [])
        self.assertEqual(legacy.range(10, 0, -1), [10, 9, 8, 7, 6, 5, 4, 3, 2, 1])

    def test_bytes(self):
        result = legacy.bytes("value")

        self.assertEqual(result, b"value")
        self.assertEqual(legacy.bytes(b"value"), b"value")

    def test_str(self):
        result = legacy.str(b"value")

        self.assertEqual(result, "value")
        self.assertEqual(legacy.str("value"), "value")

    def test_u(self):
        # the decoding is a no operation under the newer runtimes, where a
        # native string is already a unicode one, unless it's forced
        result = legacy.u(b"value", force=True)

        self.assertEqual(result, "value")
        self.assertEqual(legacy.u(None, force=True), None)
        self.assertEqual(legacy.u("value", force=True), "value")

    def test_ascii(self):
        # a byte sequence that is not representable under the target
        # encoding is replaced instead of raising, as the operation is
        # meant to be used for presentation only
        result = legacy.ascii(b"\xff")

        self.assertEqual(legacy.is_string(result), True)

    def test_orderable(self):
        result = legacy.orderable((1, "first"))

        self.assertEqual(result[0], 1)

    def test_is_str(self):
        self.assertEqual(legacy.is_str("value"), True)
        self.assertEqual(legacy.is_str(b"value"), False)

    def test_is_bytes(self):
        self.assertEqual(legacy.is_bytes(b"value"), True)
        self.assertEqual(legacy.is_bytes("value"), False)

    def test_is_string(self):
        self.assertEqual(legacy.is_string("value"), True)
        self.assertEqual(legacy.is_string(b"value"), False)

        # the complete verification also accepts the byte based sequences
        # as strings, which is required for the data coming from a socket
        self.assertEqual(legacy.is_string(b"value", all=True), True)
        self.assertEqual(legacy.is_string(1, all=True), False)

    def test_is_generator(self):
        def generator():
            yield 1

        self.assertEqual(legacy.is_generator(generator()), True)
        self.assertEqual(legacy.is_generator([1]), False)

    def test_has_module(self):
        self.assertEqual(legacy.has_module("unittest"), True)
        self.assertEqual(legacy.has_module("netius_missing_module"), False)

    def test_to_timestamp(self):
        date_time = legacy.to_datetime(0)
        result = legacy.to_timestamp(date_time)

        # the conversion is a reversible one, so that a timestamp that is
        # turned into a date may be turned back into the very same value
        self.assertEqual(result, 0)

    def test_utcfromtimestamp(self):
        result = legacy.utcfromtimestamp(0)

        self.assertEqual(result.year, 1970)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def test_quote(self):
        self.assertEqual(legacy.quote("a b"), "a%20b")
        self.assertEqual(legacy.unquote("a%20b"), "a b")

    def test_quote_plus(self):
        self.assertEqual(legacy.quote_plus("a b"), "a+b")
        self.assertEqual(legacy.unquote_plus("a+b"), "a b")

    def test_urlencode(self):
        result = legacy.urlencode(dict(first="1"))

        self.assertEqual(result, "first=1")
