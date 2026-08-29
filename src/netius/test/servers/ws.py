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

import logging
import unittest

import netius
import netius.servers

from netius.servers import ws

REQUEST = (
    b"GET /chat HTTP/1.1\r\n"
    b"Host: localhost\r\n"
    b"Upgrade: websocket\r\n"
    b"Connection: Upgrade\r\n"
    b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    b"Sec-WebSocket-Version: 13\r\n\r\n"
)
""" The upgrade request of the example of the RFC 6455, whose key
is the one that the specification uses to demonstrate the accept
key that a server has to answer with """

ACCEPT_KEY = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
""" The accept key that the RFC 6455 names as the answer to the
key of the request above, used as the vector of the handshake """


class WSConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.WSServer(level=logging.CRITICAL)
        self.connection = self._make_connection()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_send_ws(self):
        self.connection.send_ws(b"Hello World")

        # the payload that a server sends is never masked, as the masking
        # is only applied to the frames that travel towards it
        decoded, remaining = netius.common.decode_ws(self._data())
        self.assertEqual(decoded, b"Hello World")
        self.assertEqual(remaining, b"")

    def test_add_buffer(self):
        self.connection.add_buffer(b"first")
        self.connection.add_buffer(b"second")

        # the buffer joins the reads that it gathers and is emptied by the
        # reading of it, so that the data is only handled once
        self.assertEqual(self.connection.get_buffer(), b"firstsecond")
        self.assertEqual(self.connection.get_buffer(), b"")

    def test_get_buffer_keep(self):
        self.connection.add_buffer(b"first")

        # the reading may keep the buffer in place, which the handshake
        # needs so that the data is still there for a second attempt
        self.assertEqual(self.connection.get_buffer(delete=False), b"first")
        self.assertEqual(self.connection.get_buffer(), b"first")

    def test_do_handshake(self):
        self.connection.add_buffer(REQUEST)

        self.connection.do_handshake()

        # the request line and the headers of the upgrade are gathered, the
        # names of the headers being lowered so that they may be resolved
        self.assertEqual(self.connection.handshake, True)
        self.assertEqual(self.connection.method, "GET")
        self.assertEqual(self.connection.path, "/chat")
        self.assertEqual(self.connection.version, "HTTP/1.1")
        self.assertEqual(self.connection.headers["upgrade"], "websocket")
        self.assertEqual(
            self.connection.headers["sec-websocket-key"], "dGhlIHNhbXBsZSBub25jZQ=="
        )

    def test_do_handshake_remaining(self):
        frame = netius.common.encode_ws(b"Hello World")
        self.connection.add_buffer(REQUEST + frame)

        self.connection.do_handshake()

        # the bytes that follow the headers belong to the frames that come
        # after the handshake, so they are kept for the parsing that follows
        self.assertEqual(self.connection.get_buffer(), frame)

    def test_do_handshake_partial(self):
        self.connection.add_buffer(REQUEST[:40])

        # a handshake whose headers have not been completely received yet
        # cannot be performed, which is reported so that it may be retried
        self.assertRaises(netius.DataError, self.connection.do_handshake)

    def test_do_handshake_repeated(self):
        self.connection.add_buffer(REQUEST)
        self.connection.do_handshake()

        # the handshake of a connection happens once alone, so a second
        # attempt at it is refused instead of resetting the state
        self.assertRaises(netius.NetiusError, self.connection.do_handshake)

    def test_accept_key(self):
        self.connection.add_buffer(REQUEST)
        self.connection.do_handshake()

        # the accept key is the one that the specification names for the
        # key of the request, which is the vector of the handshake
        self.assertEqual(self.connection.accept_key(), ACCEPT_KEY)

    def test_accept_key_missing(self):
        self.connection.add_buffer(b"GET /chat HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.connection.do_handshake()

        # a request that names no key cannot be answered, as there is
        # nothing from which the accept key may be built
        self.assertRaises(netius.NetiusError, self.connection.accept_key)

    def _make_connection(self):
        # builds a connection without the underlying socket, replacing the
        # sending by one that gathers the payload that would reach the client
        connection = ws.WSConnection(
            owner=self.server, socket=None, address=("127.0.0.1", 9090)
        )
        connection.data = []
        connection.send = lambda data, **kwargs: connection.data.append(
            netius.legacy.bytes(data)
        )
        return connection

    def _data(self):
        return b"".join(self.connection.data)


class WSServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.WSServer(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test__handshake_response(self):
        result = self.server._handshake_response(ACCEPT_KEY)

        # the answer of the handshake names the upgrade that was accepted
        # together with the key that proves it, ending in an empty line
        self.assertEqual(result.startswith("HTTP/1.1 101"), True)
        self.assertEqual("Upgrade: websocket\r\n" in result, True)
        self.assertEqual("Sec-WebSocket-Accept: " + ACCEPT_KEY in result, True)
        self.assertEqual(result.endswith("\r\n\r\n"), True)
