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


class TorrentTest(unittest.TestCase):

    def test_bencode(self):
        # every one of the four kinds of the encoding is written in the shape
        # that the specification names for it
        self.assertEqual(netius.common.bencode(12), b"i12e")
        self.assertEqual(netius.common.bencode("netius"), b"6:netius")
        self.assertEqual(netius.common.bencode([1, "a"]), b"li1e1:ae")
        self.assertEqual(netius.common.bencode(dict(a=1)), b"d1:ai1ee")

    def test_bencode_ordered(self):
        # the keys of a dictionary travel in order, as the encoding of a value
        # has to be the same one whatever the order it was built in
        self.assertEqual(netius.common.bencode(dict(b=2, a=1)), b"d1:ai1e1:bi2ee")
        self.assertEqual(
            netius.common.bencode(dict(a=1, b=2)),
            netius.common.bencode(dict(b=2, a=1)),
        )

    def test_bencode_invalid(self):
        # a value of a kind that the encoding does not name cannot be written,
        # so it is refused instead of being written as something else
        self.assertRaises(netius.ParserError, netius.common.bencode, 1.5)

    def test_bdecode(self):
        self.assertEqual(netius.common.bdecode(b"i12e"), 12)
        self.assertEqual(netius.common.bdecode(b"6:netius"), "netius")
        self.assertEqual(netius.common.bdecode(b"li1e1:ae"), [1, "a"])
        self.assertEqual(netius.common.bdecode(b"d1:ai1ee"), dict(a=1))

    def test_bdecode_nested(self):
        data = b"d4:infod6:lengthi128e4:name6:netiuseee"

        # a value nested in another is decoded together with the one that
        # carries it, the two of them coming back as one structure
        self.assertEqual(
            netius.common.bdecode(data),
            dict(info=dict(length=128, name="netius")),
        )

    def test_bdecode_invalid(self):
        # a payload that names no kind at all cannot be read, so it is
        # refused instead of a value being invented for it
        self.assertRaises(netius.ParserError, netius.common.bdecode, b"x")

    def test_roundtrip(self):
        value = dict(
            announce="http://tracker.hive/announce",
            info=dict(length=1024, name="netius", pieces=["a", "b"]),
            created=1234,
        )

        # what is written may be read back as it was, which is the property
        # that the encoding exists for
        self.assertEqual(netius.common.bdecode(netius.common.bencode(value)), value)

    def test_info_hash(self):
        root = dict(info=dict(length=128, name="netius"))

        # the hash names the encoded form of the information of the torrent,
        # which is what makes it the same for every peer of it
        expected = hashlib.sha1(netius.common.bencode(root["info"])).digest()
        self.assertEqual(netius.common.info_hash(root), expected)
        self.assertEqual(len(netius.common.info_hash(root)), 20)


class TorrentParserTest(unittest.TestCase):

    def test_parse_handshake(self):
        owner = _MockOwner()
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind(
            "on_handshake",
            lambda *args: received.append(args),
        )

        parser.parse(self._handshake())

        # the handshake carries the protocol, the hash of the torrent and the
        # identifier of the peer, all of which reach whoever listens for it
        protocol, _reserved, info_hash, peer_id = received[0]
        self.assertEqual(protocol, b"BitTorrent protocol")
        self.assertEqual(info_hash, b"h" * 20)
        self.assertEqual(peer_id, b"p" * 20)

    def test_parse_handshake_partial(self):
        owner = _MockOwner()
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_handshake", lambda *args: received.append(args))

        data = self._handshake()

        # a handshake that arrived in parts is only read once the whole of it
        # is there, the parts being held until then
        self.assertEqual(parser.parse(data[:30]), 0)
        self.assertEqual(received, [])

        parser.parse(data[30:])

        self.assertEqual(len(received), 1)

    def test_parse_message(self):
        owner = _MockOwner(state=2)
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_message", lambda *args: received.append(args))

        parser.parse(self._message(1, b"body"))

        # the type of the message is named by the identifier that leads it,
        # and the payload that follows travels with it
        length, type_s, data = received[0]
        self.assertEqual(length, 5)
        self.assertEqual(type_s, "unchoke")
        self.assertEqual(data, b"body")

    def test_parse_message_keepalive(self):
        owner = _MockOwner(state=2)
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_message", lambda *args: received.append(args))

        parser.parse(struct.pack("!L", 0))

        # a message with no payload at all is the one that keeps a connection
        # alive, which is the name it is given
        length, type_s, data = received[0]
        self.assertEqual(length, 0)
        self.assertEqual(type_s, "keep-alive")
        self.assertEqual(data, b"")

    def test_parse_message_unknown(self):
        owner = _MockOwner(state=2)
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_message", lambda *args: received.append(args))

        parser.parse(self._message(99, b""))

        # a type that none of the known ones names is reported as an invalid
        # one, instead of the parsing of the connection breaking on it
        self.assertEqual(received[0][1], "invalid")

    def test_parse_message_partial(self):
        owner = _MockOwner(state=2)
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_message", lambda *args: received.append(args))

        data = self._message(1, b"body")

        # a size that is incomplete is held whole, and once it is there only
        # the bytes of it are taken, the payload being waited for
        self.assertEqual(parser.parse(data[:2]), 0)
        self.assertEqual(parser.parse(data[2:6]), 2)
        self.assertEqual(received, [])

        parser.parse(data[6:])

        self.assertEqual(len(received), 1)

    def test_parse_message_sequence(self):
        owner = _MockOwner(state=2)
        parser = netius.common.TorrentParser(owner)
        received = []
        parser.bind("on_message", lambda *args: received.append(args))

        data = self._message(1, b"first") + self._message(2, b"second")
        parser.parse(data)

        # more than one message in a single chunk is read as many, so that a
        # peer that batches them is not held back
        self.assertEqual(len(received), 2)
        self.assertEqual(received[0][2], b"first")
        self.assertEqual(received[1][1], "interested")

    def _handshake(self):
        # builds the handshake that opens a connection, in the shape that the
        # specification names for it
        return struct.pack(
            "!B19sQ20s20s", 19, b"BitTorrent protocol", 0, b"h" * 20, b"p" * 20
        )

    def _message(self, type, data):
        # builds a message of the requested type, led by the size of it as
        # the framing of the protocol asks for
        payload = struct.pack("!B", type) + data
        return struct.pack("!L", len(payload)) + payload


class _MockOwner(object):
    """
    Stand in for the connection that owns a parser, carrying only
    the state that the parsing of it reads and changes.
    """

    def __init__(self, state=1):
        self.state = state
