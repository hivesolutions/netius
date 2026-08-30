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
import unittest

import netius.common
import netius.middleware

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ProxyMiddlewareTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.Server(poll=netius.Poll)
        self.server.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_stop(self):
        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        instance.stop()

        # the stopping releases the handler, so that a connection that is
        # created afterwards is no longer handed a starter
        self.assertEqual(
            instance.on_connection_c in self.server.events["connection_c"], False
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        self.assertEqual(hasattr(connection, "_proxy_pending"), False)

    def test_on_connection_c_base(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection._base = True
        connection.open()

        # a connection that stands for the base of another one carries no
        # header of its own, so no starter is added to it
        self.assertEqual(hasattr(connection, "_proxy_pending"), False)

    def test_on_connection_c_skip(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection._skip_proxy = True
        connection.open()

        # the skipping is asked for by the connection itself, which is
        # enough for the handshake never to be scheduled
        self.assertEqual(hasattr(connection, "_proxy_pending"), False)

    def test_on_connection_c_version(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware, version=3)

        connection = netius.Connection(owner=self.server)

        # only the two versions of the protocol are known, so a value
        # that names neither of them is refused
        self.assertRaises(netius.RuntimeError, connection.open)

    def test_ipv4_v1(self):
        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        instance._proxy_handshake_v1(connection)

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(len(connection.restored), 0)

    def test_ipv6_v1(self):
        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(
            b"PROXY TCP4 fe80::787f:f63f:3176:d61b fe80::787f:f63f:3176:d61c 32598 8080\r\n"
        )
        instance._proxy_handshake_v1(connection)

        self.assertEqual(connection.address, ("fe80::787f:f63f:3176:d61b", 32598))
        self.assertEqual(len(connection.restored), 0)

    def test_starter_v1(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.3 ")
        connection.restore(b"192.168.1.4 32598 8080\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.3", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.3 ")
        connection.restore(b"192.168.1.4 32598 8080\r\nGET")
        connection.restore(b" / HTTP/1.0\r\n\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.3", 32598))
        self.assertEqual(connection.restored_s, 18)
        self.assertEqual(len(connection.restored), 2)

    def test_starter_v1_eof(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        with mock.patch.object(self.server, "exec_safe", return_value=b""):
            instance._proxy_handshake_v1(connection)

        # an empty read is the peer that is gone, so the connection is
        # closed instead of being waited for any longer
        self.assertEqual(connection.is_closed(), True)

    def test_starter_v1_buffer(self):
        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        # the part of the header that was already read is kept in the
        # buffer of the connection, which the next run takes up again
        connection._proxy_buffer = bytearray(b"PROXY TCP4 192.168.1.1 ")
        connection.restore(b"192.168.1.2 32598 8080\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.1", 32598))

    def test_starter_v1_blocked(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        instance = self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        with mock.patch.object(self.server, "exec_safe", return_value=False):
            instance._proxy_handshake_v1(connection)

        # a read that was blocked gives neither data nor failure, so the
        # handshake steps back and waits to be run again
        self.assertEqual(connection.is_closed(), False)
        self.assertEqual(connection._proxy_pending, True)

    def test_starter_v2(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware, version=2)

        connection = netius.Connection(owner=self.server)
        connection.open()

        body = struct.pack(
            "!IIHH",
            netius.common.ip4_to_addr("192.168.1.1"),
            netius.common.ip4_to_addr("192.168.1.2"),
            32598,
            8080,
        )

        header = struct.pack(
            "!12sBBH",
            netius.middleware.ProxyMiddleware.HEADER_MAGIC_V2,
            (2 << 4) + (netius.middleware.ProxyMiddleware.TYPE_PROXY_V2),
            (netius.middleware.ProxyMiddleware.AF_INET_v2 << 4)
            + (netius.middleware.ProxyMiddleware.PROTO_STREAM_v2),
            len(body),
        )

        connection.restore(header)
        connection.restore(body)
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)

    def test_starter_v2_eof(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, version=2
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        with mock.patch.object(self.server, "exec_safe", return_value=b""):
            instance._proxy_handshake_v2(connection)

        # the reading of the header ends the very same way, the peer
        # being gone before it was ever complete
        self.assertEqual(connection.is_closed(), True)

    def test_starter_v2_ipv6(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware, version=2)

        connection = netius.Connection(owner=self.server)
        connection.open()

        body = struct.pack(
            "!QQQQHH",
            0xFE80000000000000,
            0x787FF63F3176D61B,
            0xFE80000000000000,
            0x787FF63F3176D61C,
            32598,
            8080,
        )

        connection.restore(self._header_v2(len(body), address=self._AF_INET6))
        connection.restore(body)
        connection.run_starter()

        # the address of the six family travels as four words, which are
        # joined back into the two addresses that the message carries
        self.assertEqual(
            connection.address, ("fe80:0000:0000:0000:787f:f63f:3176:d61b", 32598)
        )
        self.assertEqual(len(connection.restored), 0)

    def test_starter_v2_family(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, version=2
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(self._header_v2(12, address=0x0F))
        connection.restore(b"x" * 12)

        # a family that is neither of the two known ones names an address
        # that cannot be read, so the message is refused
        self.assertRaises(
            netius.RuntimeError, lambda: instance._proxy_handshake_v2(connection)
        )

    def test_starter_v2_blocked(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, version=2
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        with mock.patch.object(self.server, "exec_safe", return_value=False):
            instance._proxy_handshake_v2(connection)

        # the header is never read in full, so neither the buffer nor the
        # header of the connection carry anything yet
        self.assertEqual(connection.is_closed(), False)
        self.assertEqual(hasattr(connection, "_proxy_header"), False)

    def test_pending_flag_v1(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware)

        connection = netius.Connection(owner=self.server)
        connection.open()

        self.assertTrue(hasattr(connection, "_proxy_pending"))
        self.assertTrue(connection._proxy_pending)

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        connection.run_starter()

        self.assertFalse(connection._proxy_pending)

    def test_pending_flag_v2(self):
        self.server.register_middleware(netius.middleware.ProxyMiddleware, version=2)

        connection = netius.Connection(owner=self.server)
        connection.open()

        self.assertTrue(hasattr(connection, "_proxy_pending"))
        self.assertTrue(connection._proxy_pending)

        body = struct.pack(
            "!IIHH",
            netius.common.ip4_to_addr("192.168.1.1"),
            netius.common.ip4_to_addr("192.168.1.2"),
            32598,
            8080,
        )

        header = struct.pack(
            "!12sBBH",
            netius.middleware.ProxyMiddleware.HEADER_MAGIC_V2,
            (2 << 4) + (netius.middleware.ProxyMiddleware.TYPE_PROXY_V2),
            (netius.middleware.ProxyMiddleware.AF_INET_v2 << 4)
            + (netius.middleware.ProxyMiddleware.PROTO_STREAM_v2),
            len(body),
        )

        connection.restore(header)
        connection.restore(body)
        connection.run_starter()

        self.assertFalse(connection._proxy_pending)

    def test_timeout_stale(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, handshake_timeout=1
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        self.assertTrue(connection._proxy_pending)
        self.assertEqual(connection.status, netius.OPEN)
        self.assertIn(connection, self.server.connections)

        instance._proxy_timeout(connection)

        self.assertEqual(connection.status, netius.CLOSED)
        self.assertNotIn(connection, self.server.connections)

        # the closing must be identified as a timeout driven one, so that
        # the diagnostics are able to report the cause for it
        self.assertEqual(connection.close_reason, netius.REASON_TIMEOUT)

    def test_timeout_completed(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, handshake_timeout=1
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        connection.run_starter()

        self.assertFalse(connection._proxy_pending)
        self.assertEqual(connection.status, netius.OPEN)

        instance._proxy_timeout(connection)

        self.assertEqual(connection.status, netius.OPEN)
        self.assertIn(connection, self.server.connections)

    def test_timeout_already_closed(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware, handshake_timeout=1
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        connection.close()

        self.assertEqual(connection.status, netius.CLOSED)

        instance._proxy_timeout(connection)

        self.assertEqual(connection.status, netius.CLOSED)

    def test_timeout_disabled(self):
        self.server.register_middleware(
            netius.middleware.ProxyMiddleware, handshake_timeout=0
        )

        connection = netius.Connection(owner=self.server)
        connection.open()

        self.assertFalse(hasattr(connection, "_proxy_pending"))

    _AF_INET6 = netius.middleware.ProxyMiddleware.AF_INET6_v2

    def _header_v2(self, body_size, address=None):
        # builds the header of a version two message for the provided body
        # size, defaulting the family to the four based one
        cls = netius.middleware.ProxyMiddleware
        address = cls.AF_INET_v2 if address == None else address
        return struct.pack(
            "!12sBBH",
            cls.HEADER_MAGIC_V2,
            (2 << 4) + cls.TYPE_PROXY_V2,
            (address << 4) + cls.PROTO_STREAM_v2,
            body_size,
        )
