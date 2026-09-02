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
import socket
import logging
import unittest

import netius
import netius.servers

from netius.base import conn

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class SOCKSConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.loop = netius.Base(level=logging.CRITICAL)

        # the poll is opened by hand as the loop is never started, and the
        # opening of a connection registers the socket of it in the poll
        self.loop.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.loop.poll.close()
        self.loop.close()

    def test_open(self):
        connection = self._make_connection()
        try:
            # the parser of the protocol is built with the connection and the
            # two events that drive it are bound to it
            self.assertNotEqual(connection.parser, None)
            self.assertEqual("on_data" in connection.parser.events, True)
            self.assertEqual("on_auth" in connection.parser.events, True)
        finally:
            connection.socket.close()

    def test_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        parser = connection.parser

        with mock.patch.object(parser, "destroy") as destroy:
            connection.close()

        # the parser is released with the connection, as holding it would
        # keep the buffers of it alive for as long as the loop is
        self.assertEqual(destroy.called, True)

    def test_send_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        try:
            with mock.patch.object(connection, "send") as send:
                connection.send_response()

            # the reply of the fourth version is a fixed sequence of eight
            # bytes, led by the null that names the version of the reply
            data = send.call_args[0][0]
            self.assertEqual(len(data), 8)
            self.assertEqual(
                struct.unpack("!BBHI", data),
                (0, netius.servers.socks.GRANTED, 0, 0),
            )
        finally:
            connection.socket.close()

    def test_send_response_extra(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        try:
            connection.parser.version = 0x05
            connection.parser.type = 0x01
            connection.parser.port = 8080

            with mock.patch.object(
                connection.parser, "get_address", return_value=b"\x7f\x00\x00\x01"
            ):
                with mock.patch.object(connection, "send") as send:
                    connection.send_response_extra()

            # the reply of the fifth version carries the address that was
            # asked for and the port of it, after the status of the request
            data = send.call_args[0][0]
            version, status, _reserved, type = struct.unpack("!BBBB", data[:4])
            self.assertEqual(version, 0x05)
            self.assertEqual(status, netius.servers.socks.GRANTED_EXTRA)
            self.assertEqual(type, 0x01)
            self.assertEqual(struct.unpack("!H", data[-2:])[0], 8080)
        finally:
            connection.socket.close()

    def test_send_auth(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        try:
            connection.parser.version = 0x05

            with mock.patch.object(connection, "send") as send:
                connection.send_auth()

            # the version of the parser is the one answered with when none is
            # named, so that the peer is answered in the one it spoke
            self.assertEqual(struct.unpack("!BB", send.call_args[0][0]), (0x05, 0))

            with mock.patch.object(connection, "send") as send:
                connection.send_auth(version=0x04, method=0xFF)

            self.assertEqual(struct.unpack("!BB", send.call_args[0][0]), (0x04, 0xFF))
        finally:
            connection.socket.close()

    def test_get_version(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        try:
            connection.parser.version = 0x05

            # both the version and the parsing are answered by the parser, the
            # connection being only the way to it
            self.assertEqual(connection.get_version(), 0x05)

            with mock.patch.object(connection.parser, "parse") as parse:
                connection.parse(b"data")

            self.assertEqual(parse.call_args[0][0], b"data")
        finally:
            connection.socket.close()

    def test_on_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        try:
            owner = mock.MagicMock()
            connection.owner = owner

            connection.on_data()
            connection.on_auth()

            # both of the events of the parser are relayed to the service,
            # which is the one that acts on them
            self.assertEqual(owner.on_data_socks.call_args[0][0], connection)
            self.assertEqual(owner.on_auth_socks.call_args[0][1], connection.parser)
        finally:
            connection.socket.close()

    def _make_connection(self):
        # builds an open connection of the protocol registered in the loop, so
        # that the parser of it is built as it would be in a service
        _socket = socket.socket()
        connection = netius.servers.socks.SOCKSConnection(
            owner=self.loop, socket=_socket
        )
        self.loop.connections.append(connection)
        self.loop.connections_m[_socket] = connection
        connection.open()
        return connection
