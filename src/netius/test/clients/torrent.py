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

import struct
import hashlib
import unittest

import netius.common
import netius.clients


class TorrentConnectionTest(unittest.TestCase):

    def test_extended_t(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict(ut_metadata=1)
        connection.metadata_size = 5
        connection.metadata = [None]

        # builds an extended handshake message (extended identifier zero)
        # and verifies that it is correctly dispatched and parsed
        message = netius.common.bencode(dict(m=dict(ut_metadata=1), metadata_size=5))
        data = struct.pack("!B", 0) + netius.legacy.bytes(message)
        connection.extended_t(data)

        self.assertEqual(connection.extensions, dict(ut_metadata=1))
        self.assertEqual(connection.metadata_size, 5)

    def test_on_extended_handshake(self):
        connection = _MockTorrentConnection()

        message = netius.common.bencode(
            dict(m=dict(ut_metadata=2), metadata_size=20000)
        )
        connection.on_extended_handshake(netius.legacy.bytes(message))

        self.assertEqual(connection.extensions, dict(ut_metadata=2))
        self.assertEqual(connection.metadata_size, 20000)

        # verifies that a metadata request was sent for each of the
        # (two) metadata pieces implied by the announced metadata size
        self.assertEqual(len(connection.metadata), 2)
        self.assertEqual(len(connection.sent), 2)

    def test_on_extended_handshake_unsupported(self):
        connection = _MockTorrentConnection()

        message = netius.common.bencode(dict(m=dict()))
        connection.on_extended_handshake(netius.legacy.bytes(message))

        # verifies that no metadata request is sent when the peer does
        # not announce support for the metadata extension
        self.assertEqual(connection.sent, [])

    def test_on_metadata(self):
        connection = _MockTorrentConnection()
        connection.metadata = [None]

        payload = b"hello world"
        header = netius.common.bencode(dict(msg_type=1, piece=0))
        data = netius.legacy.bytes(header) + payload
        connection.on_metadata(data)

        # verifies that the metadata buffer is complete and that the
        # assembled metadata was handed over to the associated task
        self.assertEqual(connection.task.metadata, payload)

    def test_on_metadata_reject(self):
        connection = _MockTorrentConnection()
        connection.metadata = [None]

        header = netius.common.bencode(dict(msg_type=2, piece=0))
        connection.on_metadata(netius.legacy.bytes(header))

        # verifies that a reject message does not store any data and
        # that the metadata is not (incorrectly) considered complete
        self.assertEqual(connection.metadata, [None])
        self.assertEqual(connection.task.metadata, None)

    def test_extended_handshake(self):
        connection = _MockTorrentConnection()

        connection.extended_handshake()

        self.assertEqual(len(connection.sent), 1)

        # verifies that the message has the proper extended type (20) and
        # the reserved extended handshake identifier (zero)
        length, type, extended = struct.unpack("!LBB", connection.sent[0][:6])
        self.assertEqual(type, 20)
        self.assertEqual(extended, 0)

    def test_request_metadata(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict(ut_metadata=3)

        connection.request_metadata(0)

        self.assertEqual(len(connection.sent), 1)

        # verifies that the message uses the extended identifier assigned
        # by the peer for the metadata extension (three in this case)
        length, type, extended = struct.unpack("!LBB", connection.sent[0][:6])
        self.assertEqual(type, 20)
        self.assertEqual(extended, 3)

    def test_request_metadata_unsupported(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict()

        connection.request_metadata(0)

        # verifies that no message is sent when the peer has not assigned
        # an identifier for the metadata extension (not supported)
        self.assertEqual(connection.sent, [])

    def test_extended(self):
        connection = _MockTorrentConnection()

        connection.extended(5, b"data")

        (length,) = struct.unpack("!L", connection.sent[0][:4])
        self.assertEqual(length, 6)

    def test_metadata_pieces(self):
        connection = _MockTorrentConnection()

        connection.metadata_size = 16384
        self.assertEqual(connection._metadata_pieces(), 1)

        connection.metadata_size = 16385
        self.assertEqual(connection._metadata_pieces(), 2)

        connection.metadata_size = 40000
        self.assertEqual(connection._metadata_pieces(), 3)


class _MockTorrentConnection(netius.clients.TorrentConnection):

    def __init__(self):
        self.sent = []
        self.extensions = {}
        self.metadata_size = 0
        self.metadata = []
        self.task = _MockTorrentTask()

    def send(self, data):
        self.sent.append(data)
        return data


class _MockTorrentTask(object):

    def __init__(self):
        self.metadata = None

    def has_metadata(self):
        return False

    def set_metadata(self, metadata):
        self.metadata = metadata
