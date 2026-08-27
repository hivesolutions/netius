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

import socket
import logging
import unittest
import threading

import netius

from netius.base import conn
from netius.base import common
from netius.base import server

try:
    import unittest.mock as mock
except ImportError:
    mock = None

ADDRESS = ("127.0.0.1", 9090)


class ServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.DatagramServer(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_cleanup(self):
        self.server.socket = self.server.socket_udp()

        self.server.cleanup()

        # the service socket is closed and released, as it's the one that
        # has no connection associated with it
        self.assertEqual(self.server.socket, None)

    def test_cleanup_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.Mock()
        _socket.close.side_effect = socket.error("Already closed")
        self.server.socket = _socket

        # a socket that fails to close is not able to break the cleanup, as
        # by then there's nothing left to be done about it
        self.server.cleanup()

        self.assertEqual(self.server.socket, None)

    def test_info_dict(self):
        info = self.server.info_dict()

        self.assertEqual(info["host"], self.server.host)
        self.assertEqual(info["port"], self.server.port)
        self.assertEqual(info["type"], self.server.type)
        self.assertEqual(info["ssl"], self.server.ssl)

    def test_socket_udp(self):
        _socket = self.server.socket_udp()
        try:
            # the service socket is a non blocking one, as the reading of it
            # is driven by the poll instead of by a blocking call, note that
            # the timeout is the way of telling it under the oldest runtimes
            self.assertEqual(_socket.family, socket.AF_INET)
            self.assertEqual(_socket.type, socket.SOCK_DGRAM)
            self.assertEqual(_socket.gettimeout(), 0)
            self.assertNotEqual(
                _socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0
            )
            self.assertNotEqual(
                _socket.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST), 0
            )
        finally:
            _socket.close()

    def test_on_serve(self):
        # the serve notification is an extension point with no default
        # behaviour, so that a sub class may hook into it
        self.server.on_serve()


class DatagramServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.DatagramServer(level=logging.CRITICAL)
        self.server.socket = self.server.socket_udp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        self.assertEqual(self.server.renable, True)
        self.assertEqual(self.server.wready, True)
        self.assertEqual(self.server.pending_s, 0)
        self.assertEqual(len(self.server.pending), 0)

    def test_reads(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "on_read") as on_read:
            self.server.reads((1, 2), state=False)

        # every ready socket is handed over to the read handler, as a
        # datagram server has a single socket for the complete service
        self.assertEqual(self._sockets(on_read), [1, 2])

    def test_writes(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "on_write") as on_write:
            self.server.writes((1, 2), state=False)

        self.assertEqual(self._sockets(on_write), [1, 2])

    def test_errors(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "on_error") as on_error:
            self.server.errors((1, 2), state=False)

        self.assertEqual(self._sockets(on_error), [1, 2])

    def test_serve(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(server.Server, "serve") as serve:
            self.server.serve()

        # a datagram server is bound to a datagram socket, so the type of
        # the service is overridden before it reaches the base server
        self.assertEqual(serve.call_args[1]["type"], common.UDP_TYPE)

    def test_on_exception(self):
        # both the unexpected and the expected exceptions are only logged,
        # as a datagram server has no connection to be closed
        self.server.on_exception(netius.NetiusError("boom"))
        self.server.on_expected(netius.NetiusError("broken pipe"))

    def test_on_data(self):
        # the default handling of the data is a no operation, the payload
        # is meant to be consumed by a sub class instead
        self.server.on_data(ADDRESS, b"Hello World")

    def test_ensure_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.tid = threading.current_thread().ident

        with mock.patch.object(self.server, "sub_write") as sub_write:
            self.server.ensure_write()

        # the socket of the server is the one that gets subscribed, as a
        # datagram server has a single socket for the complete service
        self.assertEqual(sub_write.call_count, 1)
        self.assertEqual(sub_write.call_args[0][0], self.server.socket)

    def test_ensure_write_unsafe(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a subscription requested from a thread other than the loop one is
        # not safe, so it must be deferred instead of run right away
        with mock.patch.object(self.server, "sub_write") as sub_write:
            self.server.ensure_write()

        self.assertEqual(sub_write.call_count, 0)
        self.assertEqual(len(self.server._delayed), 1)

    def test_remove_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "unsub_write") as unsub_write:
            self.server.remove_write()

        self.assertEqual(unsub_write.call_count, 1)
        self.assertEqual(unsub_write.call_args[0][0], self.server.socket)

    def test_enable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.renable = False

        with mock.patch.object(self.server, "sub_read") as sub_read:
            self.server.enable_read()

        self.assertEqual(self.server.renable, True)
        self.assertEqual(sub_read.call_count, 1)
        self.assertEqual(sub_read.call_args[0][0], self.server.socket)

    def test_enable_read_enabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a server that is already reading must not be subscribed once again
        # as that would be a duplicated registration in the poll
        with mock.patch.object(self.server, "sub_read") as sub_read:
            self.server.enable_read()

        self.assertEqual(sub_read.call_count, 0)

    def test_disable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "unsub_read") as unsub_read:
            self.server.disable_read()

        self.assertEqual(self.server.renable, False)
        self.assertEqual(unsub_read.call_count, 1)
        self.assertEqual(unsub_read.call_args[0][0], self.server.socket)

    def test_disable_read_disabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.renable = False

        with mock.patch.object(self.server, "unsub_read") as unsub_read:
            self.server.disable_read()

        self.assertEqual(unsub_read.call_count, 0)

    def test_send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.tid = threading.current_thread().ident

        with mock.patch.object(self.server, "_flush_write") as flush_write:
            self.server.send(b"Hello World", ADDRESS, delay=False)

        # the payload is queued together with the address it targets and
        # the pending counter grows by the size of the payload
        self.assertEqual(self.server.pending[0], (b"Hello World", ADDRESS))
        self.assertEqual(self.server.pending_s, 11)
        self.assertEqual(flush_write.call_count, 1)

    def test_send_callback(self):
        self.server.tid = threading.current_thread().ident
        callback = lambda connection: None

        self.server.send(b"Hello World", ADDRESS, callback=callback)

        # the callback travels alongside the payload, so that it's called
        # once the payload has been handed over to the socket
        data, address = self.server.pending[0]

        self.assertEqual(data, (b"Hello World", callback))
        self.assertEqual(address, ADDRESS)

    def test_send_delayed(self):
        self.server.tid = threading.current_thread().ident

        # a sending that is not immediate is deferred to the next tick, so
        # that multiple payloads are flushed in a single operation
        self.server.send(b"Hello World", ADDRESS)

        self.assertEqual(len(self.server.pending), 1)
        self.assertEqual(len(self.server._delayed), 1)

    def test_send_busy(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.tid = threading.current_thread().ident
        self.server.wready = False

        # a socket that is not ready for writing must be subscribed for the
        # write event instead of being flushed right away
        with mock.patch.object(self.server, "ensure_write") as ensure_write:
            self.server.send(b"Hello World", ADDRESS)

        self.assertEqual(ensure_write.call_count, 1)
        self.assertEqual(len(self.server.pending), 1)

    def test__flush_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server, "writes") as writes:
            self.server._flush_write()

        # the flushing is a write notification for the service socket that
        # does not change the state of the loop
        self.assertEqual(writes.call_args[0][0], (self.server.socket,))
        self.assertEqual(writes.call_args[1]["state"], False)

    def _sockets(self, handler):
        # gathers the sockets that have been handed over to the handler, so
        # that both the count and the identity of them may be verified
        return [call[0][0] for call in handler.call_args_list]


class StreamServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.StreamServer(level=logging.CRITICAL)
        self.server.socket = socket.socket()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_reads(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = socket.socket()
        try:
            with mock.patch.object(self.server, "on_read_s") as on_read_s:
                with mock.patch.object(self.server, "on_read") as on_read:
                    self.server.reads((self.server.socket, _socket), state=False)
        finally:
            _socket.close()

        # the service socket announces a new connection while any other one
        # announces data, so each of them must reach its own handler and
        # never the one of the other, which would accept instead of read
        self.assertEqual(on_read_s.call_args[0][0], self.server.socket)
        self.assertEqual(on_read.call_args[0][0], _socket)

    def test_writes(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = socket.socket()
        try:
            with mock.patch.object(self.server, "on_write_s") as on_write_s:
                with mock.patch.object(self.server, "on_write") as on_write:
                    self.server.writes((self.server.socket, _socket), state=False)
        finally:
            _socket.close()

        self.assertEqual(on_write_s.call_args[0][0], self.server.socket)
        self.assertEqual(on_write.call_args[0][0], _socket)

    def test_errors(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = socket.socket()
        try:
            with mock.patch.object(self.server, "on_error_s") as on_error_s:
                with mock.patch.object(self.server, "on_error") as on_error:
                    self.server.errors((self.server.socket, _socket), state=False)
        finally:
            _socket.close()

        self.assertEqual(on_error_s.call_args[0][0], self.server.socket)
        self.assertEqual(on_error.call_args[0][0], _socket)

    def test_on_write_s(self):
        # the service socket handlers for writing and for errors are
        # extension points with no default behaviour
        self.server.on_write_s(self.server.socket)
        self.server.on_error_s(self.server.socket)

    def test_on_exception(self):
        connection = self._make_connection()

        self.server.on_exception(netius.NetiusError("boom"), connection)

        # the closing must be identified as an error driven one, carrying
        # the details of the exception that has originated it
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "boom")

    def test_on_exception_s(self):
        # an exception raised by the service socket has no connection to be
        # closed, so it's only logged
        self.server.on_exception_s(netius.NetiusError("boom"))
        self.server.on_expected_s(netius.NetiusError("broken pipe"))

    def test_on_expected(self):
        connection = self._make_connection()

        self.server.on_expected(netius.NetiusError("broken pipe"), connection)

        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "broken pipe")

    def test_on_upgrade(self):
        connection = self._make_connection()
        connection.upgrading = True
        upgraded = []
        connection.bind("upgrade", lambda _connection: upgraded.append(_connection))

        self.server.on_upgrade(connection)

        # the end of the upgrade releases the connection from the upgrading
        # state and notifies the observers through the upgrade event
        self.assertEqual(connection.is_upgrading(), False)
        self.assertEqual(upgraded, [connection])

    def test_on_data(self):
        connection = self._make_connection()
        received = []
        connection.bind("data", lambda _connection, data: received.append(data))

        self.server.on_data(connection, b"Hello World")

        self.assertEqual(received, [b"Hello World"])

    def test_on_socket_d(self):
        connection = self._make_connection()

        self.server.on_socket_d(connection.socket)

        # a socket that is no longer associated with a connection must be
        # gracefully ignored, as the connection may already be gone
        self.server.on_socket_d(socket.socket())

    def _make_connection(self):
        # builds an open connection registered in the server, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.server, socket=_socket)
        connection.status = conn.OPEN
        self.server.connections.append(connection)
        self.server.connections_m[_socket] = connection
        return connection
