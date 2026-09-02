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
import netius.clients
import netius.servers

from netius.base import conn

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class SOCKSConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.loop = netius.Base(level=logging.CRITICAL)

        # the poll is stood in for, as the opening of a connection registers
        # the socket of it in one and the loop is never started
        self.loop.poll = mock.MagicMock()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
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
        connection = self._make_connection()
        parser = connection.parser

        with mock.patch.object(parser, "destroy") as destroy:
            connection.close()

        # the parser is released with the connection, as holding it would
        # keep the buffers of it alive for as long as the loop is
        self.assertEqual(destroy.called, True)

    def test_send_response(self):
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


class SOCKSServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server = netius.servers.SOCKSServer(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        # the service is a container one, the raw client that opens the other
        # end of a tunnel being a base of it alongside the service itself
        self.assertEqual(isinstance(self.server, netius.ContainerServer), True)
        self.assertEqual(
            isinstance(self.server.raw_client, netius.clients.RawClient), True
        )
        self.assertEqual(
            [base.name for base in self.server.container.bases],
            ["SOCKSServer", "RawClient"],
        )

        # the three events of the raw client are the ones that drive the
        # bridging, so all of them must have been bound
        for name in ("connect", "data", "close"):
            self.assertEqual(name in self.server.raw_client.events, True)

        # the pending bounds are taken from the maximum that was asked for,
        # the minimum being the ratio of it that resumes the reading
        server = netius.servers.SOCKSServer(max_pending=1024, level=logging.CRITICAL)
        try:
            self.assertEqual(server.max_pending, 1024)
            self.assertEqual(
                server.min_pending, int(1024 * netius.servers.socks.MIN_RATIO)
            )
        finally:
            server.cleanup()

    def test_cleanup(self):
        server = netius.servers.SOCKSServer(level=logging.CRITICAL)

        with mock.patch.object(server.raw_client, "destroy") as destroy:
            server.cleanup()

        # the client that backs the tunnels is released with the service, as
        # the container that holds both of them is torn down at once
        self.assertEqual(destroy.called, True)
        self.assertEqual(server.container, None)

        # a service that has already been cleaned up has no container left to
        # be torn down, and asking for it again must not raise
        self.assertEqual(server.cleanup(), None)

    def test_on_data(self):
        connection = mock.MagicMock()
        del connection.tunnel_c

        self.server.on_data(connection, b"data")

        # a connection with no tunnel behind it is still under the handshake,
        # so the data is given to the parser and nothing is bridged
        self.assertEqual(connection.parse.call_args[0][0], b"data")

        connection = mock.MagicMock()
        connection.tunnel_c.is_exhausted.return_value = False

        self.server.on_data(connection, b"data")

        # once the tunnel is up the data is relayed to it, under a buffer that
        # is not full there being no reason to stop reading
        self.assertEqual(connection.disable_read.called, False)
        self.assertEqual(connection.tunnel_c.send.call_args[0][0], b"data")
        self.assertEqual(
            connection.tunnel_c.send.call_args[1]["callback"], self.server._throttle
        )

        connection = mock.MagicMock()
        connection.tunnel_c.is_exhausted.return_value = True

        self.server.on_data(connection, b"data")

        # a tunnel whose buffer is exhausted puts the reading of this end on
        # hold, or the producer would starve the consumer
        self.assertEqual(connection.disable_read.called, True)

        connection = mock.MagicMock()
        connection.tunnel_c.is_exhausted.return_value = True
        self.server.throttle = False

        self.server.on_data(connection, b"data")

        # with the throttling turned off the buffer is left to grow, the
        # reading of the connection never being put on hold
        self.assertEqual(connection.disable_read.called, False)

    def test_on_data_socks(self):
        connection = mock.MagicMock()
        parser = mock.MagicMock()
        parser.get_host.return_value = "host.domain"
        parser.port = 8080

        _connection = mock.MagicMock()

        with mock.patch.object(
            self.server.raw_client, "connect", return_value=_connection
        ) as connect:
            self.server.on_data_socks(connection, parser)

        # the host and the port that the peer asked for are the ones that the
        # other end of the tunnel is opened against
        self.assertEqual(connect.call_args[0], ("host.domain", 8080))

        # the bounds of the service are carried to the tunnel and the two ends
        # are paired, in both of the directions of the mapping
        self.assertEqual(_connection.max_pending, self.server.max_pending)
        self.assertEqual(_connection.min_pending, self.server.min_pending)
        self.assertEqual(connection.tunnel_c, _connection)
        self.assertEqual(self.server.conn_map[_connection], connection)

    def test_on_auth_socks(self):
        connection = mock.MagicMock()
        parser = mock.MagicMock()
        parser.auth_methods = (0, 2)

        self.server.on_auth_socks(connection, parser)

        # the only method that the service supports is the one that asks for
        # no authentication, which is the one answered with
        self.assertEqual(connection.send_auth.call_args[1]["method"], 0)

        parser.auth_methods = (2,)

        # a peer that does not offer the method that is supported cannot be
        # served, so the request of it must be refused
        self.assertRaises(
            netius.ParserError, self.server.on_auth_socks, connection, parser
        )

    def test_on_connection_d(self):
        connection = mock.MagicMock()
        tunnel_c = connection.tunnel_c

        self.server.on_connection_d(connection)

        # the closing of one of the ends takes the other one with it, as a
        # tunnel with a single end left has nothing to bridge
        self.assertEqual(tunnel_c.close.called, True)
        self.assertEqual(connection.tunnel_c, None)

        connection = mock.MagicMock()
        del connection.tunnel_c

        # a connection that never reached the tunnel stage has no other end to
        # be closed, and must not raise on the way out
        self.assertEqual(self.server.on_connection_d(connection), None)
        self.assertEqual(connection.tunnel_c, None)

    def test_build_connection(self):
        _socket = socket.socket()
        try:
            connection = self.server.build_connection(_socket, ("host.domain", 8080))

            # the connection that the service builds is the one of the protocol
            # and it carries the bounds that the throttling reads
            self.assertEqual(
                isinstance(connection, netius.servers.socks.SOCKSConnection), True
            )
            self.assertEqual(connection.owner, self.server)
            self.assertEqual(connection.max_pending, self.server.max_pending)
            self.assertEqual(connection.min_pending, self.server.min_pending)
        finally:
            _socket.close()

    def test__throttle(self):
        _connection = mock.MagicMock()
        _connection.is_restored.return_value = False

        # an end whose buffer still holds data is under back pressure, so the
        # throttling of the end that faces it must remain in place
        self.assertEqual(self.server._throttle(_connection), None)

        _connection = mock.MagicMock()
        _connection.is_restored.return_value = True

        # an end that is no longer mapped (eg: one under a graceful close) has
        # no other end left to be resumed
        self.assertEqual(self.server._throttle(_connection), None)

        connection = mock.MagicMock()
        connection.renable = False
        self.server.conn_map[_connection._protocol] = connection

        with mock.patch.object(self.server, "reads") as reads:
            self.server._throttle(_connection)

        # the protocol is what stands for the end under the new architecture,
        # so it is the key under which the other end is found
        self.assertEqual(connection.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

        connection.enable_read.reset_mock()
        connection.renable = True

        # an end whose reading was never turned off has nothing to be turned
        # back on, so it is left as it is
        self.assertEqual(self.server._throttle(_connection), None)
        self.assertEqual(connection.enable_read.called, False)

    def test__raw_throttle(self):
        connection = mock.MagicMock()
        connection.is_restored.return_value = False

        # the same back pressure gate as the one of the other direction, an
        # end that is not restored asking for nothing
        self.assertEqual(self.server._raw_throttle(connection), None)

        connection = mock.MagicMock()
        connection.is_restored.return_value = True
        del connection.tunnel_c

        # a connection that carries no tunnel has no other end whose reading
        # could be resumed
        self.assertEqual(self.server._raw_throttle(connection), None)

        connection = mock.MagicMock()
        connection.is_restored.return_value = True
        connection.tunnel_c.renable = True

        # a tunnel whose reading was never turned off is left as it is
        self.assertEqual(self.server._raw_throttle(connection), None)
        self.assertEqual(connection.tunnel_c.enable_read.called, False)

        connection = mock.MagicMock()
        connection.is_restored.return_value = True
        connection.tunnel_c.renable = False

        with mock.patch.object(self.server, "reads") as reads:
            self.server._raw_throttle(connection)

        # with the buffer of the connection drained the reading of the tunnel
        # that feeds it is turned back on
        self.assertEqual(connection.tunnel_c.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

    def test__on_raw_connect(self):
        connection = mock.MagicMock()
        connection.get_version.return_value = 0x04
        _connection = mock.MagicMock()
        self.server.conn_map[_connection] = connection

        self.server._on_raw_connect(self.server.raw_client, _connection)

        # the fourth version is answered with the plain reply, granting the
        # request that opened the tunnel
        self.assertEqual(
            connection.send_response.call_args[1]["status"],
            netius.servers.socks.GRANTED,
        )

        connection.get_version.return_value = 0x05

        self.server._on_raw_connect(self.server.raw_client, _connection)

        # the fifth version carries the address back, so the reply of it is
        # the extended one
        self.assertEqual(
            connection.send_response_extra.call_args[1]["status"],
            netius.servers.socks.GRANTED_EXTRA,
        )

        connection.send_response.reset_mock()
        connection.send_response_extra.reset_mock()
        connection.get_version.return_value = 0x06

        self.server._on_raw_connect(self.server.raw_client, _connection)

        # a version that is neither of the two that are spoken is answered
        # with none of the replies
        self.assertEqual(connection.send_response.called, False)
        self.assertEqual(connection.send_response_extra.called, False)

    def test__on_raw_data(self):
        connection = mock.MagicMock()
        connection.is_exhausted.return_value = False
        _connection = mock.MagicMock()
        self.server.conn_map[_connection] = connection

        self.server._on_raw_data(self.server.raw_client, _connection, b"data")

        # the data that comes from the tunnel is written to the peer, under a
        # buffer that is not full the tunnel keeping on being read
        self.assertEqual(_connection.disable_read.called, False)
        self.assertEqual(connection.send.call_args[0][0], b"data")
        self.assertEqual(
            connection.send.call_args[1]["callback"], self.server._raw_throttle
        )

        connection.is_exhausted.return_value = True

        self.server._on_raw_data(self.server.raw_client, _connection, b"data")

        # a peer whose buffer is exhausted puts the reading of the tunnel on
        # hold, which is the other direction of the same throttling
        self.assertEqual(_connection.disable_read.called, True)

        _connection.disable_read.reset_mock()
        self.server.throttle = False

        self.server._on_raw_data(self.server.raw_client, _connection, b"data")

        # with the throttling turned off the reading of the tunnel is never
        # put on hold, whatever the buffer of the peer holds
        self.assertEqual(_connection.disable_read.called, False)

    def test__on_raw_close(self):
        connection = mock.MagicMock()
        _connection = mock.MagicMock()
        self.server.conn_map[_connection] = connection

        self.server._on_raw_close(self.server.raw_client, _connection)

        # the closing of the tunnel takes the peer with it, flushed so that
        # what is still pending reaches it, and the pairing is dropped
        self.assertEqual(connection.close.call_args[1]["flush"], True)
        self.assertEqual(_connection in self.server.conn_map, False)
