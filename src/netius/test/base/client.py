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

import ssl
import errno
import socket
import logging
import unittest
import threading

import netius

from netius.base import conn
from netius.base import legacy
from netius.base import request
from netius.base import client as client_c

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ClientTest(unittest.TestCase):

    def test_get_client_s(self):
        client = netius.DatagramClient.get_client_s(level=logging.CRITICAL)
        try:
            # the static client is a singleton, so that a second request for
            # it re-uses the instance that has already been built
            self.assertEqual(
                netius.DatagramClient.get_client_s(level=logging.CRITICAL), client
            )
            self.assertEqual(netius.DatagramClient._client, client)
        finally:
            netius.DatagramClient.cleanup_s()
            netius.DatagramClient._client = None

    def test_cleanup_s(self):
        # the cleanup of a class that never built a static client must be
        # a no operation instead of an error
        netius.DatagramClient._client = None
        netius.DatagramClient.cleanup_s()

        self.assertEqual(netius.DatagramClient._client, None)

    def test_ensure_loop(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        client = netius.DatagramClient(level=logging.CRITICAL)
        try:
            with mock.patch.object(client_c, "BaseThread") as thread_c:
                client.ensure_loop()

            # the thread that runs the loop is built lazily, only once an
            # operation that requires the loop has been requested
            self.assertEqual(thread_c.call_count, 1)
            self.assertEqual(thread_c.call_args[1]["owner"], client)
            self.assertEqual(thread_c.return_value.start.call_count, 1)
            self.assertEqual(client._thread, thread_c.return_value)

            with mock.patch.object(client_c, "BaseThread") as thread_c:
                client.ensure_loop()

            # a client that already has a loop thread must not build a new
            # one, as that would leave the first one orphaned
            self.assertEqual(thread_c.call_count, 0)
        finally:
            client._thread = None
            client.close()

    def test_ensure_loop_threadless(self):
        client = netius.DatagramClient(level=logging.CRITICAL, thread=False)
        try:
            # a client that is not meant to run in its own thread must never
            # build one, as the loop is driven by the caller instead
            client.ensure_loop()

            self.assertEqual(client._thread, None)
        finally:
            client.close()


class DatagramClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.DatagramClient(level=logging.CRITICAL)
        self.client.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.socket.close()
        self.client.close()

    def test_on_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        received = []
        self.client.socket = mock.MagicMock()
        self.client.socket.recvfrom.side_effect = [
            (b"hello", ("1.2.3.4", 1234)),
            socket.error(errno.EWOULDBLOCK, "error"),
        ]

        with mock.patch.object(
            self.client, "on_data", lambda a, d: received.append((a, d))
        ):
            self.client.on_read(self.client.socket)

        # the reading goes on until the queue of the kernel is empty, so that
        # a single wake up of the poll takes every datagram that arrived
        self.assertEqual(received, [(("1.2.3.4", 1234), b"hello")])

    def test_on_read_foreign(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.client.callbacks_m[_socket] = [callback]
        try:
            # a socket that is not the one of the client still notifies the
            # callbacks registered for it, and nothing else is done for it
            self.client.on_read(_socket)

            self.assertEqual(callback.call_args[0], ("read", _socket))
            self.assertEqual(_socket.recvfrom.called, False)
        finally:
            del self.client.callbacks_m[_socket]

    def test_on_read_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # an error that is expected is reported quietly, one that is part of
        # the retrying is ignored altogether, and any other one is reported as
        # the exception that it is
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
            (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
            (socket.error(errno.ECONNRESET, "error"), True, False),
            (socket.error(errno.EAGAIN, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            self.client.socket = mock.MagicMock()
            self.client.socket.recvfrom.side_effect = error

            with mock.patch.object(self.client, "on_expected") as on_expected:
                with mock.patch.object(self.client, "on_exception") as on_exception:
                    self.client.on_read(self.client.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        self.client.socket = mock.MagicMock()
        self.client.socket.recvfrom.side_effect = KeyboardInterrupt()

        self.assertRaises(KeyboardInterrupt, self.client.on_read, self.client.socket)

    def test_on_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.socket = mock.MagicMock()

        with mock.patch.object(self.client, "_send") as _send:
            self.client.on_write(self.client.socket)

        # the becoming writable of the socket is what drains the queue of the
        # datagrams that are waiting to be sent
        self.assertEqual(_send.call_args[0][0], self.client.socket)

        _socket = mock.MagicMock()

        with mock.patch.object(self.client, "_send") as _send:
            self.client.on_write(_socket)

        # a socket that is not the one of the client is not the one that the
        # queue belongs to, so nothing is drained for it
        self.assertEqual(_send.called, False)

    def test_on_write_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the sending classifies the failures exactly as the reading does,
        # which is what keeps the two sides of the socket consistent
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_ZERO_RETURN), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_WRITE), False, False),
            (socket.error(errno.EPIPE, "error"), True, False),
            (socket.error(errno.EAGAIN, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            self.client.socket = mock.MagicMock()

            with mock.patch.object(self.client, "_send", side_effect=error):
                with mock.patch.object(self.client, "on_expected") as on_expected:
                    with mock.patch.object(self.client, "on_exception") as on_exception:
                        self.client.on_write(self.client.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        self.client.socket = mock.MagicMock()

        with mock.patch.object(self.client, "_send", side_effect=SystemExit()):
            self.assertRaises(SystemExit, self.client.on_write, self.client.socket)

    def test_on_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.client.callbacks_m[_socket] = [callback]
        try:
            # a datagram socket carries no connection of its own, so the
            # notifying of the callbacks is the whole of the handling
            self.client.on_error(_socket)

            self.assertEqual(callback.call_args[0], ("error", _socket))
        finally:
            del self.client.callbacks_m[_socket]

        self.client.socket = mock.MagicMock()
        self.assertEqual(self.client.on_error(self.client.socket), None)

    def test_keep_gc(self):
        # the garbage collection re-schedules itself so that it keeps being
        # run for as long as the client is alive
        self.client.keep_gc(timeout=60, run=False)

        self.assertEqual(len(self.client._delayed), 1)

    def test_keep_gc_run(self):
        expired = request.Request(timeout=-1)
        self.client.add_request(expired)

        # the collection may also be run right away, instead of only being
        # scheduled for a later moment in time
        self.client.keep_gc(timeout=60)

        self.assertEqual(self.client.requests, [])
        self.assertEqual(len(self.client._delayed), 1)

    def test_gc(self):
        expired = request.Request(timeout=-1)
        pending = request.Request(timeout=60)
        self.client.add_request(expired)
        self.client.add_request(pending)

        self.client.gc()

        # only the request that has timed out is dropped, the one that is
        # still within its timeout must be kept for a later response
        self.assertEqual(self.client.requests, [pending])
        self.assertEqual(self.client.requests_m, {pending.id: pending})

    def test_gc_empty(self):
        # a client with no pending requests has nothing to collect, so the
        # operation must return before any bookkeeping is done
        self.client.gc()

        self.assertEqual(self.client.requests, [])

    def test_gc_callback(self):
        called = []
        expired = request.Request(
            timeout=-1, callback=lambda result: called.append(result)
        )
        self.client.add_request(expired)

        self.client.gc()

        # the callback of a timed out request is called with an invalid
        # value, so that the caller is able to tell the request has failed
        self.assertEqual(called, [None])

    def test_gc_no_callbacks(self):
        called = []
        expired = request.Request(
            timeout=-1, callback=lambda result: called.append(result)
        )
        self.client.add_request(expired)

        self.client.gc(callbacks=False)

        self.assertEqual(called, [])
        self.assertEqual(self.client.requests, [])

    def test_add_request(self):
        item = request.Request()
        self.client.add_request(item)

        # the request is kept both in the sequence used by the garbage
        # collection and in the map used for the response matching
        self.assertEqual(self.client.requests, [item])
        self.assertEqual(self.client.requests_m, {item.id: item})

    def test_remove_request(self):
        item = request.Request()
        self.client.add_request(item)

        self.client.remove_request(item)

        self.assertEqual(self.client.requests, [])
        self.assertEqual(self.client.requests_m, {})

    def test_get_request(self):
        item = request.Request()
        self.client.add_request(item)

        self.assertEqual(self.client.get_request(item.id), item)

        # a response may be used in place of an identifier, as the identifier
        # of the request that originated it is carried by it
        response = _MockResponse(b"", request=item)

        self.assertEqual(self.client.get_request(response), item)

        # an identifier that matches no request must yield an invalid value
        # instead of raising, as a response may be an unsolicited one
        self.assertEqual(self.client.get_request(-1), None)

    def test_ensure_socket(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the socket that the setup built is released, so that the building
        # of one is the operation under test
        self.client.socket.close()
        self.client.socket = None

        with mock.patch.object(self.client, "sub_all") as sub_all:
            self.client.ensure_socket()

        # the socket of a client never blocks and may reach every host of the
        # network, and it is registered in the poll once built
        self.assertEqual(self.client.socket.gettimeout(), 0.0)
        self.assertNotEqual(
            self.client.socket.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST), 0
        )
        self.assertEqual(sub_all.call_args[0][0], self.client.socket)

        _socket = self.client.socket

        with mock.patch.object(self.client, "sub_all") as sub_all:
            self.client.ensure_socket()

        # asking for it a second time is a no operation, a single socket being
        # the one that serves the whole of the client
        self.assertEqual(self.client.socket, _socket)
        self.assertEqual(sub_all.called, False)

    def test_ensure_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.socket = mock.MagicMock()
        self.client.tid = threading.current_thread().ident

        with mock.patch.object(self.client, "sub_write") as sub_write:
            self.client.ensure_write()

        # a request that comes from the thread of the loop registers for the
        # writing right away, as there is no race to be avoided
        self.assertEqual(sub_write.call_args[0][0], self.client.socket)

        self.client.tid = -1

        with mock.patch.object(self.client, "sub_write") as sub_write:
            with mock.patch.object(self.client, "delay") as delay:
                self.client.ensure_write()

        # one that comes from another thread is delayed into the loop instead,
        # as the poll may only be changed from the thread that owns it
        self.assertEqual(sub_write.called, False)
        self.assertEqual(delay.call_args[0][0], self.client.ensure_write)
        self.assertEqual(delay.call_args[1]["safe"], True)

    def test_remove_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "unsub_write") as unsub_write:
            self.client.remove_write()

        # the socket of the client is the one that gets unsubscribed, as a
        # datagram client has a single socket for the complete service
        self.assertEqual(unsub_write.call_count, 1)
        self.assertEqual(unsub_write.call_args[0][0], self.client.socket)

    def test_enable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.renable = False

        with mock.patch.object(self.client, "sub_read") as sub_read:
            self.client.enable_read()

        self.assertEqual(self.client.renable, True)
        self.assertEqual(sub_read.call_count, 1)
        self.assertEqual(sub_read.call_args[0][0], self.client.socket)

    def test_enable_read_enabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a client that is already reading must not be subscribed once again
        # as that would be a duplicated registration in the poll
        with mock.patch.object(self.client, "sub_read") as sub_read:
            self.client.enable_read()

        self.assertEqual(self.client.renable, True)
        self.assertEqual(sub_read.call_count, 0)

    def test_disable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "unsub_read") as unsub_read:
            self.client.disable_read()

        self.assertEqual(self.client.renable, False)
        self.assertEqual(unsub_read.call_count, 1)
        self.assertEqual(unsub_read.call_args[0][0], self.client.socket)

    def test_disable_read_disabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.renable = False

        with mock.patch.object(self.client, "unsub_read") as unsub_read:
            self.client.disable_read()

        self.assertEqual(self.client.renable, False)
        self.assertEqual(unsub_read.call_count, 0)


class StreamClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.StreamClient(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self._close_connections()
        self.client.close()

    def test_acquire_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        # a connection that is free in the pool must be re-used instead of
        # a new one being established for the same endpoint
        result = self.client.acquire_c("host", 80)

        self.assertEqual(result, connection)
        self.assertEqual(self.client.free_map[connection.tuple], [])

    def test_acquire_c_connect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "connect") as connect:
            result = self.client.acquire_c("host", 80)

        # with no connection free in the pool a new one has to be established
        # and tagged with the endpoint it belongs to, for a later re-usage
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(result.tuple, ("host", 80, False, None, None))

    def test_acquire_c_invalid(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        with mock.patch.object(self.client, "validate_c", return_value=False):
            with mock.patch.object(self.client, "connect") as connect:
                result = self.client.acquire_c("host", 80, validate=True)

        # a pooled connection that no longer validates must be dropped and a
        # new connection established in its place
        self.assertNotEqual(result, connection)
        self.assertEqual(connect.call_count, 1)

    def test_release_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)

        self.client.release_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [connection])

    def test_release_c_untied(self):
        connection = self._make_connection()

        # a connection that has never been acquired through the pool has no
        # endpoint tuple, so releasing it must be ignored
        self.client.release_c(connection)

        self.assertEqual(self.client.free_map, {})

    def test_remove_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [])

        # the removal of a connection that is no longer in the pool must be
        # a no operation, as it may have been removed by the closing of it
        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [])

    def test_remove_c_untied(self):
        connection = self._make_connection()

        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map, {})

    def test_validate_c(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()

        with mock.patch.object(
            connection,
            "recv",
            side_effect=[b"data", socket.error(errno.EWOULDBLOCK, "error")],
        ):
            with mock.patch.object(connection, "send"):
                result = self.client.validate_c(connection)

        # a connection that still answers is a usable one, the error that says
        # there is nothing more to read being the way out of the probing
        self.assertEqual(result, True)
        self.assertEqual(connection.status, conn.OPEN)

    def test_validate_c_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed(error=errno.ECONNRESET)

        with mock.patch.object(connection, "recv") as recv:
            result = self.client.validate_c(connection)

        # a socket that carries an error of its own is not usable, and it is
        # not even probed for data
        self.assertEqual(result, False)
        self.assertEqual(recv.called, False)

    def test_validate_c_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()

        with mock.patch.object(connection, "recv", return_value=b""):
            result = self.client.validate_c(connection)

        # a peer that closed the connection while it sat in the pool leaves an
        # empty read behind, and the connection is dropped for it
        self.assertEqual(result, False)
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)

    def test_validate_c_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # an error that merely says that there is nothing to read leaves the
        # connection as it is, under either of the two layers
        for error in (
            ssl.SSLError(ssl.SSL_ERROR_WANT_READ),
            socket.error(errno.EAGAIN, "error"),
        ):
            connection = self._make_probed()

            with mock.patch.object(connection, "recv", side_effect=error):
                result = self.client.validate_c(connection)

            self.assertEqual(result, True)
            self.assertEqual(connection.status, conn.OPEN)

    def test_validate_c_broken(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # one that says the connection is gone drops it, whichever of the two
        # layers reported it
        for error in (
            ssl.SSLError(ssl.SSL_ERROR_SSL),
            socket.error(errno.ECONNRESET, "error"),
        ):
            connection = self._make_probed()

            with mock.patch.object(connection, "recv", side_effect=error):
                result = self.client.validate_c(connection)

            self.assertEqual(result, False)
            self.assertEqual(connection.status, conn.CLOSED)

        # with the closing turned off the connection is only reported as
        # unusable, the caller being the one that decides what to do with it
        connection = self._make_probed()

        with mock.patch.object(
            connection, "recv", side_effect=socket.error(errno.ECONNRESET, "error")
        ):
            result = self.client.validate_c(connection, close=False)

        self.assertEqual(result, False)
        self.assertEqual(connection.status, conn.OPEN)

    def test_connect(self):
        connection = self.client.connect("host", 80, ensure_loop=False, env=False)

        # the connection is built but not yet established, so it waits in the
        # queue of the pending ones until the loop reaches it
        self.assertEqual(connection.address, ("host", 80))
        self.assertEqual(connection in self.client.pendings, True)

        # the socket of it never blocks and is told to keep itself alive, the
        # delaying of the small writes being off as well
        self.assertEqual(connection.socket.gettimeout(), 0.0)
        self.assertNotEqual(
            connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), 0
        )
        self.assertNotEqual(
            connection.socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 0
        )

    def test_connect_invalid(self):
        # a connection with no host or no port names no peer at all, so it is
        # refused instead of a socket being built for it
        self.assertRaises(
            netius.NetiusError, self.client.connect, None, 80, ensure_loop=False
        )
        self.assertRaises(
            netius.NetiusError, self.client.connect, "host", None, ensure_loop=False
        )

    def test_connect_unix(self):
        if not hasattr(socket, "AF_UNIX"):
            self.skipTest("Skipping test: Unix domain sockets unavailable")

        connection = self.client.connect(
            "unix", "/tmp/netius.sock", ensure_loop=False, env=False
        )

        # a peer named as of the domain of the machine is reached through a
        # path, which takes the place of the pair of the host and the port
        self.assertEqual(connection.socket.family, socket.AF_UNIX)
        self.assertEqual(connection.address, "/tmp/netius.sock")

    def test_connect_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(
            self.client, "_ssl_wrap", side_effect=lambda s, **kwargs: s
        ) as ssl_wrap:
            connection = self.client.connect(
                "host", 443, ssl=True, ssl_verify=True, ensure_loop=False, env=False
            )

        # the wrapping happens as the client side of the exchange and the host
        # travels with it, as it is the one the certificate is matched against
        self.assertEqual(ssl_wrap.call_args[1]["server"], False)
        self.assertEqual(ssl_wrap.call_args[1]["server_hostname"], "host")

        # the host is kept in the connection as well, so that the verification
        # may be run once the handshake is done
        self.assertEqual(connection.ssl_host, "host")

    def test_acquire(self):
        connection = self._make_connection()

        # the acquire notification is deferred to the next tick, so that it's
        # never run in the middle of the acquiring of the connection
        self.client.acquire(connection)

        self.assertEqual(len(self.client._delayed), 1)

    def test_on_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        received = []
        connection.bind("data", lambda _connection, data: received.append(data))

        with mock.patch.object(connection, "recv", side_effect=[b"hello", b""]):
            self.client.on_read(connection.socket)

        # every chunk that comes off the socket is handed over until the peer
        # closes it, which is what an empty read stands for
        self.assertEqual(received, [b"hello"])
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_CLIENT_EOF)

    def test_on_read_callbacks(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.client.callbacks_m[_socket] = [callback]
        try:
            # a socket that names no connection still notifies the callbacks
            # registered for it, as they are what a raw reader relies on
            self.client.on_read(_socket)

            self.assertEqual(callback.call_args[0], ("read", _socket))
        finally:
            del self.client.callbacks_m[_socket]

    def test_on_read_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a connection that is no longer open, or one whose reading was turned
        # off, is left alone instead of being read from
        for attribute, value in (("status", conn.CLOSED), ("renable", False)):
            connection = self._make_connection()
            setattr(connection, attribute, value)

            with mock.patch.object(connection, "recv") as recv:
                self.client.on_read(connection.socket)

            self.assertEqual(recv.called, False)

    def test_on_read_connecting(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.connecting = True

        with mock.patch.object(connection, "recv", side_effect=[b""]):
            with mock.patch.object(self.client, "_connectf") as connectf:
                self.client.on_read(connection.socket)

        # a connection that is still being established is finished before
        # anything is read from it, as the reading depends on it
        self.assertEqual(connectf.call_args[0][0], connection)

    def test_on_read_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # an error that is expected drops the connection quietly, one that is
        # part of the retrying is ignored altogether, and any other one is
        # reported as the exception that it is
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
            (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
            (socket.error(errno.ECONNRESET, "error"), True, False),
            (socket.error(errno.EWOULDBLOCK, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            connection = self._make_connection()

            with mock.patch.object(connection, "recv", side_effect=error):
                with mock.patch.object(self.client, "on_expected") as on_expected:
                    with mock.patch.object(self.client, "on_exception") as on_exception:
                        self.client.on_read(connection.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        connection = self._make_connection()

        with mock.patch.object(connection, "recv", side_effect=KeyboardInterrupt()):
            self.assertRaises(KeyboardInterrupt, self.client.on_read, connection.socket)

    def test_on_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        with mock.patch.object(connection, "_send") as _send:
            self.client.on_write(connection.socket)

        # a socket that became writable flushes whatever the connection still
        # holds in its buffer
        self.assertEqual(_send.called, True)

        connection = self._make_connection()
        connection.status = conn.CLOSED

        with mock.patch.object(connection, "_send") as _send:
            self.client.on_write(connection.socket)

        # one that is no longer open has nothing to flush, the buffer of it
        # having been dropped with the closing
        self.assertEqual(_send.called, False)

    def test_on_write_connecting(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.connecting = True

        with mock.patch.object(connection, "_send"):
            with mock.patch.object(self.client, "_connectf") as connectf:
                self.client.on_write(connection.socket)

        # the becoming writable of a socket is what says that a connection was
        # established, so it is finished before anything is sent
        self.assertEqual(connectf.call_args[0][0], connection)

    def test_on_write_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the sending classifies the failures exactly as the reading does,
        # which is what keeps the two sides of a connection consistent
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_ZERO_RETURN), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_WRITE), False, False),
            (socket.error(errno.EPIPE, "error"), True, False),
            (socket.error(errno.EAGAIN, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            connection = self._make_connection()

            with mock.patch.object(connection, "_send", side_effect=error):
                with mock.patch.object(self.client, "on_expected") as on_expected:
                    with mock.patch.object(self.client, "on_exception") as on_exception:
                        self.client.on_write(connection.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        connection = self._make_connection()

        with mock.patch.object(connection, "_send", side_effect=SystemExit()):
            self.assertRaises(SystemExit, self.client.on_write, connection.socket)

    def test_on_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.client.callbacks_m[_socket] = [callback]
        try:
            self.client.on_error(_socket)

            self.assertEqual(callback.call_args[0], ("error", _socket))
        finally:
            del self.client.callbacks_m[_socket]

        connection = self._make_connection()

        self.client.on_error(connection.socket)

        # a connection whose socket is in error is dropped, the reason naming
        # it so that the diagnostics may tell it apart
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)

        connection = self._make_connection()
        connection.status = conn.CLOSED

        # one that is already closed is left alone, instead of being closed a
        # second time
        self.client.on_error(connection.socket)

        self.assertEqual(connection.close_reason, None)

    def test_on_exception(self):
        connection = self._make_connection()
        self.client.on_exception(netius.NetiusError("boom"), connection)

        # the closing must be identified as an error driven one, carrying
        # the details of the exception that has originated it
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "boom")

    def test_on_expected(self):
        connection = self._make_connection()
        self.client.on_expected(netius.NetiusError("broken pipe"), connection)

        # an expected exception is still an error driven closing, as the
        # connection was not closed by a decision of the upper layers
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "broken pipe")

    def test_on_connect(self):
        connection = self._make_connection()
        connection.connecting = True

        self.client.on_connect(connection)

        # the establishment of a connection marks it as connected, which is
        # what releases the operations that were waiting on it
        self.assertEqual(connection.connecting, False)

    def test_on_connect_pooled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.connecting = True
        connection.tuple = ("host", 80, False, None, None)

        with mock.patch.object(self.client, "on_acquire") as on_acquire:
            self.client.on_connect(connection)

        # a connection that belongs to the pool is acquired as soon as it is
        # established, as the request that asked for it is waiting on it
        self.assertEqual(on_acquire.call_args[0][0], connection)

    def test_on_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.connecting = True

        with mock.patch.object(connection, "ssl_verify_host") as verify_host:
            with mock.patch.object(
                connection, "ssl_verify_fingerprint"
            ) as verify_fingerprint:
                with mock.patch.object(self.client, "on_connect") as on_connect:
                    self.client.on_ssl(connection)

        # the peer is verified as soon as the handshake is done, before the
        # connection is handed over to whatever asked for it
        self.assertEqual(verify_host.called, True)
        self.assertEqual(verify_fingerprint.called, True)
        self.assertEqual(on_connect.call_args[0][0], connection)

    def test_on_ssl_upgrading(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.connecting = False
        connection.upgrading = True

        with mock.patch.object(connection, "ssl_verify_host"):
            with mock.patch.object(connection, "ssl_verify_fingerprint"):
                with mock.patch.object(self.client, "on_upgrade") as on_upgrade:
                    self.client.on_ssl(connection)

        # a connection that was already established and became secure is an
        # upgraded one, and not a newly connected one
        self.assertEqual(on_upgrade.call_args[0][0], connection)

    def test_on_acquire(self):
        connection = self._make_connection()

        # the acquire and release notifications are extension points with no
        # default behaviour, so that a sub class may hook into them
        self.client.on_acquire(connection)
        self.client.on_release(connection)

        self.assertEqual(connection.status, conn.OPEN)

    def test_on_data(self):
        connection = self._make_connection()

        # the default handling of the data hands it over to the connection
        # so that it's dispatched through the data event
        received = []
        connection.bind("data", lambda _connection, data: received.append(data))
        self.client.on_data(connection, b"Hello World")

        self.assertEqual(received, [b"Hello World"])

    def test__connectf(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()

        with mock.patch.object(self.client, "on_connect") as on_connect:
            self.client._connectf(connection)

        # a connection that reached its peer is announced as connected and the
        # starters of it are run, there being none for a plain one
        self.assertEqual(on_connect.call_args[0][0], connection)

    def test__connectf_handshaking(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()
        connection.ssl_connecting = True

        with mock.patch.object(self.client, "on_connect") as on_connect:
            self.client._connectf(connection)

        # one that is already running the handshake has been through here
        # before, so nothing is done for it a second time
        self.assertEqual(on_connect.called, False)

    def test__connectf_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed(error=errno.ECONNREFUSED)

        with mock.patch.object(self.client, "on_error") as on_error:
            with mock.patch.object(self.client, "on_connect") as on_connect:
                self.client._connectf(connection)

        # a socket that carries an error never reached its peer, so it is
        # handled as a failed one instead of being announced as connected
        self.assertEqual(on_error.call_args[0][0], connection.socket)
        self.assertEqual(on_connect.called, False)

    def test__connectf_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()
        connection.ssl = True

        with mock.patch.object(connection, "add_starter") as add_starter:
            with mock.patch.object(self.client, "on_connect") as on_connect:
                self.client._connectf(connection)

        # a secure connection is only usable once the handshake has run, so it
        # is registered as the starter instead of being announced right away
        self.assertEqual(add_starter.call_args[0][0], self.client._ssl_handshake)
        self.assertEqual(on_connect.called, False)

    def test__connects(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        first, second = mock.MagicMock(), mock.MagicMock()
        self.client.pendings.extend((first, second))

        with mock.patch.object(self.client, "_connect") as _connect:
            self.client._connects()

        # every connection that was waiting is established and the queue is
        # left empty, so that a later tick does not reach them again
        self.assertEqual(_connect.call_count, 2)
        self.assertEqual(self.client.pendings, [])

    def test__connect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()
        connection.address = ("1.2.3.4", 1234)

        with mock.patch.object(self.client, "_connectf") as connectf:
            self.client._connect(connection)

        # the connection is opened before the reaching of the peer, and the
        # establishment is finished as soon as that one returns
        self.assertEqual(connection.socket.connect.call_args[0][0], connection.address)
        self.assertEqual(connectf.call_args[0][0], connection)

    def test__connect_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()
        connection.status = conn.CLOSED

        # a connection that was closed while it waited for its turn is left
        # alone, instead of a peer being reached for it
        self.client._connect(connection)

        self.assertEqual(connection.socket.connect.called, False)

    def test__connect_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # an error that merely says that the establishment is under way leaves
        # the connection open, the poll being the one that says when it has
        # finished
        for error in (
            ssl.SSLError(ssl.SSL_ERROR_WANT_WRITE),
            socket.error(errno.EINPROGRESS, "error"),
        ):
            connection = self._make_probed()
            connection.socket.connect.side_effect = error

            with mock.patch.object(self.client, "_connectf") as connectf:
                self.client._connect(connection)

            self.assertEqual(connection.status, conn.OPEN)
            self.assertEqual(connectf.called, False)

    def test__connect_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # one that says that the peer cannot be reached drops the connection,
        # naming the reason so that the caller may tell it apart
        for error in (
            ssl.SSLError(ssl.SSL_ERROR_SSL),
            socket.error(errno.ECONNREFUSED, "error"),
        ):
            connection = self._make_probed()
            connection.socket.connect.side_effect = error

            self.client._connect(connection)

            self.assertEqual(connection.status, conn.CLOSED)
            self.assertEqual(connection.close_reason, netius.REASON_ERROR)

    def test__connect_exception(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()
        connection.socket.connect.side_effect = ValueError("broken")

        # a failure that is none of the expected ones drops the connection and
        # still reaches the caller, as it names a defect and not a state of
        # the network
        self.assertRaises(ValueError, self.client._connect, connection)
        self.assertEqual(connection.status, conn.CLOSED)

        connection = self._make_probed()
        connection.socket.connect.side_effect = KeyboardInterrupt()

        self.assertRaises(KeyboardInterrupt, self.client._connect, connection)
        self.assertEqual(connection.status, conn.OPEN)

    def test__ssl_handshake(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_probed()

        with mock.patch.object(self.client, "on_ssl") as on_ssl:
            self.client._ssl_handshake(connection)

        # a handshake that completed makes the connection secure, which is
        # what the verification of the peer is run over
        self.assertEqual(connection.ssl_handshake, True)
        self.assertEqual(on_ssl.call_args[0][0], connection)

        connection = self._make_probed()
        connection.socket.do_handshake.side_effect = ssl.SSLError(
            ssl.SSL_ERROR_WANT_READ
        )

        with mock.patch.object(self.client, "is_sub_write", return_value=False):
            with mock.patch.object(self.client, "on_ssl") as on_ssl:
                self.client._ssl_handshake(connection)

        # one that is still under way is resumed by the poll, and nothing is
        # announced until it completes
        self.assertEqual(connection.ssl_handshake, False)
        self.assertEqual(on_ssl.called, False)

    def _make_connection(self):
        # builds an open connection registered in the client, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.client, socket=_socket)
        connection.status = conn.OPEN
        self.client.connections.append(connection)
        self.client.connections_m[_socket] = connection
        return connection

    def _make_probed(self, error=0):
        # builds an open connection whose socket is a stand-in, so that the
        # error it carries may be set (the reading of it cannot be replaced
        # on a real socket, being a read only method)
        connection = self._make_connection()
        connection.socket = mock.MagicMock()
        connection.socket.getsockopt.return_value = error
        return connection

    def _close_connections(self):
        # the closing of a client that has never been started is a no
        # operation, so the socket of a connection that the path under test
        # did not close by itself has to be released by hand
        for _socket in legacy.keys(self.client.connections_m):
            _socket.close()


class _MockResponse(request.Response):

    def get_id(self):
        return self.request.id
