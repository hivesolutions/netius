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

import hashlib
import unittest

import netius.common
import netius.servers


class TorrentTaskTest(unittest.TestCase):

    def test_has_metadata(self):
        task = _build_task()
        self.assertEqual(task.has_metadata(), False)

        task.info["info"] = dict(name="hello.txt")
        self.assertEqual(task.has_metadata(), True)

    def test_set_metadata(self):
        info = dict(name="hello.txt", length=5)
        metadata = netius.common.bencode(info)
        metadata = netius.legacy.bytes(metadata)
        info_hash = hashlib.sha1(metadata).digest()

        task = _build_task(info_hash=info_hash)
        task.set_metadata(metadata)

        # verifies that the metadata is correctly decoded and stored and
        # that the deferred loading operations have been triggered
        self.assertEqual(task.has_metadata(), True)
        self.assertEqual(task.info["info"]["name"], "hello.txt")
        self.assertEqual(task.loaded, True)

    def test_set_metadata_invalid(self):
        task = _build_task(info_hash=b"a" * 20)
        task.set_metadata(b"invalid")

        # verifies that an invalid metadata (info hash mismatch) is
        # discarded and that no loading operation is triggered
        self.assertEqual(task.has_metadata(), False)
        self.assertEqual(task.loaded, False)


def _build_task(info_hash=None):
    task = netius.servers.TorrentTask.__new__(netius.servers.TorrentTask)
    task.owner = _MockOwner()
    task.info_hash = info_hash
    task.info = dict(info_hash=info_hash)
    task.connections = []
    task.loaded = False

    def mark():
        task.loaded = True

    task.pieces_tracker = mark
    task.load_file = mark
    task.load_pieces = mark
    task.connect_peers = lambda: None
    task.trigger = lambda *args, **kwargs: None

    return task


class _MockOwner(object):

    def warning(self, *args, **kwargs):
        pass
