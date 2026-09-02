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

import os
import shutil
import tempfile
import unittest

import netius
import netius.adapters


class BaseAdapterTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.adapter = netius.adapters.BaseAdapter()

    def test_get(self):
        # the base of the adapters stores nothing at all, so what is read back
        # from it is always empty
        self.assertEqual(self.adapter.get("key"), "")
        self.assertEqual(self.adapter.set(b"value"), None)
        self.assertEqual(self.adapter.delete("key"), None)

    def test_size(self):
        # and it names no key of its own, so every one of the aggregations
        # over the set of them comes back empty
        self.assertEqual(self.adapter.size("key"), 0)
        self.assertEqual(self.adapter.count(), 0)
        self.assertEqual(self.adapter.list(), ())
        self.assertEqual(self.adapter.sizes(), [])
        self.assertEqual(self.adapter.total(), 0)

    def test_generate(self):
        first = self.adapter.generate()
        second = self.adapter.generate()

        # every key that is generated is a new one, as two values that shared
        # a key would overwrite each other
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 64)


class FsAdapterTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.adapter = netius.adapters.FsAdapter(base_path=self.base_path)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base_path, ignore_errors=True)

    def test_set(self):
        key = self.adapter.set(b"Hello World", owner="joe")

        # the value reaches the storage under the key that was generated for
        # it, and it is read back exactly as it was given
        self.assertEqual(self.adapter.get(key), b"Hello World")
        self.assertEqual(self.adapter.size(key), 11)

        # the owner of it names a set of its own, so that the values of one
        # may be told apart from the ones of another
        self.assertEqual(self.adapter.count(owner="joe"), 1)
        self.assertEqual(self.adapter.list(owner="joe"), [key])

    def test_set_text(self):
        key = self.adapter.set("Hello World", owner="joe")

        # a value that is text is stored as the bytes of it, so that what is
        # read back is of the same kind whatever was given
        self.assertEqual(self.adapter.get(key), b"Hello World")

    def test_delete(self):
        key = self.adapter.set(b"Hello World", owner="joe")
        self.adapter.delete(key, owner="joe")

        # the value is gone from both the storage and the set of the owner,
        # as one that stayed in either would be a leak
        self.assertEqual(self.adapter.count(owner="joe"), 0)
        self.assertEqual(os.path.exists(os.path.join(self.base_path, key)), False)

    def test_append(self):
        key = self.adapter.set(b"Hello", owner="joe")
        self.adapter.append(key, b" World")

        # what is appended goes after what is already there, the value being
        # grown instead of replaced
        self.assertEqual(self.adapter.get(key), b"Hello World")

    def test_truncate(self):
        key = self.adapter.set(b"Hello World", owner="joe")
        self.adapter.truncate(key, 6)

        # the truncating takes the requested number of bytes off the end of
        # the value, which is what a partial upload asks for
        self.assertEqual(self.adapter.get(key), b"Hello")

    def test_reserve(self):
        key = self.adapter.reserve(owner="joe")

        # a reserved key names a value that is still empty, so that it may be
        # filled in later on
        self.assertEqual(self.adapter.get(key), b"")
        self.assertEqual(self.adapter.size(key), 0)

    def test_sizes(self):
        self.adapter.set(b"Hello", owner="joe")
        self.adapter.set(b"World!", owner="joe")

        # the sizes of the set are reported together, and so is the sum of
        # them, which is what a quota is verified against
        self.assertEqual(sorted(self.adapter.sizes(owner="joe")), [5, 6])
        self.assertEqual(self.adapter.total(owner="joe"), 11)
        self.assertEqual(self.adapter.count(owner="joe"), 2)

    def test_list_missing(self):
        # an owner that names no set of its own carries no value, and asking
        # for them must not raise
        self.assertEqual(self.adapter.list(owner="missing"), [])
        self.assertEqual(self.adapter.count(owner="missing"), 0)

    def test_list_all(self):
        self.adapter.set(b"Hello", owner="joe")

        # with no owner named the whole of the storage is listed, which
        # carries the value and the set of the owner that holds the link
        self.assertEqual(len(self.adapter.list()), 2)


class NullAdapterTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.adapter = netius.adapters.NullAdapter()

    def test_set(self):
        # the adapter that stores nothing keeps neither the value nor a key
        # for it, which is what makes it the one to use where the storing is
        # not wanted at all
        self.assertEqual(self.adapter.set(b"Hello World", owner="joe"), None)
        self.assertEqual(self.adapter.count(owner="joe"), 0)
        self.assertEqual(self.adapter.list(owner="joe"), ())
        self.assertEqual(self.adapter.get("key"), "")
