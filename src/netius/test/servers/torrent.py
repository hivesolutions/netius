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

import time
import struct
import hashlib
import unittest

import netius.common
import netius.servers


class TorrentTaskTest(unittest.TestCase):

    def test_on_dht_unloaded(self):
        task = _build_task()
        task.owner = None

        # verifies that a DHT response received after the task has been
        # unloaded (no owner) is ignored instead of raising an error
        task.on_dht("response")

    def test_on_dht_malformed(self):
        task = _build_task()
        task.connect_peers = lambda: None

        valid = struct.pack("!LH", netius.common.ip4_to_addr("1.2.3.4"), 6881)
        response = _MockResponse(dict(values=[valid, b"bad"]))
        task.on_dht(response)

        # verifies that the malformed value is skipped and only the valid
        # (compact) peer is added to the task instead of raising an error
        self.assertEqual(len(task.peers), 1)
        self.assertEqual(task.peers[0]["ip"], "1.2.3.4")
        self.assertEqual(task.peers[0]["port"], 6881)

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

    def test_set_data_no_pieces(self):
        task = _build_task()
        task.stored = None

        # verifies that setting data while the pieces structure is not
        # loaded (eg: before the metadata exchange) does not raise
        task.set_data(b"data", 0, 0)

    def test_eta(self):
        task = _build_task()
        task.info = dict(length=100)
        task.downloaded = 50
        task.start = time.time() - 10

        # with half the data downloaded in 10 seconds the speed is 5 bytes
        # per second and so the remaining 50 bytes take 10 seconds (eta)
        self.assertEqual(round(task.eta()), 10)
        self.assertEqual(task.eta_s(), "10s")

    def test_eta_no_speed(self):
        task = _build_task()
        task.info = dict(length=100)
        task.downloaded = 0
        task.start = time.time()

        # with no data downloaded the speed is null and the eta should be
        # zero instead of raising a division by zero error
        self.assertEqual(task.eta(), 0.0)
        self.assertEqual(task.eta_s(), "0s")

    def test_add_peer_max(self):
        task = _build_task()
        task.owner.max_peers = 1

        task.add_peer(dict(ip="1.2.3.4", port=6881))
        task.add_peer(dict(ip="5.6.7.8", port=1234))

        # verifies that no more peers than the configured maximum are
        # added to the task (the second peer is discarded)
        self.assertEqual(len(task.peers), 1)
        self.assertEqual(task.peers[0]["ip"], "1.2.3.4")


def _build_task(info_hash=None):
    task = netius.servers.TorrentTask.__new__(netius.servers.TorrentTask)
    task.owner = _MockOwner()
    task.info_hash = info_hash
    task.info = dict(info_hash=info_hash)
    task.connections = []
    task.peers = []
    task.peers_m = {}
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

    def __init__(self):
        self.max_peers = netius.servers.torrent.MAX_PEERS

    def warning(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


class _MockResponse(object):

    def __init__(self, payload):
        self.payload = payload

    def get_payload(self):
        return self.payload
