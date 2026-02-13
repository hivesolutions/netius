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
import unittest
import collections

import netius
import netius.extra
import netius.clients

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
        self.server.x_forwarded_proto = None
        self.server.x_forwarded_port = None

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

    def test_cleanup(self):
        server = netius.extra.ReverseProxyServer(hosts={"host.com": "http://localhost"})
        server.cleanup()

        self.assertIsNone(server.container)
        self.assertIsNone(server.http_client)
        self.assertIsNone(server.raw_client)

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

    def _make_frontend(self):
        frontend = mock.MagicMock()
        frontend.ssl = False
        frontend.address = ("127.0.0.1", 12345)
        frontend.current = 0
        frontend.parser = mock.MagicMock()
        frontend.parser.keep_alive = True
        frontend.is_throttleable.return_value = False
        frontend.is_exhausted.return_value = False
        frontend.is_restored.return_value = True
        frontend.is_chunked.return_value = False
        frontend.is_gzip.return_value = False
        frontend.is_deflate.return_value = False
        frontend.is_compressed.return_value = False
        frontend.is_measurable.return_value = True
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
        parser.path_s = path
        parser.version_s = "HTTP/1.1"
        parser.headers = {"host": host}
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

    def test_close_no_loop_destroys_before_event(self):
        """
        When a `Protocol` has no event loop (`_loop` is None),
        `close_c()` calls `delay(self.finish)` which invokes
        `finish()` immediately (synchronously). `finish()` calls
        `destroy()` -> `unbind_all()` which removes all event
        handlers. Then when `close()` reaches `trigger("close")`
        the handler list is already empty and the relay never
        fires, so `_on_prx_close` is never called and the
        `conn_map` entry is never cleaned up.

        This test reproduces the scenario using a real
        `StreamProtocol` whose `_loop` is None.
        """

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
