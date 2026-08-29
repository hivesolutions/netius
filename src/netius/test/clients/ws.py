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

import base64
import unittest

import netius
import netius.clients

from netius.clients import ws

KEY = "dGhlIHNhbXBsZSBub25jZQ=="
""" The key of the example of the RFC 6455, whose accept key is
the one that the specification uses to demonstrate the handshake """

ACCEPT_KEY = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
""" The accept key that the RFC 6455 names as the answer to the
key above, used as the vector of the validation """

RESPONSE = (
    b"HTTP/1.1 101 Switching Protocols\r\n"
    b"Upgrade: websocket\r\n"
    b"Connection: Upgrade\r\n"
    b"Sec-WebSocket-Accept: " + netius.legacy.bytes(ACCEPT_KEY) + b"\r\n\r\n"
)
""" The answer of a server to the upgrade request, carrying the
accept key that the specification names for the key above """


class WSProtocolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.protocol = ws.WSProtocol()
        self.protocol.key = KEY

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.protocol.close()

    def test__key(self):
        result = ws.WSProtocol._key()

        # the key is the base 64 of sixteen bytes, which is what the
        # specification asks a client to offer in the handshake
        self.assertEqual(len(base64.b64decode(result)), 16)
        self.assertNotEqual(result, ws.WSProtocol._key())

    def test_add_buffer(self):
        self.protocol.add_buffer(b"first")
        self.protocol.add_buffer(b"second")

        # the buffer joins the reads that it gathers and is emptied by the
        # reading of it, so that the data is only handled once
        self.assertEqual(self.protocol.get_buffer(), b"firstsecond")
        self.assertEqual(self.protocol.get_buffer(), b"")

    def test_get_buffer_keep(self):
        self.protocol.add_buffer(b"first")

        # the reading may keep the buffer in place, which the handshake
        # needs so that the data is still there for a second attempt
        self.assertEqual(self.protocol.get_buffer(delete=False), b"first")
        self.assertEqual(self.protocol.get_buffer(), b"first")

    def test_do_handshake(self):
        self.protocol.add_buffer(RESPONSE)

        self.protocol.do_handshake()

        # the status line and the headers of the answer are gathered, the
        # names of the headers being lowered so that they may be resolved
        self.assertEqual(self.protocol.handshake, True)
        self.assertEqual(self.protocol.version, "HTTP/1.1")
        self.assertEqual(self.protocol.code, "101")
        self.assertEqual(self.protocol.headers["upgrade"], "websocket")

    def test_do_handshake_remaining(self):
        frame = netius.common.encode_ws(b"Hello World", mask=False)
        self.protocol.add_buffer(RESPONSE + frame)

        self.protocol.do_handshake()

        # the bytes that follow the headers belong to the frames that come
        # after the handshake, so they are kept for the parsing that follows
        self.assertEqual(self.protocol.get_buffer(), frame)

    def test_do_handshake_partial(self):
        self.protocol.add_buffer(RESPONSE[:30])

        # an answer whose headers have not been completely received yet
        # cannot be handled, which is reported so that it may be retried
        self.assertRaises(netius.DataError, self.protocol.do_handshake)

    def test_do_handshake_repeated(self):
        self.protocol.add_buffer(RESPONSE)
        self.protocol.do_handshake()

        # the handshake of a protocol happens once alone, so a second
        # attempt at it is refused instead of resetting the state
        self.assertRaises(netius.NetiusError, self.protocol.do_handshake)

    def test_validate_key(self):
        self.protocol.add_buffer(RESPONSE)
        self.protocol.do_handshake()

        # the accept key of the answer is the one that the specification
        # names for the key that was offered, so it validates
        self.assertEqual(self.protocol.validate_key(), None)

    def test_validate_key_missing(self):
        self.protocol.add_buffer(
            b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\n"
        )
        self.protocol.do_handshake()

        # an answer that names no accept key proves nothing, so it is
        # refused instead of being taken for a valid handshake
        self.assertRaises(netius.NetiusError, self.protocol.validate_key)

    def test_validate_key_invalid(self):
        self.protocol.add_buffer(
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Sec-WebSocket-Accept: aW52YWxpZCBhY2NlcHQga2V5\r\n\r\n"
        )
        self.protocol.do_handshake()

        # an accept key that does not follow from the key that was offered
        # is refused, as it does not prove that the peer read the request
        self.assertRaises(netius.SecurityError, self.protocol.validate_key)
