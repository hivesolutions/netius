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

import collections
import unittest

import netius.servers

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.ProxyServer()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_is_upgrade(self):
        Parser = collections.namedtuple("Parser", "headers")

        parser = Parser(headers={"connection": "Upgrade", "upgrade": "websocket"})
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(
            headers={"connection": "keep-alive, Upgrade", "upgrade": "WebSocket"}
        )
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(headers={"connection": "keep-alive"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(headers={"connection": "Upgrade", "upgrade": "h2c"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(headers={"connection": "notupgrade", "upgrade": "websocket"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(
            headers={
                "connection": ["keep-alive", "Upgrade"],
                "upgrade": ["websocket"],
            }
        )
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(headers={})
        self.assertEqual(self.server.is_upgrade(parser), False)

    def test_tunnel(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()

        with mock.patch.object(
            self.server.raw_client, "connect", return_value=backend
        ) as connect:
            result = self.server.tunnel(
                connection, "host.com", 9090, ssl=True, data=b"data"
            )

        # the back-end connection must be created through the raw client
        # using the requested host, port and secure transport flag
        self.assertEqual(result, backend)
        self.assertEqual(connect.call_args[0], ("host.com", 9090))
        self.assertEqual(connect.call_args[1], dict(ssl=True))

        # the back-end connection must be set as the tunnel connection of
        # the front-end and the reverse mapping must exist in the conn map
        self.assertEqual(connection.tunnel_c, backend)
        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.conn_map[backend], connection)

        # the data and response values must be stored in the back-end so
        # that they may be used once the connection is established
        self.assertEqual(backend.tunnel_d, b"data")
        self.assertEqual(backend.tunnel_r, None)

    def test_on_raw_connect_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()
        backend.tunnel_d = b"data"
        backend.tunnel_r = None
        self.server.conn_map[backend] = connection

        self.server._on_raw_connect(self.server.raw_client, backend)

        # the buffered data must be forwarded to the back-end and no
        # acknowledge response must be sent to the front-end connection
        self.assertEqual(backend.send.call_args[0], (b"data",))
        self.assertEqual(connection.send_response.call_count, 0)

        # the data reference must be unset after being sent so that the
        # request buffer is not retained for the lifetime of the tunnel
        self.assertEqual(backend.tunnel_d, None)

    def test_on_raw_connect_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()
        backend.tunnel_d = None
        backend.tunnel_r = (200, "Connection established")
        self.server.conn_map[backend] = connection

        self.server._on_raw_connect(self.server.raw_client, backend)

        # the acknowledge response must be sent to the front-end connection
        # and no data must be forwarded to the back-end connection
        self.assertEqual(connection.send_response.call_count, 1)
        self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        self.assertEqual(backend.send.call_count, 0)
