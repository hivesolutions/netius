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

import re
import zlib
import json
import time
import socket
import unittest
import threading
import collections

import netius
import netius.extra
import netius.clients
import netius.servers

try:
    import http.client as http_client
except ImportError:
    http_client = None

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ReverseProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"}, alias={"alias.host.com": "host.com"}
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_alias(self):
        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="alias.host.com"))
        result = self.server.rules_host(None, parser)
        self.assertEqual(result, ("http://localhost", None))

    def test_container_setup(self):
        self.assertIsNotNone(self.server.container)
        self.assertEqual(len(self.server.container.bases), 3)
        self.assertIn(self.server, self.server.container.bases)
        self.assertIn(self.server.http_client, self.server.container.bases)
        self.assertIn(self.server.raw_client, self.server.container.bases)

    def test_container_agent_types(self):
        self.assertIsInstance(self.server.http_client, netius.clients.HTTPClient)
        self.assertIsInstance(self.server.raw_client, netius.clients.RawClient)
        self.assertIsInstance(self.server.http_client, netius.Agent)
        self.assertIsInstance(self.server.raw_client, netius.Agent)
        self.assertNotIsInstance(self.server.http_client, netius.Base)
        self.assertNotIsInstance(self.server.raw_client, netius.Base)

    def test_container_loop_agents(self):
        self.assertTrue(hasattr(self.server.http_client, "_container_loop"))
        self.assertTrue(hasattr(self.server.raw_client, "_container_loop"))

    def test_container_loop_not_on_server(self):
        self.assertFalse(hasattr(self.server, "_container_loop"))

    def test_container_lifecycle(self):
        self.server.container.start_all()
        self.server.container.ticks()
        self.server.container.call_all("on_start")
        self.server.container.call_all("on_stop")

    def test_agent_connections_dict(self):
        self.assertEqual(self.server.http_client.connections_dict(), {})
        self.assertEqual(self.server.raw_client.connections_dict(), {})

    def test_container_connection_dict(self):
        result = self.server.container.connection_dict(999)
        self.assertIsNone(result)

    def test_http_client_bindings(self):
        events = self.server.http_client.events
        self.assertIn("headers", events)
        self.assertIn("message", events)
        self.assertIn("partial", events)
        self.assertIn("connect", events)
        self.assertIn("acquire", events)
        self.assertIn("close", events)
        self.assertIn("error", events)

    def test_raw_client_bindings(self):
        events = self.server.raw_client.events
        self.assertIn("connect", events)
        self.assertIn("data", events)
        self.assertIn("close", events)

    def test_agent_base_interface(self):
        for client in (self.server.http_client, self.server.raw_client):
            self.assertTrue(hasattr(client, "name"))
            self.assertTrue(hasattr(client, "connections"))
            self.assertTrue(hasattr(client, "load"))
            self.assertTrue(hasattr(client, "unload"))
            self.assertTrue(hasattr(client, "ticks"))
            self.assertTrue(hasattr(client, "on_start"))
            self.assertTrue(hasattr(client, "on_stop"))
            self.assertTrue(hasattr(client, "connections_dict"))

    def test_config(self):
        self.assertEqual(self.server.hosts, {"host.com": "http://localhost"})
        self.assertEqual(self.server.alias, {"alias.host.com": "host.com"})
        self.assertEqual(self.server.strategy, "robin")
        self.assertTrue(self.server.reuse)

    def test_config_custom(self):
        server = netius.extra.ReverseProxyServer(
            hosts={"app.com": "http://backend"},
            strategy="smart",
            reuse=False,
            sts=86400,
        )

        self.assertEqual(server.hosts, {"app.com": "http://backend"})
        self.assertEqual(server.strategy, "smart")
        self.assertFalse(server.reuse)
        self.assertEqual(server.sts, 86400)

        server.cleanup()

    def test_conn_map_empty(self):
        self.assertIsInstance(self.server.conn_map, dict)
        self.assertEqual(len(self.server.conn_map), 0)

    def test_rules_host(self):
        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="host.com"))
        result = self.server.rules_host(None, parser)
        self.assertEqual(result, ("http://localhost", None))

    def test_rules_host_unknown(self):
        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="unknown.com"))
        prefix, state = self.server.rules_host(None, parser)
        self.assertIsNone(prefix)

    def test_rules_host_default(self):
        server = netius.extra.ReverseProxyServer(hosts={"default": "http://fallback"})

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="any.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://fallback", None))

        server.cleanup()

    def test_rules_host_strip_port(self):
        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="host.com:8080"))
        result = self.server.rules_host(None, parser)
        self.assertEqual(result, ("http://localhost", None))

    def test_rules_regex(self):
        server = netius.extra.ReverseProxyServer(
            regex=[(re.compile(r"https://api\.host\.com"), "http://api-backend")]
        )

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="api.host.com"))
        prefix, state = server.rules_regex("https://api.host.com/v1", parser)
        self.assertEqual(prefix, "http://api-backend")

        server.cleanup()

    def test_rules_regex_groups(self):
        server = netius.extra.ReverseProxyServer(
            regex=[
                (re.compile(r"https://([a-zA-Z]+)\.host\.com"), "http://localhost/{0}")
            ]
        )

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="app.host.com"))
        prefix, state = server.rules_regex("https://app.host.com/path", parser)
        self.assertEqual(prefix, "http://localhost/app")

        server.cleanup()

    def test_rules_regex_no_match(self):
        server = netius.extra.ReverseProxyServer(
            regex=[(re.compile(r"https://api\.host\.com"), "http://api-backend")]
        )

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="other.com"))
        prefix, state = server.rules_regex("https://other.com/v1", parser)
        self.assertIsNone(prefix)

        server.cleanup()

    def test_rules_forward(self):
        server = netius.extra.ReverseProxyServer(forward="http://catch-all")

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="any.com"))
        result = server.rules_forward(None, parser)
        self.assertEqual(result, ("http://catch-all", None))

        server.cleanup()

    def test_rules_priority(self):
        server = netius.extra.ReverseProxyServer(
            regex=[(re.compile(r"https://api\.host\.com"), "http://regex-backend")],
            hosts={"host.com": "http://host-backend"},
            forward="http://forward-backend",
        )

        Parser = collections.namedtuple("Parser", "headers")

        # regex matches first in the resolution chain
        parser = Parser(headers=dict(host="api.host.com"))
        prefix, state = server.rules("https://api.host.com/path", parser)
        self.assertEqual(prefix, "http://regex-backend")

        # host matches when regex does not
        parser = Parser(headers=dict(host="host.com"))
        prefix, state = server.rules("http://host.com/path", parser)
        self.assertEqual(prefix, "http://host-backend")

        # forward acts as the final fallback
        parser = Parser(headers=dict(host="unknown.com"))
        prefix, state = server.rules("http://unknown.com/path", parser)
        self.assertEqual(prefix, "http://forward-backend")

        server.cleanup()

    def test_rules_no_match(self):
        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="unknown.com"))
        prefix, state = self.server.rules("http://unknown.com/path", parser)
        self.assertIsNone(prefix)
        self.assertIsNone(state)

    def test_balancer_single(self):
        prefix, state = self.server.balancer("http://localhost")
        self.assertEqual(prefix, "http://localhost")
        self.assertIsNone(state)

    def test_balancer_robin(self):
        values = ("http://a", "http://b", "http://c")

        prefix, state = self.server.balancer(values)
        self.assertEqual(prefix, "http://a")

        prefix, state = self.server.balancer(values)
        self.assertEqual(prefix, "http://b")

        prefix, state = self.server.balancer(values)
        self.assertEqual(prefix, "http://c")

        # wraps around to the first value
        prefix, state = self.server.balancer(values)
        self.assertEqual(prefix, "http://a")

    def test_balancer_smart(self):
        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": ("http://a", "http://b")},
            strategy="smart",
        )

        values = ("http://a", "http://b")

        prefix, state = server.balancer(values)
        self.assertIn(prefix, values)
        self.assertIsNotNone(state)

        # acquirer and releaser operate without errors
        server.acquirer(state)
        server.releaser(state)

        server.cleanup()

    def test_strategy_robin(self):
        self.assertEqual(self.server.strategy, "robin")
        self.assertEqual(self.server.balancer_m, self.server.balancer_robin)
        self.assertEqual(self.server.acquirer_m, self.server.acquirer_robin)
        self.assertEqual(self.server.releaser_m, self.server.releaser_robin)

    def test_strategy_smart(self):
        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"},
            strategy="smart",
        )

        self.assertEqual(server.strategy, "smart")
        self.assertEqual(server.balancer_m, server.balancer_smart)
        self.assertEqual(server.acquirer_m, server.acquirer_smart)
        self.assertEqual(server.releaser_m, server.releaser_smart)

        server.cleanup()

    def test_alias_chain(self):
        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"},
            alias={"www.host.com": "host.com", "alias.host.com": "host.com"},
        )

        Parser = collections.namedtuple("Parser", "headers")

        parser = Parser(headers=dict(host="www.host.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://localhost", None))

        parser = Parser(headers=dict(host="alias.host.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://localhost", None))

        server.cleanup()

    def test_info_dict(self):
        info = self.server.info_dict()
        self.assertIn("reuse", info)
        self.assertIn("strategy", info)
        self.assertIn("busy_conn", info)
        self.assertTrue(info["reuse"])
        self.assertEqual(info["strategy"], "robin")
        self.assertEqual(info["busy_conn"], 0)

    def test_busy_conn_initial(self):
        self.assertEqual(self.server.busy_conn, 0)

    def test_x_forwarded_initial(self):
        self.assertEqual(self.server.x_forwarded_port, None)
        self.assertEqual(self.server.x_forwarded_proto, None)

    def test_cleanup(self):
        server = netius.extra.ReverseProxyServer(hosts={"host.com": "http://localhost"})
        server.cleanup()

        self.assertIsNone(server.container)
        self.assertIsNone(server.http_client)
        self.assertIsNone(server.raw_client)

    def test_apply_headers_http_10_no_connection(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.0 client without a `Connection` header parses as
        # `keep_alive = False` while the HTTP/1.1 backend defaults to
        # `keep_alive = True`. Without the override the response would
        # advertise `keep-alive` to the client and then close the socket,
        # which is the row-1 contradiction in the keep-alive matrix
        parser = self._make_apply_headers_parser(version=netius.common.HTTP_10)
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "close")

    def test_apply_headers_http_10_keep_alive(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.0 client that explicitly opts into keep-alive matches
        # the backend's keep-alive flag, so the connection should be kept
        parser = self._make_apply_headers_parser(
            version=netius.common.HTTP_10, keep_alive=True
        )
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "keep-alive")

    def test_apply_headers_http_10_connection_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.0 client requesting `Connection: close` must result in
        # both the advertised header and the upstream parser agreeing on
        # close, regardless of the backend's keep-alive flag
        parser = self._make_apply_headers_parser(
            version=netius.common.HTTP_10, keep_alive=False
        )
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "close")

    def test_apply_headers_http_11_no_connection(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.1 client without a `Connection` header defaults to
        # keep-alive, matching the backend, so the socket should stay open
        parser = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "keep-alive")

    def test_apply_headers_http_11_keep_alive(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.1 client explicitly requesting keep-alive should be
        # honored when the backend agrees
        parser = self._make_apply_headers_parser(
            version=netius.common.HTTP_11, keep_alive=True
        )
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "keep-alive")

    def test_apply_headers_http_11_connection_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # HTTP/1.1 client requesting `Connection: close` must force the
        # advertised header to close even though the backend would keep
        parser = self._make_apply_headers_parser(
            version=netius.common.HTTP_11, keep_alive=False
        )
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "close")

    def test_apply_headers_backend_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # backend signals close, so the front-end response must advertise
        # close regardless of what the client requested, otherwise the
        # client would retain a socket the proxy is about to tear down
        parser = self._make_apply_headers_parser(
            version=netius.common.HTTP_11, keep_alive=True
        )
        parser_prx = self._make_apply_headers_parser(
            version=netius.common.HTTP_11, keep_alive=False
        )
        connection = self._make_apply_headers_connection()
        headers = dict()

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual(headers["Connection"], "close")

    def test_apply_headers_hop(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the headers that describe a single transport level connection must
        # never reach the client, as they refer to the connection kept with
        # the back-end and not to the one kept with the client
        parser = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = {
            "keep-alive": "timeout=5",
            "proxy-connection": "keep-alive",
            "te": "trailers",
            "trailer": "Expires",
            "upgrade": "h2c",
            "x-kept": "value",
        }

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual("Keep-Alive" in headers, False)
        self.assertEqual("Proxy-Connection" in headers, False)
        self.assertEqual("Te" in headers, False)
        self.assertEqual("Trailer" in headers, False)
        self.assertEqual("Upgrade" in headers, False)
        self.assertEqual(headers["X-Kept"], "value")

    def test_apply_headers_hop_connection(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # every token named by the connection header is also a hop-by-hop one
        # and so it must be removed before the response is forwarded, the
        # connection header itself is then rebuilt for the client
        parser = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = {
            "connection": "keep-alive, X-Custom",
            "x-custom": "value",
            "x-kept": "value",
        }

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual("X-Custom" in headers, False)
        self.assertEqual(headers["X-Kept"], "value")
        self.assertEqual(headers["Connection"], "keep-alive")

    def test_apply_headers_hop_connection_repeated(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a repeated connection header names hop-by-hop tokens on each one of
        # its definitions, so all of them must be taken into account and not
        # only the ones named by the last definition
        parser = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        parser_prx = self._make_apply_headers_parser(version=netius.common.HTTP_11)
        connection = self._make_apply_headers_connection()
        headers = {
            "connection": ["keep-alive, X-First", "X-Second"],
            "keep-alive": "timeout=5",
            "x-first": "a",
            "x-second": "b",
            "x-kept": "c",
        }

        self.server._apply_headers(parser, connection, parser_prx, headers)

        self.assertEqual("X-First" in headers, False)
        self.assertEqual("X-Second" in headers, False)
        self.assertEqual("Keep-Alive" in headers, False)
        self.assertEqual(headers["X-Kept"], "c")

    def test_resolve_regex(self):
        regexes = [
            (re.compile(r"https://host\.com/api"), "http://api-backend"),
            (re.compile(r"https://host\.com"), "http://backend"),
        ]

        result, match = self.server._resolve_regex("https://host.com/api/v1", regexes)
        self.assertEqual(result, "http://api-backend")
        self.assertIsNotNone(match)

    def test_resolve_regex_no_match(self):
        regexes = [
            (re.compile(r"https://host\.com"), "http://backend"),
        ]

        result, match = self.server._resolve_regex(
            "https://other.com/path", regexes, default="fallback"
        )
        self.assertEqual(result, "fallback")
        self.assertIsNone(match)

    def test_throttle_config(self):
        self.assertTrue(self.server.throttle)
        self.assertGreater(self.server.max_pending, 0)
        self.assertGreater(self.server.min_pending, 0)
        self.assertLess(self.server.min_pending, self.server.max_pending)

    def test_dynamic_config(self):
        self.assertTrue(self.server.dynamic)

    def test_trust_origin_config(self):
        self.assertFalse(self.server.trust_origin)

    def test_http_client_event_relay(self):
        events_received = []
        client = self.server.http_client

        client.bind("connect", lambda *args: events_received.append("connect"))
        client.bind("close", lambda *args: events_received.append("close"))

        # creates a protocol and relays its events through the client
        protocol = netius.clients.http.HTTPProtocol(
            "GET",
            "http://localhost/",
            safe=True,
        )
        client._relay_protocol_events(protocol)

        # simulates protocol lifecycle events
        protocol.trigger("open", protocol)
        protocol.trigger("close", protocol)

        self.assertIn("connect", events_received)
        self.assertIn("close", events_received)

    def test_raw_client_event_relay(self):
        # uses a fresh client to avoid the proxy server's own bindings
        events_received = []
        client = netius.clients.RawClient()

        client.bind("connect", lambda *args: events_received.append("connect"))
        client.bind("data", lambda *args: events_received.append("data"))
        client.bind("close", lambda *args: events_received.append("close"))

        # creates a protocol and relays its events through the client
        protocol = netius.clients.raw.RawProtocol()
        client._relay_protocol_events(protocol)

        # simulates protocol lifecycle events
        protocol.trigger("open", protocol)
        protocol.trigger("data", protocol, b"hello")
        protocol.trigger("close", protocol)

        self.assertIn("connect", events_received)
        self.assertIn("data", events_received)
        self.assertIn("close", events_received)

        client.cleanup()

    def test_multiple_hosts(self):
        server = netius.extra.ReverseProxyServer(
            hosts={
                "app.com": "http://app-backend",
                "api.com": "http://api-backend",
                "admin.com": "http://admin-backend",
            }
        )

        Parser = collections.namedtuple("Parser", "headers")

        parser = Parser(headers=dict(host="app.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://app-backend", None))

        parser = Parser(headers=dict(host="api.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://api-backend", None))

        parser = Parser(headers=dict(host="admin.com"))
        result = server.rules_host(None, parser)
        self.assertEqual(result, ("http://admin-backend", None))

        server.cleanup()

    def test_load_balancing_hosts(self):
        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": ("http://backend-1", "http://backend-2")}
        )

        Parser = collections.namedtuple("Parser", "headers")
        parser = Parser(headers=dict(host="host.com"))

        # round-robin cycles through the backends
        prefix1, _ = server.rules_host(None, parser)
        prefix2, _ = server.rules_host(None, parser)
        prefix3, _ = server.rules_host(None, parser)

        self.assertEqual(prefix1, "http://backend-1")
        self.assertEqual(prefix2, "http://backend-2")
        self.assertEqual(prefix3, "http://backend-1")

        server.cleanup()

    def test_balancer_none(self):
        prefix, state = self.server.balancer(None)
        self.assertIsNone(prefix)
        self.assertIsNone(state)

    def test_on_headers_routes_to_backend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_request_parser()
        backend = self._make_backend()

        with mock.patch.object(
            self.server.http_client, "method", return_value=(None, backend)
        ):
            self.server.on_headers(frontend, request_parser)

        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.conn_map[backend], frontend)
        self.assertTrue(backend.waiting)
        self.assertEqual(backend.busy, 1)
        self.assertEqual(self.server.busy_conn, 1)
        self.assertEqual(frontend.proxy_c, backend)
        self.assertEqual(frontend.prefix, "http://localhost")

    def test_on_headers_upgrade_tunnels_to_backend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_upgrade_parser()
        backend = self._make_backend()

        with mock.patch.object(
            self.server.raw_client, "connect", return_value=backend
        ) as connect:
            with mock.patch.object(self.server.http_client, "method") as method:
                self.server.on_headers(frontend, request_parser)

        # the upgrade request must be tunneled through the raw client and
        # never reach the (HTTP) client based forwarding code path
        self.assertEqual(method.call_count, 0)
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(connect.call_args[0], ("localhost", 80))
        self.assertEqual(connect.call_args[1], dict(ssl=False))

        # the back-end connection must be set as the tunnel connection and
        # the proper reverse mapping must exist in the connection map
        self.assertEqual(frontend.tunnel_c, backend)
        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.conn_map[backend], frontend)

        # the original upgrade request must have been stored for forwarding
        # to the back-end once the tunnel connection is established
        self.assertTrue(backend.tunnel_d.startswith(b"GET /socket HTTP/1.1\r\n"))
        self.assertIn(b"Upgrade: websocket\r\n", backend.tunnel_d)
        self.assertIsNone(backend.tunnel_r)

        # the (case sensitive) WebSocket handshake headers must be forwarded
        # with their original casing preserved, the proxy must not normalize
        # them (some back-ends match these headers in a case sensitive way)
        self.assertIn(
            b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n", backend.tunnel_d
        )
        self.assertIn(b"Sec-WebSocket-Version: 13\r\n", backend.tunnel_d)

        # the reverse proxy forwarding headers must be appended to the request
        # so that the back-end is aware of the original client and protocol
        self.assertIn(b"x-forwarded-for: ", backend.tunnel_d)
        self.assertIn(b"x-forwarded-host: ", backend.tunnel_d)

    def test_on_headers_upgrade_secure_backend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "https://localhost"}
        )

        frontend = self._make_frontend()
        request_parser = self._make_upgrade_parser()
        backend = self._make_backend()

        try:
            with mock.patch.object(
                server.raw_client, "connect", return_value=backend
            ) as connect:
                server.on_headers(frontend, request_parser)
        finally:
            server.cleanup()

        # the secure scheme of the back-end must be reflected both in the
        # default port resolution and in the secure transport flag
        self.assertEqual(connect.call_args[0], ("localhost", 443))
        self.assertEqual(connect.call_args[1], dict(ssl=True))

    def test_on_headers_upgrade_prefix_path(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost/base"}
        )

        frontend = self._make_frontend()
        request_parser = self._make_upgrade_parser()
        backend = self._make_backend()

        try:
            with mock.patch.object(
                server.raw_client, "connect", return_value=backend
            ) as connect:
                server.on_headers(frontend, request_parser)
        finally:
            server.cleanup()

        # the back-end prefix path must be prepended to the original path in
        # the forwarded request line (prefix + path), matching the routing of
        # a regular (non upgrade) request to the same prefixed back-end
        self.assertEqual(connect.call_args[0], ("localhost", 80))
        self.assertTrue(backend.tunnel_d.startswith(b"GET /base/socket HTTP/1.1\r\n"))

    def test_on_headers_no_match_sends_404(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_request_parser(host="unknown.com")

        self.server.on_headers(frontend, request_parser)

        self.assertEqual(frontend.send_response.call_count, 1)
        call_kwargs = frontend.send_response.call_args
        self.assertEqual(call_kwargs[1]["code"], 404)

    def test_on_headers_redirect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"},
            redirect={"host.com": "other.com"},
        )

        frontend = self._make_frontend()
        request_parser = self._make_request_parser(host="host.com")

        server.on_headers(frontend, request_parser)

        self.assertEqual(frontend.send_response.call_count, 1)
        call_kwargs = frontend.send_response.call_args[1]
        self.assertEqual(call_kwargs["code"], 303)
        self.assertIn("location", call_kwargs["headers"])
        self.assertIn("other.com", call_kwargs["headers"]["location"])

        server.cleanup()

    def test_prx_headers_relays_to_frontend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(backend)
        response_parser.headers = {"content-type": "text/html"}

        self.server._on_prx_headers(
            self.server.http_client, response_parser, response_parser.headers
        )

        self.assertEqual(frontend.send_header.call_count, 1)
        call_kwargs = frontend.send_header.call_args[1]
        self.assertEqual(call_kwargs["code"], 200)
        self.assertEqual(call_kwargs["code_s"], "OK")

        # _apply_via adds a Via header to the response
        headers = call_kwargs["headers"]
        self.assertIn("Via", headers)

    def test_prx_headers_interim(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(
            backend, code="100", status="Continue"
        )
        response_parser.headers = {"connection": "keep-alive"}

        self.server._on_prx_headers(
            self.server.http_client, response_parser, response_parser.headers
        )

        # an informational response is relayed as is, carrying neither the
        # hop-by-hop headers of the back-end nor any framing decision
        self.assertEqual(frontend.send_header.call_count, 1)
        call_kwargs = frontend.send_header.call_args[1]
        self.assertEqual(call_kwargs["code"], 100)
        self.assertEqual(call_kwargs["code_s"], "Continue")
        self.assertEqual("connection" in call_kwargs["headers"], False)
        self.assertEqual("Transfer-Encoding" in call_kwargs["headers"], False)

    def test_prx_headers_interim_http_10(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend
        frontend.parser.version = netius.common.HTTP_10

        response_parser = self._make_response_parser(
            backend, code="100", status="Continue"
        )
        response_parser.headers = {}

        self.server._on_prx_headers(
            self.server.http_client, response_parser, response_parser.headers
        )

        # a client with no support for an interim response must never be
        # presented with one, as it would take it as the final response
        self.assertEqual(frontend.send_header.call_count, 0)

    def test_prx_partial_relays_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(backend)

        self.server._on_prx_partial(
            self.server.http_client, response_parser, b"<html>hello</html>"
        )

        self.assertEqual(frontend.send_part.call_count, 1)
        args = frontend.send_part.call_args
        self.assertEqual(args[0][0], b"<html>hello</html>")

    def test_prx_message_completes_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        backend.waiting = True
        backend.busy = 1
        self.server.busy_conn = 1
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(backend)

        self.server._on_prx_message(self.server.http_client, response_parser, b"")

        self.assertEqual(frontend.flush_s.call_count, 1)
        self.assertFalse(backend.waiting)
        self.assertEqual(backend.busy, 0)
        self.assertEqual(self.server.busy_conn, 0)

    def test_prx_message_keep_alive(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.parser.keep_alive = True
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(backend)
        response_parser.keep_alive = True

        self.server._on_prx_message(self.server.http_client, response_parser, b"")

        # keep-alive means no close callback
        call_kwargs = frontend.flush_s.call_args[1]
        self.assertIsNone(call_kwargs.get("callback"))

    def test_prx_message_no_keep_alive(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.parser.keep_alive = True
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        response_parser = self._make_response_parser(backend)
        response_parser.keep_alive = False

        self.server._on_prx_message(self.server.http_client, response_parser, b"")

        # no keep-alive means a close callback is set
        call_kwargs = frontend.flush_s.call_args[1]
        self.assertIsNotNone(call_kwargs.get("callback"))

    def test_prx_close_while_waiting(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        backend.waiting = True
        backend.busy = 1
        self.server.busy_conn = 1
        self.server.conn_map[backend] = frontend

        self.server._on_prx_close(self.server.http_client, backend)

        self.assertEqual(frontend.send_response.call_count, 1)
        call_kwargs = frontend.send_response.call_args[1]
        self.assertEqual(call_kwargs["code"], 403)
        self.assertNotIn(backend, self.server.conn_map)
        self.assertEqual(self.server.busy_conn, 0)

    def test_prx_close_after_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        backend.waiting = False
        self.server.conn_map[backend] = frontend

        self.server._on_prx_close(self.server.http_client, backend)

        frontend.close.assert_called_once_with(flush=True)
        self.assertNotIn(backend, self.server.conn_map)

    def test_prx_close_no_mapping(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        backend = self._make_backend()

        # should not raise when backend is not in conn_map
        self.server._on_prx_close(self.server.http_client, backend)

    def test_prx_error_sends_500(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        backend = self._make_backend()
        backend.waiting = True
        self.server.conn_map[backend] = frontend

        self.server._on_prx_error(
            self.server.http_client, backend, Exception("connection timeout")
        )

        self.assertEqual(frontend.send_response.call_count, 1)
        call_kwargs = frontend.send_response.call_args[1]
        self.assertEqual(call_kwargs["code"], 500)

    def test_full_request_response_flow(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        request_parser = self._make_request_parser()
        backend = self._make_backend()

        # routes the front-end request to the backend
        with mock.patch.object(
            self.server.http_client, "method", return_value=(None, backend)
        ):
            self.server.on_headers(frontend, request_parser)

        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.busy_conn, 1)

        response_parser = self._make_response_parser(backend)
        response_parser.headers = {"content-type": "text/html"}

        # simulates back-end response headers
        self.server._on_prx_headers(
            self.server.http_client, response_parser, response_parser.headers
        )
        self.assertEqual(frontend.send_header.call_count, 1)

        # simulates partial body data from the back-end
        self.server._on_prx_partial(self.server.http_client, response_parser, b"<html>")
        self.server._on_prx_partial(
            self.server.http_client, response_parser, b"</html>"
        )
        self.assertEqual(frontend.send_part.call_count, 2)

        # completes the back-end response
        self.server._on_prx_message(self.server.http_client, response_parser, b"")
        self.assertEqual(frontend.flush_s.call_count, 1)
        self.assertEqual(self.server.busy_conn, 0)

    def test_busy_conn_multiple_requests(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend1 = self._make_frontend()
        frontend2 = self._make_frontend()
        backend1 = self._make_backend()
        backend2 = self._make_backend()

        # routes two requests to different backends
        with mock.patch.object(
            self.server.http_client, "method", return_value=(None, backend1)
        ):
            self.server.on_headers(frontend1, self._make_request_parser())

        with mock.patch.object(
            self.server.http_client, "method", return_value=(None, backend2)
        ):
            self.server.on_headers(frontend2, self._make_request_parser())

        self.assertEqual(self.server.busy_conn, 2)

        # completes the first request
        parser1 = self._make_response_parser(backend1)
        self.server._on_prx_message(self.server.http_client, parser1, b"")
        self.assertEqual(self.server.busy_conn, 1)

        # completes the second request
        parser2 = self._make_response_parser(backend2)
        self.server._on_prx_message(self.server.http_client, parser2, b"")
        self.assertEqual(self.server.busy_conn, 0)

    def test_x_forwarded_headers(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.address = ("192.168.1.100", 54321)
        request_parser = self._make_request_parser(host="host.com")
        backend = self._make_backend()

        captured_headers = {}

        def capture_method(method, url, **kwargs):
            captured_headers.update(kwargs.get("headers", {}))
            return (None, backend)

        with mock.patch.object(
            self.server.http_client, "method", side_effect=capture_method
        ):
            self.server.on_headers(frontend, request_parser)

        self.assertEqual(captured_headers.get("x-forwarded-for"), "192.168.1.100")
        self.assertEqual(captured_headers.get("x-forwarded-proto"), "http")
        self.assertEqual(captured_headers.get("x-forwarded-host"), "host.com")
        self.assertEqual(captured_headers.get("x-real-ip"), "192.168.1.100")
        self.assertEqual(captured_headers.get("x-client-ip"), "192.168.1.100")

    def test_accept_encoding_auto(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"}, encoding="auto"
        )
        try:
            frontend = self._make_frontend()
            request_parser = self._make_request_parser(host="host.com")
            request_parser.headers["accept-encoding"] = "gzip, deflate"
            backend = self._make_backend()

            captured_headers = {}

            def capture_method(method, url, **kwargs):
                captured_headers.update(kwargs.get("headers", {}))
                return (None, backend)

            with mock.patch.object(
                server.http_client, "method", side_effect=capture_method
            ):
                server.on_headers(frontend, request_parser)

            # the back-end must be asked for the identity coding so that the
            # proxy becomes the compression authority for the edge
            self.assertEqual(captured_headers.get("accept-encoding"), "identity")

            # the codings accepted by the client must have been recorded
            # before the request headers were rewritten
            self.assertEqual(frontend.resolve_encoding.call_count, 1)
        finally:
            server.cleanup()

    def test_accept_encoding_upgrade(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        server = netius.extra.ReverseProxyServer(
            hosts={"host.com": "http://localhost"}, encoding="auto"
        )
        try:
            frontend = self._make_frontend()
            request_parser = self._make_upgrade_parser(host="host.com")
            request_parser.headers["accept-encoding"] = "gzip, deflate"
            backend = self._make_backend()

            with mock.patch.object(server.raw_client, "connect", return_value=backend):
                server.on_headers(frontend, request_parser)

            # an upgrade is bridged through a raw tunnel that bypasses the
            # encoding layer, so the request must be forwarded untouched
            self.assertEqual(request_parser.headers["accept-encoding"], "gzip, deflate")
            self.assertEqual(frontend.tunnel_c, backend)
        finally:
            server.cleanup()

    def _make_frontend(self):
        frontend = mock.MagicMock()
        frontend.ssl = False
        frontend.address = ("127.0.0.1", 12345)
        frontend.current = 0
        frontend.parser = mock.MagicMock()
        frontend.parser.keep_alive = True
        frontend.parser.version = netius.common.HTTP_11
        frontend.is_throttleable.return_value = False
        frontend.is_exhausted.return_value = False
        frontend.is_restored.return_value = True
        frontend.is_chunked.return_value = False
        frontend.is_gzip.return_value = False
        frontend.is_deflate.return_value = False
        frontend.is_compressed.return_value = False
        frontend.is_measurable.return_value = True
        frontend.encoding_w.return_value = netius.common.PLAIN_ENCODING
        frontend.encoding_name.return_value = None
        frontend.encodings_a = None
        frontend.encoding_b = None
        frontend.ctx_request.return_value = mock.MagicMock()
        # removes dynamic attributes that on_headers checks via hasattr
        del frontend.prefix
        del frontend.state
        del frontend.proxy_c
        del frontend.tunnel_c
        return frontend

    def _make_backend(self):
        backend = mock.MagicMock()
        backend.current = 0
        backend.address = ("10.0.0.1", 8080)
        backend.waiting = False
        backend.busy = 0
        backend.state = None
        backend.error_url = None
        backend.is_throttleable.return_value = False
        backend.is_exhausted.return_value = False
        backend.is_restored.return_value = True
        return backend

    def _make_request_parser(self, host="host.com", method="GET", path="/test"):
        parser = mock.MagicMock()
        parser.method = method
        parser.method_s = method
        parser.path_s = path
        parser.version_s = "HTTP/1.1"
        parser.headers = {"host": host}
        return parser

    def _make_upgrade_parser(self, host="host.com", path="/socket"):
        parser = self._make_request_parser(host=host, method="GET", path=path)
        parser.headers = {
            "host": host,
            "connection": "Upgrade",
            "upgrade": "websocket",
            "sec-websocket-key": "dGhlIHNhbXBsZSBub25jZQ==",
            "sec-websocket-version": "13",
        }
        # the raw header block preserves the original (case sensitive) header
        # names exactly as received, the leading separator follows the format
        # produced by the HTTP parser
        parser.headers_s = netius.legacy.bytes(
            "\r\nHost: %s\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n"
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            "Sec-WebSocket-Version: 13" % host
        )
        return parser

    def _make_response_parser(self, backend, code="200", status="OK"):
        parser = mock.MagicMock()
        parser.owner = backend
        parser.code_s = code
        parser.status_s = status
        parser.version_s = "HTTP/1.1"
        parser.version = netius.common.HTTP_11
        parser.headers = {}
        parser.keep_alive = True
        parser.content_l = 100
        return parser

    def test_throttle_connection(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.renable = False
        backend = self._make_backend()

        # removes `_protocol` so that getattr falls back to the
        # connection itself as the conn_map key (old architecture)
        del backend._protocol

        self.server.conn_map[backend] = frontend
        self.server._throttle(backend)

        self.assertEqual(frontend.enable_read.call_count, 1)

    def test_throttle_transport(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.renable = False
        backend = self._make_backend()
        self.server.conn_map[backend] = frontend

        # creates a transport mock whose `_protocol` points to the
        # backend, simulating the new protocol architecture path
        transport = mock.MagicMock()
        transport.is_restored.return_value = True
        transport._protocol = backend

        self.server._throttle(transport)

        self.assertEqual(frontend.enable_read.call_count, 1)

    def test_throttle_not_restored(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        frontend = self._make_frontend()
        frontend.renable = False
        backend = self._make_backend()
        backend.is_restored.return_value = False
        self.server.conn_map[backend] = frontend

        self.server._throttle(backend)

        self.assertEqual(frontend.enable_read.call_count, 0)

    def test_close_no_loop_destroys_before_event(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # creates a real StreamProtocol to exercise the actual
        # close -> close_c -> delay -> finish -> destroy chain
        backend = netius.StreamProtocol()
        backend.open_c()

        # sets up the attributes that the proxy expects on
        # a backend connection (normally set during on_headers)
        backend.waiting = True
        backend.busy = 1
        backend.state = None
        backend.error_url = None
        backend.current = 0
        backend.address = ("10.0.0.1", 8080)

        # wire a frontend mock into the conn_map
        frontend = self._make_frontend()
        self.server.conn_map[backend] = frontend
        self.server.busy_conn = 1

        # verify the protocol has no loop, which is the
        # precondition for the bug
        self.assertIsNone(backend._loop)

        # simulate the event relay that HTTPClient.method()
        # would normally set up via _relay_protocol_events
        self.server.http_client._relay_protocol_events(backend)

        # close the backend protocol, this is the operation
        # that should trigger _on_prx_close via the event relay
        # but when _loop is None the events are unbound before
        # the "close" trigger fires
        backend.close()

        # the conn_map entry should have been cleaned up by
        # _on_prx_close but because finish() ran synchronously
        # and destroyed all bindings before trigger("close"),
        # the entry remains (this is the bug)
        self.assertNotIn(backend, self.server.conn_map)
        self.assertEqual(self.server.busy_conn, 0)

    def _make_apply_headers_parser(self, version=None, keep_alive=None, headers=None):
        # produces a parser stand-in whose `keep_alive` flag follows the
        # rules in `netius.common.HTTPParser._parse_headers` for the
        # given HTTP version and `Connection` header value, this avoids
        # a full parser bootstrap while keeping the matrix faithful
        if version == None:
            version = netius.common.HTTP_11
        if keep_alive == None:
            keep_alive = version >= netius.common.HTTP_11
        parser = mock.MagicMock()
        parser.version = version
        parser.version_s = (
            "HTTP/1.0" if version == netius.common.HTTP_10 else "HTTP/1.1"
        )
        parser.keep_alive = keep_alive
        parser.headers = dict(headers) if headers else {}
        parser.content_l = 0
        parser.code_s = "200"
        parser.status_s = "OK"
        parser.owner = self._make_apply_headers_connection()
        return parser

    def _make_apply_headers_connection(self):
        # builds a minimal connection mock that satisfies the encoding
        # and chunking probes done by `_apply_all` / `_apply_connection`
        connection = mock.MagicMock()
        connection.address = ("127.0.0.1", 12345)
        connection.current = 0
        connection.is_chunked.return_value = False
        connection.is_gzip.return_value = False
        connection.is_deflate.return_value = False
        connection.is_compressed.return_value = False
        connection.is_measurable.return_value = True
        connection.encoding_w.return_value = netius.common.PLAIN_ENCODING
        connection.encoding_name.return_value = None
        connection.encodings_a = None
        return connection


class ReverseProxyIntegrationTest(unittest.TestCase):
    """
    End-to-end integration tests for the reverse proxy.

    Starts a real ReverseProxyServer in a background thread
    and makes HTTP requests through it to an httpbin
    backend. Verifies the complete data flow including
    routing, header forwarding (Via, X-Forwarded-*),
    response relay, body integrity, and error handling
    for unmatched hosts.

    These tests exercise the protocol-level address
    attribute and other backward-compatibility properties
    that are only reachable through actual network I/O.

    Requires network; skipped when NO_NETWORK is set.
    """

    @classmethod
    def setUpClass(cls):
        if http_client == None:
            return

        if netius.conf("NO_NETWORK", False, cast=bool):
            return

        cls.httpbin = netius.conf("HTTPBIN", "httpbin.org")

        # create a reverse proxy that forwards all requests to httpbin
        cls.server = netius.extra.ReverseProxyServer(
            hosts={"default": "http://%s" % cls.httpbin},
            env=False,
            resolve=False,
        )
        cls.server.x_forwarded_proto = None
        cls.server.x_forwarded_port = None

        # call serve() with start=False to bind the socket and set up
        # the poll without entering the event loop yet, using port 0
        # lets the OS pick a free port which is retrieved afterwards
        cls.server.serve(host="127.0.0.1", port=0, start=False)
        cls.proxy_port = cls.server.port

        # start the proxy server event loop in a background thread
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()

        # wait for the server to be ready (accepting connections)
        for _i in range(50):
            time.sleep(0.1)
            try:
                probe = socket.create_connection(
                    ("127.0.0.1", cls.proxy_port), timeout=1
                )
                probe.close()
                break
            except (ConnectionRefusedError, OSError):
                continue

    @classmethod
    def tearDownClass(cls):
        if not hasattr(cls, "server"):
            return
        cls.server.stop()
        cls.server_thread.join(timeout=5)

    def setUp(self):
        if http_client == None:
            self.skipTest("Skipping test: http.client unavailable")
        if netius.conf("NO_NETWORK", False, cast=bool):
            self.skipTest("Network access is disabled")

    def test_simple_get(self):
        code, _headers, body = self._request("/get")
        self.assertEqual(code, 200)
        self.assertGreater(len(body), 0)

    def test_response_body_integrity(self):
        code, _headers, body = self._request("/get")
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("headers", data)
        self.assertIn("url", data)

    def test_via_header(self):
        code, headers, _body = self._request("/get")
        self.assertEqual(code, 200)
        via = headers.get("Via", None)
        self.assertIsNotNone(via, "Proxy should add a Via header to the response")

    def test_x_forwarded_headers_sent(self):
        code, _headers, body = self._request("/get")
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        request_headers = data.get("headers", {})

        # httpbin echoes the request headers back to us,
        # build a case-insensitive lookup since different httpbin
        # implementations normalize casing differently
        headers_lower = {k.lower(): v for k, v in request_headers.items()}

        # verify the proxy injected the x-forwarded-* headers,
        # note that some httpbin variants or upstream proxies may
        # strip certain headers, so we check for the ones that are
        # reliably passed through
        self.assertIn("x-forwarded-host", headers_lower)
        self.assertIn("x-client-ip", headers_lower)

    def test_404_no_match(self):
        connection = http_client.HTTPConnection(
            "127.0.0.1", self.proxy_port, timeout=30
        )

        # the shared server routes every host through a default (catch-all)
        # rule, so it must be unset for the request to be an unmatched one
        hosts = self.server.hosts
        self.server.hosts = dict()
        try:
            connection.request(
                "GET", "/get", headers={"Host": "unknown.host.example.com"}
            )
            response = connection.getresponse()
            response.read()
            self.assertEqual(response.status, 404)
        finally:
            self.server.hosts = hosts
            connection.close()

    def test_multiple_requests(self):
        for _i in range(3):
            code, _headers, body = self._request("/get")
            self.assertEqual(code, 200)
            self.assertGreater(len(body), 0)

    def test_post_with_body(self):
        payload = json.dumps({"key": "value"}).encode("utf-8")
        code, _headers, body = self._request(
            "/post",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=payload,
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("data", data)
        self.assertIn("key", data.get("json", {}))

    def test_put_with_body(self):
        payload = b"updated content"
        code, _headers, body = self._request(
            "/put",
            method="PUT",
            headers={"Content-Type": "text/plain"},
            body=payload,
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("data"), "updated content")

    def test_delete(self):
        code, _headers, _body = self._request("/delete", method="DELETE")
        self.assertEqual(code, 200)

    def _request(self, path, method="GET", headers=None, body=None):
        conn = http_client.HTTPConnection("127.0.0.1", self.proxy_port, timeout=30)
        try:
            _headers = {"Host": self.httpbin}
            if headers:
                _headers.update(headers)
            conn.request(method, path, body=body, headers=_headers)
            response = conn.getresponse()
            response_body = response.read()
            response_headers = dict(response.getheaders())
            return response.status, response_headers, response_body
        finally:
            conn.close()


class ReverseProxyCompressionTest(unittest.TestCase):
    """
    End-to-end tests for the automatic encoding mode of the reverse
    proxy.

    Starts a real WSGI back-end and a real reverse proxy running
    under the `auto` encoding, both in background threads and both
    bound to the loopback interface, so that the complete negotiation
    (client, proxy and back-end) is exercised without any network
    access.
    """

    BIG = b"netius " * 900

    SMALL = b"ab"

    JPEG = b"\xff\xd8" + b"j" * 4000

    ENCODED = zlib.compress(b"netius " * 900)

    BROTLI = b"\x1b\x2e\x00\x00" + b"b" * 200

    @classmethod
    def setUpClass(cls):
        if http_client == None:
            return

        cls.backend = netius.servers.WSGIServer(app=cls._app, env=False)
        cls.backend.serve(host="127.0.0.1", port=0, start=False)
        cls.backend_port = cls.backend.port
        cls.backend_thread = threading.Thread(target=cls.backend.start, daemon=True)
        cls.backend_thread.start()
        cls._wait(cls.backend_port)

        cls.server = netius.extra.ReverseProxyServer(
            hosts={"default": "http://127.0.0.1:%d" % cls.backend_port},
            encoding="auto",
            env=False,
            resolve=False,
        )
        cls.server.serve(host="127.0.0.1", port=0, start=False)
        cls.proxy_port = cls.server.port
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()
        cls._wait(cls.proxy_port)

    @classmethod
    def tearDownClass(cls):
        # stops each of the services on its own, as the construction of the
        # proxy may have failed leaving the back-end still running
        if hasattr(cls, "server"):
            cls.server.stop()
            cls.server_thread.join(timeout=5)
        if hasattr(cls, "backend"):
            cls.backend.stop()
            cls.backend_thread.join(timeout=5)

    def setUp(self):
        if http_client == None:
            self.skipTest("Skipping test: http.client unavailable")

    def test_compress_identity(self):
        _code, headers, body = self._request("/big")

        # a payload that arrives from the back-end under the identity coding
        # must be compressed with the coding accepted by the client
        self.assertEqual(headers.get("Content-Encoding"), "gzip")
        self.assertEqual(headers.get("Transfer-Encoding"), "chunked")
        self.assertEqual(headers.get("Vary"), "Accept-Encoding")
        self.assertEqual(self._decode(body, "gzip"), self.BIG)
        self.assertLess(len(body), len(self.BIG))

        # the coding must be the one accepted by the client and not the one
        # preferred by the proxy whenever they do not intersect
        _code, headers, body = self._request("/big", accept="deflate")
        self.assertEqual(headers.get("Content-Encoding"), "deflate")
        self.assertEqual(self._decode(body, "deflate"), self.BIG)

    def test_compress_not_accepted(self):
        for accept in (None, "identity", "gzip;q=0, deflate;q=0"):
            _code, headers, body = self._request("/big", accept=accept)

            # a client that does not accept any of the supported codings must
            # never be handed a compressed payload
            self.assertEqual(headers.get("Content-Encoding"), None)
            self.assertEqual(headers.get("Content-Length"), str(len(self.BIG)))
            self.assertEqual(body, self.BIG)

            # the representation still depends on the codings accepted, so
            # the vary header must be announced (avoids cache poisoning)
            self.assertEqual(headers.get("Vary"), "Accept-Encoding")

    def test_compress_encoded(self):
        # a payload that already arrives encoded must be forwarded
        # byte-identical, never being decoded and re-encoded
        _code, headers, body = self._request("/encoded")
        self.assertEqual(headers.get("Content-Encoding"), "deflate")
        self.assertEqual(body, self.ENCODED)
        self.assertEqual(headers.get("Vary"), None)

        # a coding that Netius is not able to decode must be forwarded in
        # the very same way, instead of taking the response down
        _code, headers, body = self._request("/brotli")
        self.assertEqual(headers.get("Content-Encoding"), "br")
        self.assertEqual(body, self.BROTLI)

    def test_compress_bounds(self):
        # a payload that is too small to pay for the framing overhead must
        # be forwarded as is, keeping its exact length
        _code, headers, body = self._request("/small")
        self.assertEqual(headers.get("Content-Encoding"), None)
        self.assertEqual(headers.get("Content-Length"), str(len(self.SMALL)))
        self.assertEqual(headers.get("Vary"), None)

        # a payload that is larger than the configured maximum must not be
        # compressed either, keeping the cost of the compression bounded
        compress_max = self.server.compress_max
        self.server.compress_max = 128
        try:
            _code, headers, body = self._request("/big")
            self.assertEqual(headers.get("Content-Encoding"), None)
            self.assertEqual(body, self.BIG)
        finally:
            self.server.compress_max = compress_max

    def test_compress_types(self):
        # a media type for which the compression provides no relevant gain
        # must be forwarded as is, with no vary announcement
        _code, headers, body = self._request("/jpeg")
        self.assertEqual(headers.get("Content-Encoding"), None)
        self.assertEqual(body, self.JPEG)
        self.assertEqual(headers.get("Vary"), None)

    def test_compress_preserve(self):
        # the no-transform cache directive forbids the proxy from changing
        # the coding of the payload
        _code, headers, body = self._request("/no-transform")
        self.assertEqual(headers.get("Content-Encoding"), None)
        self.assertEqual(body, self.BIG)

        # a response to a HEAD request carries no payload and so there's
        # nothing in it that may be compressed
        _code, headers, _body = self._request("/big", method="HEAD")
        self.assertEqual(headers.get("Content-Encoding"), None)

    def test_compress_deferred(self):
        # a back-end that streams with no declared length must have the
        # decision deferred until the minimum size has been crossed
        _code, headers, body = self._request("/stream")
        self.assertEqual(headers.get("Content-Encoding"), "gzip")
        self.assertEqual(self._decode(body, "gzip"), self.BIG)

        # a streamed payload that ends below the minimum size must be
        # forwarded as identity announcing its exact length
        _code, headers, body = self._request("/trickle")
        self.assertEqual(headers.get("Content-Encoding"), None)
        self.assertEqual(headers.get("Content-Length"), "4")
        self.assertEqual(body, b"tiny")

        # with the deferred decision disabled the size of the payload cannot
        # be verified, so a streamed back-end is forwarded untouched
        compress_buffer = self.server.compress_buffer
        self.server.compress_buffer = False
        try:
            _code, headers, body = self._request("/stream")
            self.assertEqual(headers.get("Content-Encoding"), None)
            self.assertEqual(body, self.BIG)
        finally:
            self.server.compress_buffer = compress_buffer

    def _decode(self, data, encoding):
        if encoding == "gzip":
            return zlib.decompress(data, zlib.MAX_WBITS | 16)
        try:
            return zlib.decompress(data)
        except zlib.error:
            return zlib.decompress(data, -zlib.MAX_WBITS)

    def _request(self, path, method="GET", accept="gzip, deflate"):
        conn = http_client.HTTPConnection("127.0.0.1", self.proxy_port, timeout=30)
        try:
            headers = {"Host": "compress.example.com"}
            if not accept == None:
                headers["Accept-Encoding"] = accept
            conn.request(method, path, headers=headers)
            response = conn.getresponse()
            response_body = response.read()
            response_headers = dict(response.getheaders())
            return response.status, response_headers, response_body
        finally:
            conn.close()

    @classmethod
    def _app(cls, environ, start_response):
        path = environ["PATH_INFO"]
        if path == "/big":
            body, headers = cls.BIG, [("Content-Type", "text/plain")]
        elif path == "/small":
            body, headers = cls.SMALL, [("Content-Type", "text/plain")]
        elif path == "/jpeg":
            body, headers = cls.JPEG, [("Content-Type", "image/jpeg")]
        elif path == "/encoded":
            body, headers = cls.ENCODED, [
                ("Content-Type", "text/plain"),
                ("Content-Encoding", "deflate"),
            ]
        elif path == "/brotli":
            body, headers = cls.BROTLI, [
                ("Content-Type", "text/plain"),
                ("Content-Encoding", "br"),
            ]
        elif path == "/no-transform":
            body, headers = cls.BIG, [
                ("Content-Type", "text/plain"),
                ("Cache-Control", "no-transform"),
            ]
        elif path == "/stream":
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [cls.BIG[:3000], cls.BIG[3000:]]
        elif path == "/trickle":
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"tiny"]
        else:
            body, headers = b"not found", [("Content-Type", "text/plain")]
        headers.append(("Content-Length", str(len(body))))
        start_response("200 OK", headers)
        return [body]

    @classmethod
    def _wait(cls, port):
        for _i in range(50):
            time.sleep(0.1)
            try:
                probe = socket.create_connection(("127.0.0.1", port), timeout=1)
                probe.close()
                break
            except (ConnectionRefusedError, OSError):
                continue


class ReverseProxyMatrixTest(unittest.TestCase):
    """
    Matrix tests covering every combination of the `ENCODING` and
    `DYNAMIC` options of the reverse proxy against every permutation of
    the coding used by the back-end response and of the codings accepted
    by the front-end request.

    Instead of a hand written expectation per cell the tests assert the
    invariants that must hold in every one of them, the most important
    being that the coding announced to the client is always the coding
    that has been applied to the payload.
    """

    PAYLOAD = b"netius " * 900

    BROTLI = b"\x1b\x2e\x00\x00" + b"b" * 200

    ENCODINGS = ("plain", "chunked", "gzip", "deflate", "auto")

    DYNAMICS = (True, False)

    SOURCES = ("identity", "gzip", "deflate", "zlib", "br")

    SPECIALS = ("204", "304", "206", "explicit")

    ACCEPTS = (None, "identity", "gzip", "deflate", "gzip, deflate", "*")

    @classmethod
    def setUpClass(cls):
        if http_client == None:
            return

        cls.servers = []

        cls.backend = netius.servers.WSGIServer(app=cls._app, env=False)
        cls.backend.serve(host="127.0.0.1", port=0, start=False)
        cls.backend_port = cls.backend.port
        cls.backend_thread = threading.Thread(target=cls.backend.start, daemon=True)
        cls.backend_thread.start()
        cls._wait(cls.backend_port)

        # builds one proxy per combination of the encoding and dynamic
        # options, so that every cell of the matrix has its own server
        cls.ports = dict()
        for encoding in cls.ENCODINGS:
            for dynamic in cls.DYNAMICS:
                server = netius.extra.ReverseProxyServer(
                    hosts={"default": "http://127.0.0.1:%d" % cls.backend_port},
                    encoding=encoding,
                    dynamic=dynamic,
                    env=False,
                    resolve=False,
                )
                server.serve(host="127.0.0.1", port=0, start=False)
                thread = threading.Thread(target=server.start, daemon=True)
                thread.start()
                cls._wait(server.port)
                cls.ports[(encoding, dynamic)] = server.port
                cls.servers.append((server, thread))

    @classmethod
    def tearDownClass(cls):
        # stops each of the services on its own, as the construction of a
        # proxy may have failed leaving the back-end still running
        for server, thread in getattr(cls, "servers", []):
            server.stop()
            thread.join(timeout=5)
        if hasattr(cls, "backend"):
            cls.backend.stop()
            cls.backend_thread.join(timeout=5)

    def setUp(self):
        if http_client == None:
            self.skipTest("Skipping test: http.client unavailable")

    def test_matrix_integrity(self):
        # the payload received by the client must always be recoverable
        # using the coding that has been announced to it, this is the
        # invariant that both of the reported header lies violated
        failures = []
        for encoding, dynamic, source, accept in self._matrix():
            failures += self._verify_integrity(encoding, dynamic, source, accept)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def test_matrix_negotiation(self):
        # under the automatic mode a coding must never be applied unless
        # the client has explicitly accepted it, the remaining modes keep
        # their documented (server wide) behaviour
        failures = []
        for encoding, dynamic, source, accept in self._matrix():
            failures += self._verify_negotiation(encoding, dynamic, source, accept)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def test_matrix_passthrough(self):
        # a payload that arrives from the back-end already encoded must
        # keep its coding, and one under a coding that cannot be decoded
        # must be forwarded byte-identical instead of taking it down
        failures = []
        for encoding, dynamic, source, accept in self._matrix():
            failures += self._verify_passthrough(encoding, dynamic, source, accept)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def test_matrix_framing(self):
        # a response that cannot carry a payload must never announce either a
        # framing or a coding, a partial one must never be transformed and the
        # identity coding must never be announced to the client
        failures = []
        for encoding in self.ENCODINGS:
            for dynamic in self.DYNAMICS:
                for source in self.SPECIALS:
                    failures += self._verify_framing(encoding, dynamic, source)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def test_matrix_http_10(self):
        # the chunked framing requires HTTP/1.1, so an older front-end must
        # never have it announced and must still receive the complete payload
        failures = []
        for encoding in self.ENCODINGS:
            for dynamic in self.DYNAMICS:
                failures += self._verify_http_10(encoding, dynamic)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def test_matrix_vary(self):
        # the vary header must be announced exactly for the responses whose
        # representation depends on the codings accepted by the client
        failures = []
        for encoding, dynamic, source, accept in self._matrix():
            failures += self._verify_vary(encoding, dynamic, source, accept)
        self.assertEqual(failures, [], "\n".join([""] + failures))

    def _matrix(self):
        for encoding in self.ENCODINGS:
            for dynamic in self.DYNAMICS:
                for source in self.SOURCES:
                    for accept in self.ACCEPTS:
                        yield encoding, dynamic, source, accept

    def _verify_integrity(self, encoding, dynamic, source, accept):
        label, headers, body = self._cell(encoding, dynamic, source, accept)
        announced = headers.get("Content-Encoding", None)
        length = headers.get("Content-Length", None)
        failures = []

        # the length announced to the client, whenever it exists, must
        # match the amount of payload that has been received by it
        if length and not int(length) == len(body):
            failures.append("%s: length %s but %d bytes" % (label, length, len(body)))

        # the payload must decode under the announced coding and match the
        # one of the origin, an unknown coding is verified as pass-through
        try:
            payload = self._decode(announced, body)
        except zlib.error:
            return failures + ["%s: '%s' payload is not decodable" % (label, announced)]
        if payload == None:
            expected = self.BROTLI
            payload = body
        else:
            expected = self.PAYLOAD
        if not payload == expected:
            failures.append("%s: payload does not match the origin" % label)

        return failures

    def _verify_negotiation(self, encoding, dynamic, source, accept):
        if not encoding == "auto":
            return []
        label, headers, _body = self._cell(encoding, dynamic, source, accept)
        announced = headers.get("Content-Encoding", None)

        # only the payloads that arrive under the identity coding may be
        # compressed by the proxy, so any coding announced for one of them
        # is a coding that the proxy itself has applied
        if not source == "identity":
            return []
        if not announced:
            return []
        accepted = netius.common.parse_encodings(accept or "")
        if announced in accepted:
            return []
        return ["%s: '%s' was applied but not accepted" % (label, announced)]

    def _verify_passthrough(self, encoding, dynamic, source, accept):
        if source == "identity":
            return []
        label, headers, body = self._cell(encoding, dynamic, source, accept)
        announced = headers.get("Content-Encoding", None)

        # a coding that Netius is not able to decode must always be kept
        # and its payload forwarded without a single byte being changed,
        # independently of the mode the proxy is running under
        if source == "br":
            if announced == "br" and body == self.BROTLI:
                return []
            return ["%s: '%s' was not forwarded as is" % (label, announced)]

        # the modes that re-encode the payload decode it first, so the coding
        # of the back-end is legitimately replaced by the one of the proxy
        # (which may be the identity for the uncompressed encodings)
        if not encoding == "auto" and not dynamic:
            return []

        # for the pass-through modes an already encoded payload must never
        # reach the client under the identity coding, as that would mean the
        # coding of the back-end has been silently dropped
        if announced:
            return []
        return ["%s: the coding of the back-end was dropped" % label]

    def _verify_framing(self, encoding, dynamic, source):
        label = "ENCODING=%s DYNAMIC=%d source=%s" % (
            encoding,
            1 if dynamic else 0,
            source,
        )
        status, headers, body = self._request(
            self.ports[(encoding, dynamic)], "/" + source
        )
        announced = headers.get("Content-Encoding", None)
        transfer = headers.get("Transfer-Encoding", None)
        failures = []

        # the identity coding is not a valid value for the content encoding
        # header, so it must never reach the client
        if announced and announced.lower() == "identity":
            failures.append("%s: the identity coding was announced" % label)

        # a status that cannot carry a payload must have neither the framing
        # nor the coding announced for it
        if source in ("204", "304"):
            if not status == int(source):
                failures.append("%s: status %s" % (label, status))
            if transfer:
                failures.append(
                    "%s: '%s' framing on an empty response" % (label, transfer)
                )
            if announced:
                failures.append(
                    "%s: '%s' coding on an empty response" % (label, announced)
                )
            if body:
                failures.append("%s: payload on an empty response" % label)
            return failures

        # a partial payload must be forwarded untouched, keeping the range
        # that has been announced by the back-end consistent with it
        if source == "206":
            if not status == 206:
                failures.append("%s: status %s" % (label, status))
            if announced:
                failures.append("%s: partial payload was transformed" % label)
            if not body == self.PAYLOAD[:100]:
                failures.append("%s: partial payload does not match" % label)
            if not headers.get("Content-Range", None):
                failures.append("%s: the content range was dropped" % label)

        return failures

    def _verify_http_10(self, encoding, dynamic):
        label = "ENCODING=%s DYNAMIC=%d" % (encoding, 1 if dynamic else 0)
        head, body = self._request_10(self.ports[(encoding, dynamic)], "/identity")
        failures = []

        # the chunked framing is only available from HTTP/1.1 onwards, so it
        # must never be announced to a client that speaks an older version
        if "transfer-encoding" in head.lower():
            failures.append("%s: chunked framing announced to HTTP/1.0" % label)

        # the payload must still arrive complete, delimited by the closing of
        # the connection whenever no length is available for it
        if not body == self.PAYLOAD:
            failures.append("%s: payload does not match the origin" % label)

        return failures

    def _verify_vary(self, encoding, dynamic, source, accept):
        label, headers, _body = self._cell(encoding, dynamic, source, accept)
        vary = headers.get("Vary", None)

        # the remaining modes apply a server wide encoding and so their
        # representation never depends on the codings accepted
        if not encoding == "auto":
            if vary:
                return ["%s: unexpected vary '%s'" % (label, vary)]
            return []

        # under the automatic mode only the payloads that are eligible for
        # compression (the identity ones) depend on the accepted codings
        should_vary = source == "identity"
        if should_vary and not vary == "Accept-Encoding":
            return ["%s: missing vary, got '%s'" % (label, vary)]
        if not should_vary and vary:
            return ["%s: unexpected vary '%s'" % (label, vary)]
        return []

    def _cell(self, encoding, dynamic, source, accept):
        label = "ENCODING=%s DYNAMIC=%d source=%s accept=%s" % (
            encoding,
            1 if dynamic else 0,
            source,
            accept,
        )
        status, headers, body = self._request(
            self.ports[(encoding, dynamic)], "/" + source, accept=accept
        )
        self.assertEqual(status, 200, "%s: status %s" % (label, status))
        return label, headers, body

    def _decode(self, encoding, data):
        # decodes the payload using the announced coding, an invalid value
        # is returned for the codings that are not implemented locally
        if encoding in (None, "identity"):
            return data
        if encoding == "gzip":
            return zlib.decompress(data, zlib.MAX_WBITS | 16)
        if not encoding == "deflate":
            return None
        try:
            return zlib.decompress(data)
        except zlib.error:
            return zlib.decompress(data, -zlib.MAX_WBITS)

    def _request(self, port, path, accept=None):
        conn = http_client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            headers = {"Host": "matrix.example.com"}
            if not accept == None:
                headers["Accept-Encoding"] = accept
            conn.request("GET", path, headers=headers)
            response = conn.getresponse()
            response_body = response.read()
            response_headers = dict(response.getheaders())
            return response.status, response_headers, response_body
        finally:
            conn.close()

    def _request_10(self, port, path):
        # issues the request at the raw socket level, as the standard client
        # is not able to downgrade the version of the request being sent
        sock = socket.create_connection(("127.0.0.1", port), timeout=30)
        try:
            sock.sendall(
                netius.legacy.bytes(
                    "GET %s HTTP/1.0\r\nHost: matrix.example.com\r\n"
                    "Accept-Encoding: gzip, deflate\r\n\r\n" % path
                )
            )
            data = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
        finally:
            sock.close()
        head, _separator, body = data.partition(b"\r\n\r\n")
        return netius.legacy.str(head), body

    @classmethod
    def _app(cls, environ, start_response):
        source = environ["PATH_INFO"].lstrip("/")

        # serves the responses that exercise the framing rules, either
        # because they carry no payload or because they are partial
        if source in ("204", "304"):
            start_response(
                "204 No Content" if source == "204" else "304 Not Modified", []
            )
            return []
        if source == "206":
            start_response(
                "206 Partial Content",
                [
                    ("Content-Type", "text/plain"),
                    ("Content-Range", "bytes 0-99/%d" % len(cls.PAYLOAD)),
                    ("Content-Length", "100"),
                ],
            )
            return [cls.PAYLOAD[:100]]

        body, encoding = cls._source(source)
        headers = [("Content-Type", "text/plain")]
        if encoding:
            headers.append(("Content-Encoding", encoding))
        headers.append(("Content-Length", str(len(body))))
        start_response("200 OK", headers)
        return [body]

    @classmethod
    def _source(cls, source):
        # builds the back-end payload for the requested coding, note that
        # the deflate coding is produced both raw (the variant emitted by
        # a Netius origin) and zlib wrapped (the one of the specification)
        if source == "gzip":
            compressor = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS | 16)
            return compressor.compress(cls.PAYLOAD) + compressor.flush(), "gzip"
        if source == "deflate":
            compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
            return compressor.compress(cls.PAYLOAD) + compressor.flush(), "deflate"
        if source == "zlib":
            return zlib.compress(cls.PAYLOAD), "deflate"
        if source == "br":
            return cls.BROTLI, "br"
        if source == "explicit":
            return cls.PAYLOAD, "identity"
        return cls.PAYLOAD, None

    @classmethod
    def _wait(cls, port):
        for _i in range(50):
            time.sleep(0.1)
            try:
                probe = socket.create_connection(("127.0.0.1", port), timeout=1)
                probe.close()
                break
            except (ConnectionRefusedError, OSError):
                continue
