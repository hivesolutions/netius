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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius
import netius.clients
import netius.clients.http
import netius.clients.raw


class ContainerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.container = netius.Container()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.container.cleanup()

    def test_agent_base_interface(self):
        client = netius.clients.HTTPClient()

        self.assertTrue(hasattr(client, "name"))
        self.assertTrue(hasattr(client, "connections"))
        self.assertTrue(hasattr(client, "load"))
        self.assertTrue(hasattr(client, "unload"))
        self.assertTrue(hasattr(client, "ticks"))
        self.assertTrue(hasattr(client, "on_start"))
        self.assertTrue(hasattr(client, "on_stop"))
        self.assertTrue(hasattr(client, "connections_dict"))

        self.assertEqual(client.name, "HTTPClient")
        self.assertEqual(client.connections, [])
        self.assertEqual(client.connections_dict(), {})

        client.cleanup()

    def test_add_base_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        self.assertEqual(len(self.container.bases), 1)
        self.assertTrue(client in self.container.bases)

        client.cleanup()

    def test_add_base_agent_multiple(self):
        http_client = netius.clients.HTTPClient()
        raw_client = netius.clients.RawClient()
        self.container.add_base(http_client)
        self.container.add_base(raw_client)

        self.assertEqual(len(self.container.bases), 2)
        self.assertIn(http_client, self.container.bases)
        self.assertIn(raw_client, self.container.bases)

        http_client.cleanup()
        raw_client.cleanup()

    def test_remove_base_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)
        self.container.remove_base(client)

        self.assertEqual(len(self.container.bases), 0)

        client.cleanup()

    def test_start_base_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        self.container.start_base(client)

        client.cleanup()

    def test_start_all_agent(self):
        http_client = netius.clients.HTTPClient()
        raw_client = netius.clients.RawClient()
        self.container.add_base(http_client)
        self.container.add_base(raw_client)

        self.container.start_all()

        http_client.cleanup()
        raw_client.cleanup()

    def test_ticks_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        self.container.ticks()

        client.cleanup()

    def test_call_all_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        self.container.call_all("on_start")
        self.container.call_all("on_stop")

        client.cleanup()

    def test_trigger_all_agent(self):
        triggered = []
        client = netius.clients.HTTPClient()
        client.bind("test_event", lambda *args: triggered.append(True))
        self.container.add_base(client)

        self.container.trigger_all("test_event")

        self.assertEqual(len(triggered), 1)

        client.cleanup()

    def test_connections_dict_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        result = self.container.connections_dict()

        self.assertEqual(isinstance(result, dict), True)
        self.assertIn("HTTPClient", result)
        self.assertEqual(result["HTTPClient"], {})

        client.cleanup()

    def test_connection_dict_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        result = self.container.connection_dict(1)

        self.assertEqual(result, None)

        client.cleanup()

    def test_apply_base_agent(self):
        client = netius.clients.HTTPClient()
        self.container.add_base(client)

        self.assertTrue(hasattr(client, "tid"))
        self.assertTrue(hasattr(client, "poll"))
        self.assertTrue(hasattr(client, "level"))
        self.assertTrue(hasattr(client, "logger"))
        self.assertTrue(hasattr(client, "poll_owner"))

        client.cleanup()

    def test_cleanup_agent(self):
        http_client = netius.clients.HTTPClient()
        raw_client = netius.clients.RawClient()
        self.container.add_base(http_client)
        self.container.add_base(raw_client)

        self.container.cleanup()

        self.assertEqual(len(self.container.bases), 0)

    def test_container_loop_agent(self):
        server = netius.StreamServer()
        http_client = netius.clients.HTTPClient()
        raw_client = netius.clients.RawClient()

        self.container.add_base(server)
        self.container.add_base(http_client)
        self.container.add_base(raw_client)

        self.assertFalse(hasattr(server, "_container_loop"))
        self.assertTrue(hasattr(http_client, "_container_loop"))
        self.assertTrue(hasattr(raw_client, "_container_loop"))

        server.cleanup()
        http_client.cleanup()
        raw_client.cleanup()

    def test_container_loop_not_on_base(self):
        server = netius.StreamServer()
        self.container.add_base(server)

        self.assertFalse(hasattr(server, "_container_loop"))

        server.cleanup()

    def test_http_client_event_relay(self):
        client = netius.clients.HTTPClient()
        events_received = []

        client.bind("headers", lambda *args: events_received.append("headers"))
        client.bind("message", lambda *args: events_received.append("message"))
        client.bind("partial", lambda *args: events_received.append("partial"))
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

        client.cleanup()

    def test_raw_client_event_relay(self):
        client = netius.clients.RawClient()
        events_received = []

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

    def test_mixed_base_and_agent(self):
        server = netius.StreamServer()
        http_client = netius.clients.HTTPClient()
        raw_client = netius.clients.RawClient()

        self.container.add_base(server)
        self.container.add_base(http_client)
        self.container.add_base(raw_client)

        self.assertEqual(len(self.container.bases), 3)

        # runs all lifecycle operations to ensure no errors
        self.container.start_all()
        self.container.ticks()
        self.container.call_all("on_start")
        self.container.call_all("on_stop")
        self.container.connections_dict()
        self.container.connection_dict(1)

        server.cleanup()
        http_client.cleanup()
        raw_client.cleanup()
