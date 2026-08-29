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

from netius.common import structures


class PriorityDictTest(unittest.TestCase):

    def test_init(self):
        result = structures.PriorityDict(dict(a=2, b=1))

        # the heap is built from the values that the map is created with,
        # so the smallest of them is available right away
        self.assertEqual(result.smallest(), "b")

    def test_setitem(self):
        result = structures.PriorityDict()
        result["a"] = 2
        result["b"] = 1

        self.assertEqual(result["a"], 2)
        self.assertEqual(result.smallest(), "b")

        # a value that is lowered takes the place of the previous smallest
        # one, the stale entry of the heap being skipped when it is read
        result["a"] = 0
        self.assertEqual(result.smallest(), "a")

    def test_setitem_rebuild(self):
        result = structures.PriorityDict(dict(a=1))
        result["a"] = 2
        result["a"] = 3

        # the heap is rebuilt once the entries that it holds outnumber the
        # keys of the map, so that it does not grow without bound as the
        # values of a key are replaced over and over
        self.assertEqual(len(result._heap), 1)
        self.assertEqual(result.smallest(), "a")

    def test_smallest(self):
        result = structures.PriorityDict(dict(a=3, b=1, c=2))

        # the reading of the smallest key does not consume it, so the very
        # same key is returned by a second reading of the map
        self.assertEqual(result.smallest(), "b")
        self.assertEqual(result.smallest(), "b")
        self.assertEqual(len(result), 3)

    def test_smallest_stale(self):
        result = structures.PriorityDict(dict(a=0, b=1))
        result["a"] = 5

        # the previous value of the key is left behind in the heap, so the
        # reading of the smallest key skips it instead of naming a key whose
        # value is no longer the one that the entry carries
        self.assertEqual(result.smallest(), "b")

    def test_pop_smallest(self):
        result = structures.PriorityDict(dict(a=3, b=1, c=2))

        # the popping of the smallest key removes it from the map, so the
        # keys come out in the order of their values
        self.assertEqual(result.pop_smallest(), "b")
        self.assertEqual(result.pop_smallest(), "c")
        self.assertEqual(result.pop_smallest(), "a")
        self.assertEqual(len(result), 0)

    def test_pop_smallest_stale(self):
        result = structures.PriorityDict(dict(a=0, b=1))
        result["a"] = 5

        # the stale entry is discarded by the popping as well, so that the
        # key that is removed is the one that really holds the lowest value
        self.assertEqual(result.pop_smallest(), "b")
        self.assertEqual(result.smallest(), "a")

    def test_setdefault(self):
        result = structures.PriorityDict(dict(a=1))

        # a key that is already in the map keeps the value that it carries,
        # while a new one is set with the value that is provided for it
        self.assertEqual(result.setdefault("a", 9), 1)
        self.assertEqual(result.setdefault("b", 0), 0)
        self.assertEqual(result.smallest(), "b")

    def test_update(self):
        result = structures.PriorityDict(dict(a=3))
        result.update(dict(b=1))

        # the heap is rebuilt by the update, so a value that arrives through
        # it takes part in the resolution of the smallest key
        self.assertEqual(result.smallest(), "b")

    def test_sorted_iter(self):
        result = structures.PriorityDict(dict(a=3, b=1, c=2))

        # the iteration consumes the map by the order of the values, leaving
        # it empty once the sequence has been exhausted
        self.assertEqual(list(result.sorted_iter()), ["b", "c", "a"])
        self.assertEqual(len(result), 0)


class FileIteratorTest(unittest.TestCase):

    def test_file_iterator(self):
        file = netius.legacy.BytesIO(b"hello world")
        iterator = structures.file_iterator(file, chunk_size=5)

        # the size of the file is the first value of the sequence, the ones
        # that follow it being the chunks of the contents
        self.assertEqual(next(iterator), 11)
        self.assertEqual(list(iterator), [b"hello", b" worl", b"d"])

    def test_file_iterator_empty(self):
        file = netius.legacy.BytesIO(b"")
        iterator = structures.file_iterator(file)

        # an empty file announces the size of zero and yields no chunk of
        # contents at all, instead of an empty one
        self.assertEqual(next(iterator), 0)
        self.assertEqual(list(iterator), [])
