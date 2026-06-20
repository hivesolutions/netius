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

import unittest

import netius.extra

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ForwardProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.ForwardProxyServer()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_on_headers_connect_tunnels(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_request_parser(
            method="CONNECT", path="host.com:443"
        )
        backend = self._make_backend()

        with mock.patch.object(
            self.server.raw_client, "connect", return_value=backend
        ) as connect:
            with mock.patch.object(self.server.http_client, "method") as method:
                self.server.on_headers(frontend, request_parser)

        # the CONNECT request must establish a raw tunnel through the raw
        # client and never reach the (HTTP) client based forwarding path
        self.assertEqual(method.call_count, 0)
        self.assertEqual(connect.call_args[0], ("host.com", 443))

        # the back-end connection must be set as the tunnel connection and
        # the proper reverse mapping must exist in the connection map
        self.assertEqual(frontend.tunnel_c, backend)
        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.conn_map[backend], frontend)

        # the acknowledge response must be stored so that it may be sent to
        # the front-end once the tunnel connection is established
        self.assertEqual(backend.tunnel_r, (200, "Connection established"))
        self.assertIsNone(backend.tunnel_d)

    def test_on_headers_method_routes_to_backend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_request_parser(
            method="GET", path="http://host.com/"
        )
        backend = self._make_backend()

        with mock.patch.object(self.server.raw_client, "connect") as connect:
            with mock.patch.object(
                self.server.http_client, "method", return_value=backend
            ) as method:
                self.server.on_headers(frontend, request_parser)

        # a regular method must be forwarded through the (HTTP) client and
        # no raw tunnel must be established for the connection
        self.assertEqual(connect.call_count, 0)
        self.assertEqual(method.call_count, 1)
        self.assertEqual(frontend.proxy_c, backend)
        self.assertIn(backend, self.server.conn_map)

    def test_on_headers_rejected_sends_403(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ForwardProxyServer(rules=dict(deny=".*host.com.*"))

        frontend = self._make_frontend()
        request_parser = self._make_request_parser(
            method="CONNECT", path="host.com:443"
        )

        try:
            with mock.patch.object(server.raw_client, "connect") as connect:
                server.on_headers(frontend, request_parser)
        finally:
            server.cleanup()

        # a rejected connection must be answered with a forbidden response
        # and must never establish a raw tunnel towards the back-end
        self.assertEqual(connect.call_count, 0)
        self.assertEqual(frontend.send_response.call_count, 1)
        self.assertEqual(frontend.send_response.call_args[1]["code"], 403)

    def _make_frontend(self):
        frontend = mock.MagicMock()
        frontend.ssl = False
        frontend.address = ("127.0.0.1", 12345)
        # removes dynamic attributes that on_headers checks via hasattr
        del frontend.proxy_c
        del frontend.tunnel_c
        return frontend

    def _make_backend(self):
        backend = mock.MagicMock()
        backend.address = ("10.0.0.1", 8080)
        backend.waiting = False
        return backend

    def _make_request_parser(self, method="GET", path="/test"):
        parser = mock.MagicMock()
        parser.method = method
        parser.path_s = path
        parser.version_s = "HTTP/1.1"
        parser.headers = {}
        return parser
