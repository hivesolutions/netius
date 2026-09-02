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
            self.assertEqual(self._type(_socket), socket.SOCK_DGRAM)
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

    def _type(self, _socket):
        # under Linux the non blocking flag is part of the type of the
        # socket until Python 3.7, where it started being masked out, so
        # it has to be removed for the type to be comparable
        return _socket.type & ~getattr(socket, "SOCK_NONBLOCK", 0)


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

    def test_on_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        received = []
        self.server.socket = mock.MagicMock()
        self.server.socket.recvfrom.side_effect = [
            (b"hello", ("1.2.3.4", 1234)),
            socket.error(errno.EWOULDBLOCK, "error"),
        ]

        with mock.patch.object(
            self.server, "on_data", lambda a, d: received.append((a, d))
        ):
            self.server.on_read(self.server.socket)

        # the reading goes on until the queue of the kernel is empty, so that
        # a single wake up of the poll takes every datagram that arrived
        self.assertEqual(received, [(("1.2.3.4", 1234), b"hello")])

    def test_on_read_disabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.socket = mock.MagicMock()
        self.server.renable = False

        # a service whose reading was turned off is not read from, which is
        # what the throttling of it relies on
        self.server.on_read(self.server.socket)

        self.assertEqual(self.server.socket.recvfrom.called, False)

    def test_on_read_foreign(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.server.callbacks_m[_socket] = [callback]
        try:
            # a socket that is not the one of the service still notifies the
            # callbacks registered for it, and nothing else is done for it
            self.server.on_read(_socket)

            self.assertEqual(callback.call_args[0], ("read", _socket))
            self.assertEqual(_socket.recvfrom.called, False)
        finally:
            del self.server.callbacks_m[_socket]

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
            self.server.socket = mock.MagicMock()
            self.server.socket.recvfrom.side_effect = error

            with mock.patch.object(self.server, "on_expected") as on_expected:
                with mock.patch.object(self.server, "on_exception") as on_exception:
                    self.server.on_read(self.server.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        self.server.socket = mock.MagicMock()
        self.server.socket.recvfrom.side_effect = KeyboardInterrupt()

        self.assertRaises(KeyboardInterrupt, self.server.on_read, self.server.socket)

    def test_on_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.server.socket = mock.MagicMock()

        with mock.patch.object(self.server, "_send") as _send:
            self.server.on_write(self.server.socket)

        # the becoming writable of the socket is what drains the queue of the
        # datagrams that are waiting to be sent
        self.assertEqual(_send.call_args[0][0], self.server.socket)

        _socket = mock.MagicMock()

        with mock.patch.object(self.server, "_send") as _send:
            self.server.on_write(_socket)

        # a socket that is not the one of the service is not the one that the
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
            self.server.socket = mock.MagicMock()

            with mock.patch.object(self.server, "_send", side_effect=error):
                with mock.patch.object(self.server, "on_expected") as on_expected:
                    with mock.patch.object(self.server, "on_exception") as on_exception:
                        self.server.on_write(self.server.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        self.server.socket = mock.MagicMock()

        with mock.patch.object(self.server, "_send", side_effect=SystemExit()):
            self.assertRaises(SystemExit, self.server.on_write, self.server.socket)

    def test_on_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.server.callbacks_m[_socket] = [callback]
        try:
            # a datagram service carries no connection of its own, so the
            # notifying of the callbacks is the whole of the handling
            self.server.on_error(_socket)

            self.assertEqual(callback.call_args[0], ("error", _socket))
        finally:
            del self.server.callbacks_m[_socket]

        self.server.socket = mock.MagicMock()
        self.assertEqual(self.server.on_error(self.server.socket), None)

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

    def test__send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        callback = mock.MagicMock()
        _socket = mock.MagicMock()
        _socket.sendto.return_value = 5
        self.server.pending.appendleft(((b"hello", callback), ("1.2.3.4", 1234)))
        self.server.pending_s = 5

        with mock.patch.object(self.server, "remove_write"):
            self.server._send(_socket)

        # the datagram reaches the address that was named with it, and the
        # callback of it is run once the whole of it has been taken
        self.assertEqual(_socket.sendto.call_args[0], (b"hello", ("1.2.3.4", 1234)))
        self.assertEqual(callback.call_args[0][0], self.server)
        self.assertEqual(self.server.pending_s, 0)
        self.assertEqual(len(self.server.pending), 0)

    def test__send_partial(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        callback = mock.MagicMock()
        _socket = mock.MagicMock()
        _socket.sendto.side_effect = [2, 3]
        self.server.pending.appendleft(((b"hello", callback), ("1.2.3.4", 1234)))
        self.server.pending_s = 5

        with mock.patch.object(self.server, "remove_write"):
            self.server._send(_socket)

        # what was not taken is queued again, so that the rest of it goes out
        # under the next writing, and only then is the callback run
        self.assertEqual(_socket.sendto.call_args_list[1][0][0], b"llo")
        self.assertEqual(callback.call_count, 1)
        self.assertEqual(self.server.pending_s, 0)

    def test__send_blocked(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        _socket.sendto.side_effect = socket.error(errno.EWOULDBLOCK, "error")
        self.server.pending.appendleft((b"hello", ("1.2.3.4", 1234)))

        with mock.patch.object(self.server, "ensure_write") as ensure_write:
            self.assertRaises(socket.error, self.server._send, _socket)

        # a socket that could not take the datagram is no longer known to be
        # writable, the datagram being queued again for when it is
        self.assertEqual(self.server.wready, False)
        self.assertEqual(len(self.server.pending), 1)
        self.assertEqual(ensure_write.called, True)

    def test__send_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()

        with mock.patch.object(self.server, "remove_write") as remove_write:
            self.server._send(_socket)

        # with nothing queued the socket is no longer watched for the writing,
        # as it would otherwise wake the poll up for nothing
        self.assertEqual(_socket.sendto.called, False)
        self.assertEqual(remove_write.called, True)

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

    def test_on_read_s(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        first, second = mock.MagicMock(), mock.MagicMock()
        _socket.accept.side_effect = [
            (first, ("1.2.3.4", 1234)),
            (second, ("5.6.7.8", 5678)),
            socket.error(errno.EWOULDBLOCK, "error"),
        ]

        with mock.patch.object(self.server, "on_socket_c") as on_socket_c:
            self.server.on_read_s(_socket)

        # the accepting goes on until the queue of the kernel is empty, so
        # that a single wake up of the poll takes every connection
        self.assertEqual(on_socket_c.call_count, 2)
        self.assertEqual(on_socket_c.call_args_list[0][0][0], first)

    def test_on_read_s_refused(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        socket_c = mock.MagicMock()
        _socket.accept.side_effect = [(socket_c, ("1.2.3.4", 1234))]

        with mock.patch.object(
            self.server, "on_socket_c", side_effect=ValueError("broken")
        ):
            with mock.patch.object(self.server, "on_exception_s") as on_exception_s:
                self.server.on_read_s(_socket)

        # a socket that the service refused is closed rather than leaked, and
        # the failure is still reported as the exception that it is
        self.assertEqual(socket_c.close.called, True)
        self.assertEqual(on_exception_s.called, True)

    def test_on_read_s_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the accepting classifies the failures as the reading does, with no
        # connection to be dropped as none was established
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
            (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
            (socket.error(errno.ECONNABORTED, "error"), True, False),
            (socket.error(errno.EAGAIN, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            _socket = mock.MagicMock()
            _socket.accept.side_effect = error

            with mock.patch.object(self.server, "on_expected_s") as on_expected_s:
                with mock.patch.object(self.server, "on_exception_s") as on_exception_s:
                    self.server.on_read_s(_socket)

            self.assertEqual(on_expected_s.called, expected)
            self.assertEqual(on_exception_s.called, exception)

        _socket = mock.MagicMock()
        _socket.accept.side_effect = KeyboardInterrupt()

        self.assertRaises(KeyboardInterrupt, self.server.on_read_s, _socket)

    def test_on_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        received = []
        connection.bind("data", lambda _connection, data: received.append(data))

        with mock.patch.object(connection, "recv", side_effect=[b"hello", b""]):
            self.server.on_read(connection.socket)

        # every chunk that comes off the socket is handed over until the peer
        # closes it, which is what an empty read stands for
        self.assertEqual(received, [b"hello"])
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_CLIENT_EOF)

    def test_on_read_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a connection that is no longer open, or one whose reading was turned
        # off, is left alone instead of being read from
        for attribute, value in (("status", conn.CLOSED), ("renable", False)):
            connection = self._make_connection()
            setattr(connection, attribute, value)

            with mock.patch.object(connection, "recv") as recv:
                self.server.on_read(connection.socket)

            self.assertEqual(recv.called, False)

    def test_on_read_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the same ladder as everywhere else, the connection being the one
        # that the failure is reported against
        for error, expected, exception in (
            (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
            (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
            (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
            (socket.error(errno.ECONNRESET, "error"), True, False),
            (socket.error(errno.EAGAIN, "error"), False, False),
            (socket.error(errno.EBADF, "error"), False, True),
            (ValueError("broken"), False, True),
        ):
            connection = self._make_connection()

            with mock.patch.object(connection, "recv", side_effect=error):
                with mock.patch.object(self.server, "on_expected") as on_expected:
                    with mock.patch.object(self.server, "on_exception") as on_exception:
                        self.server.on_read(connection.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        connection = self._make_connection()

        with mock.patch.object(connection, "recv", side_effect=KeyboardInterrupt()):
            self.assertRaises(KeyboardInterrupt, self.server.on_read, connection.socket)

    def test_on_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()

        with mock.patch.object(connection, "_send") as _send:
            self.server.on_write(connection.socket)

        # a socket that became writable flushes whatever the connection still
        # holds in its buffer
        self.assertEqual(_send.called, True)

        connection = self._make_connection()
        connection.status = conn.CLOSED

        with mock.patch.object(connection, "_send") as _send:
            self.server.on_write(connection.socket)

        self.assertEqual(_send.called, False)

    def test_on_write_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

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
                with mock.patch.object(self.server, "on_expected") as on_expected:
                    with mock.patch.object(self.server, "on_exception") as on_exception:
                        self.server.on_write(connection.socket)

            self.assertEqual(on_expected.called, expected)
            self.assertEqual(on_exception.called, exception)

        connection = self._make_connection()

        with mock.patch.object(connection, "_send", side_effect=SystemExit()):
            self.assertRaises(SystemExit, self.server.on_write, connection.socket)

    def test_on_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _socket = mock.MagicMock()
        callback = mock.MagicMock()
        self.server.callbacks_m[_socket] = [callback]
        try:
            self.server.on_error(_socket)

            self.assertEqual(callback.call_args[0], ("error", _socket))
        finally:
            del self.server.callbacks_m[_socket]

        connection = self._make_connection()

        self.server.on_error(connection.socket)

        # a connection whose socket is in error is dropped, the reason naming
        # it so that the diagnostics may tell it apart
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)

        connection = self._make_connection()
        connection.status = conn.CLOSED

        self.server.on_error(connection.socket)

        self.assertEqual(connection.close_reason, None)

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

    def test_on_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        self._make_served()

        with mock.patch.object(connection, "ssl_verify_host") as verify_host:
            with mock.patch.object(
                connection, "ssl_verify_fingerprint"
            ) as verify_fingerprint:
                with mock.patch.object(
                    connection, "ssl_dump_certificate"
                ) as dump_certificate:
                    self.server.on_ssl(connection)

        # with nothing configured the verification runs with no value of its
        # own, the connection being the one that decides what to check
        self.assertEqual(verify_host.call_args[0], ())
        self.assertEqual(verify_fingerprint.call_args[0], ())
        self.assertEqual(dump_certificate.call_args[0], ())

    def test_on_ssl_configured(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        self._make_served(
            ssl_host="netius.hive",
            ssl_fingerprint="ab:cd",
            ssl_dump="/tmp/netius.cer",
        )

        with mock.patch.object(connection, "ssl_verify_host") as verify_host:
            with mock.patch.object(
                connection, "ssl_verify_fingerprint"
            ) as verify_fingerprint:
                with mock.patch.object(
                    connection, "ssl_dump_certificate"
                ) as dump_certificate:
                    self.server.on_ssl(connection)

        # the values of the service are the ones the peer is verified against,
        # which is what a configured one asks for
        self.assertEqual(verify_host.call_args[0][0], "netius.hive")
        self.assertEqual(verify_fingerprint.call_args[0][0], "ab:cd")
        self.assertEqual(dump_certificate.call_args[0][0], "/tmp/netius.cer")

    def test_on_ssl_upgrading(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.upgrading = True
        self._make_served()

        with mock.patch.object(connection, "ssl_verify_host"):
            with mock.patch.object(connection, "ssl_verify_fingerprint"):
                with mock.patch.object(connection, "ssl_dump_certificate"):
                    with mock.patch.object(self.server, "on_upgrade") as on_upgrade:
                        self.server.on_ssl(connection)

        # a connection that was already established and became secure is an
        # upgraded one, and the service is told about it
        self.assertEqual(on_upgrade.call_args[0][0], connection)

    def test_on_socket_c(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        socket_c = mock.MagicMock()
        socket_c.family = socket.AF_INET
        connection = mock.MagicMock()
        connection.is_pending_data.return_value = False

        with mock.patch.object(
            self.server, "build_connection", return_value=connection
        ):
            self.server.on_socket_c(socket_c, ("1.2.3.4", 1234))

        # the socket of a peer never blocks and is told to keep itself alive,
        # the connection being opened right after
        self.assertEqual(socket_c.setblocking.call_args[0][0], 0)
        self.assertEqual(connection.open.called, True)

    def test_on_socket_c_refused(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        socket_c = mock.MagicMock()
        socket_c.family = socket.AF_INET
        self.server.allowed = ["10.0.0.1"]

        # a peer whose address is not among the allowed ones is refused before
        # anything at all is built for it
        self.assertRaises(
            netius.NetiusError, self.server.on_socket_c, socket_c, ("1.2.3.4", 1234)
        )

    def test_on_socket_d(self):
        connection = self._make_connection()

        self.server.on_socket_d(connection.socket)

        # a socket that is no longer associated with a connection must be
        # gracefully ignored, as the connection may already be gone
        self.server.on_socket_d(socket.socket())

    def _make_served(self, ssl_host=None, ssl_fingerprint=None, ssl_dump=None):
        # settles the values of the verification of the peer, which a service
        # only gains once it is serving, so that the handling of the secure
        # layer may be run over it
        self.server.ssl_host = ssl_host
        self.server.ssl_fingerprint = ssl_fingerprint
        self.server.ssl_dump = ssl_dump

    def _make_connection(self):
        # builds an open connection registered in the server, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.server, socket=_socket)
        connection.status = conn.OPEN
        self.server.connections.append(connection)
        self.server.connections_m[_socket] = connection
        return connection
