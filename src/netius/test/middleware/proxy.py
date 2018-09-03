#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct
import unittest

import netius.common
import netius.middleware

class ProxyMiddlewareTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.Server(poll = netius.Poll)
        self.server.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_ipv4_v1(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware
        )

        connection = netius.Connection(owner = self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        instance._proxy_handshake_v1(connection)

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(len(connection.restored), 0)

    def test_ipv6_v1(self):
        instance = self.server.register_middleware(
            netius.middleware.ProxyMiddleware
        )

        connection = netius.Connection(owner = self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 fe80::787f:f63f:3176:d61b fe80::787f:f63f:3176:d61c 32598 8080\r\n")
        instance._proxy_handshake_v1(connection)

        self.assertEqual(connection.address, ("fe80::787f:f63f:3176:d61b", 32598))
        self.assertEqual(len(connection.restored), 0)

    def test_starter_v1(self):
        self.server.register_middleware(
            netius.middleware.ProxyMiddleware
        )

        connection = netius.Connection(owner = self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.1 192.168.1.2 32598 8080\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)

        connection = netius.Connection(owner = self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.3 ")
        connection.restore(b"192.168.1.4 32598 8080\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.3", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)

        connection = netius.Connection(owner = self.server)
        connection.open()

        connection.restore(b"PROXY TCP4 192.168.1.3 ")
        connection.restore(b"192.168.1.4 32598 8080\r\nGET")
        connection.restore(b" / HTTP/1.0\r\n\r\n")
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.3", 32598))
        self.assertEqual(connection.restored_s, 18)
        self.assertEqual(len(connection.restored), 2)

    def test_starter_v2(self):
        self.server.register_middleware(
            netius.middleware.ProxyMiddleware, version = 2
        )

        connection = netius.Connection(owner = self.server)
        connection.open()

        body = struct.pack(
            "!IIHH",
            netius.common.ip4_to_addr("192.168.1.1"),
            netius.common.ip4_to_addr("192.168.1.2"),
            32598,
            8080
        )

        header = struct.pack(
            "!12sBBH",
            netius.middleware.ProxyMiddleware.HEADER_MAGIC_V2,
            (2 << 4) + (netius.middleware.ProxyMiddleware.TYPE_PROXY_V2),
            (netius.middleware.ProxyMiddleware.AF_INET_v2 << 4) + (netius.middleware.ProxyMiddleware.PROTO_STREAM_v2),
            len(body)
        )

        connection.restore(header)
        connection.restore(body)
        connection.run_starter()

        self.assertEqual(connection.address, ("192.168.1.1", 32598))
        self.assertEqual(connection.restored_s, 0)
        self.assertEqual(len(connection.restored), 0)
