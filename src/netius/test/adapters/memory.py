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
import netius.adapters


class MemoryAdapterTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.adapter = netius.adapters.MemoryAdapter()

    def test_set(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        self.assertEqual(self.adapter.get(key), b"Hello World")
        self.assertEqual(self.adapter.count(owner="joe"), 1)

    def test_set_text(self):
        key = self.adapter.set("Hello World", owner="joe")

        # a textual value is normalized on the way in, so that the adapters
        # remain interchangeable with the file based one, which does the same
        self.assertEqual(self.adapter.get(key), b"Hello World")

        file = self.adapter.get_file(key)
        try:
            self.assertEqual(file.read(), b"Hello World")
        finally:
            file.close()

    def test_get_file(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        file = self.adapter.get_file(key)
        try:
            # the file is served in binary mode, as the values that are
            # kept by the adapter are byte based ones
            self.assertEqual(file.read(), b"Hello World")
        finally:
            file.close()

    def test_get_file_missing(self):
        # a key that names no value is reported through the error of the
        # library instead of leaking the one of the underlying structure
        self.assertRaises(netius.NetiusError, self.adapter.get_file, "missing")
        self.assertRaises(netius.NetiusError, self.adapter.get, "missing")

    def test_delete(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        self.adapter.delete(key)

        self.assertEqual(self.adapter.count(owner="joe"), 0)
        self.assertEqual(self.adapter.list(owner="joe"), [])

    def test_append(self):
        key = self.adapter.reserve(owner="joe")

        # the value that is appended comes from a connection and so it's a
        # byte based one, which the reserved value must be able to take
        self.adapter.append(key, b"Hello")
        self.adapter.append(key, b" World")

        self.assertEqual(self.adapter.get(key), b"Hello World")
        self.assertEqual(self.adapter.size(key), 11)

    def test_append_text(self):
        key = self.adapter.reserve(owner="joe")

        # a textual chunk is normalized the same way as a stored value, so
        # that either kind of caller is able to build up a value
        self.adapter.append(key, "Hello")
        self.adapter.append(key, b" World")

        self.assertEqual(self.adapter.get(key), b"Hello World")

    def test_truncate(self):
        key = self.adapter.set(b"Hello World\r\n", owner="joe")

        self.adapter.truncate(key, 2)

        self.assertEqual(self.adapter.get(key), b"Hello World")

    def test_size(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        self.assertEqual(self.adapter.size(key), 11)

    def test_sizes(self):
        self.adapter.set(b"Hello", owner="joe")
        self.adapter.set(b"World", owner="joe")

        self.assertEqual(self.adapter.sizes(owner="joe"), [5, 5])
        self.assertEqual(self.adapter.total(owner="joe"), 10)

    def test_reserve(self):
        key = self.adapter.reserve(owner="joe")

        self.assertEqual(self.adapter.get(key), b"")
        self.assertEqual(self.adapter.size(key), 0)

    def test_count(self):
        self.adapter.set(b"Hello", owner="joe")
        self.adapter.set(b"World", owner="mary")

        self.assertEqual(self.adapter.count(owner="joe"), 1)
        self.assertEqual(self.adapter.count(), 2)

    def test_list(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        result = self.adapter.list(owner="joe")

        # the listing is a materialized sequence so that it may be indexed
        # by the servers that walk it, which a view would not allow
        self.assertEqual(result[0], key)
        self.assertEqual(len(result), 1)
        self.assertEqual(self.adapter.list(owner="mary"), [])
