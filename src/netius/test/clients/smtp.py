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

import netius.clients


class SMTPClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.original_query_s = netius.clients.DNSClient.__dict__["query_s"]
        self.original_connect = netius.clients.SMTPClient.connect
        self.original_ensure_loop = netius.clients.SMTPClient.ensure_loop
        self.connections = []
        self.dns_queries = []
        self.clients = []
        self._dns_resolver = None

        connections = self.connections
        dns_queries = self.dns_queries

        def mock_connect(self, host, port):
            connection = _MockSMTPConnection(host, port)
            connections.append(connection)
            return connection

        def mock_ensure_loop(self):
            pass

        def mock_query_s(name, type="a", cls_="in", ns=None, callback=None, loop=None):
            dns_queries.append(name)
            if self._dns_resolver:
                response = self._dns_resolver(name)
                if callback:
                    callback(response)
                return
            raise AssertionError("Unexpected DNS query: %s" % name)

        netius.clients.DNSClient.query_s = staticmethod(mock_query_s)
        netius.clients.SMTPClient.connect = mock_connect
        netius.clients.SMTPClient.ensure_loop = mock_ensure_loop

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for client in self.clients:
            client.cleanup()
        netius.clients.DNSClient.query_s = self.original_query_s
        netius.clients.SMTPClient.connect = self.original_connect
        netius.clients.SMTPClient.ensure_loop = self.original_ensure_loop

    def test_message_direct_host(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            mark=False,
        )

        self.assertEqual(len(self.dns_queries), 0)
        self.assertEqual(len(self.connections), 1)
        self.assertEqual(connection.host, "relay.example.com")
        self.assertEqual(connection.port, 25)
        self.assertEqual(connection.tos, ["user1@domain-a.com"])
        self.assertEqual(connection.froms, ["sender@example.com"])

    def test_message_direct_host_returns_connection(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            mark=False,
        )

        self.assertNotEqual(connection, None)
        self.assertIsInstance(connection, _MockSMTPConnection)

    def test_message_direct_host_port(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            port=587,
            mark=False,
        )

        self.assertEqual(connection.host, "relay.example.com")
        self.assertEqual(connection.port, 587)

    def test_message_direct_host_multiple_tos(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
                "user3@domain-c.com",
            ],
            "test contents",
            host="relay.example.com",
            mark=False,
        )

        self.assertEqual(len(self.connections), 1)
        self.assertEqual(len(connection.tos), 3)

    def test_message_direct_host_no_dns(self):
        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
            ],
            "test contents",
            host="relay.example.com",
            mark=False,
        )

        self.assertEqual(len(self.dns_queries), 0)

    def test_message_direct_host_binds_close(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            mark=False,
        )

        self.assertIn("close", connection._bindings)
        self.assertIn("exception", connection._bindings)

    def test_message_direct_host_stls(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            stls=True,
            mark=False,
        )

        self.assertEqual(connection.sequence, "stls")

    def test_message_direct_host_no_stls(self):
        client = self._build_client()
        connection = client.message(
            ["sender@example.com"],
            ["user1@domain-a.com"],
            "test contents",
            host="relay.example.com",
            stls=False,
            mark=False,
        )

        self.assertEqual(connection.sequence, "message")

    def test_message_single_domain(self):
        self._build_mock_dns(unique=True)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            ["user1@domain-a.com", "user2@domain-a.com"],
            "test contents",
            mark=False,
        )

        self.assertEqual(len(self.dns_queries), 1)
        self.assertEqual(self.dns_queries[0], "domain-a.com")
        self.assertEqual(len(self.connections), 1)
        self.assertEqual(len(self.connections[0].tos), 2)

    def test_message_separate_different_mx(self):
        self._build_mock_dns(unique=True)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
            ],
            "test contents",
            mark=False,
            sequential=False,
        )

        self.assertEqual(len(self.connections), 2)

        hosts = set(netius.legacy.str(c.host) for c in self.connections)
        self.assertEqual(hosts, {"mx.domain-a.com", "mx.domain-b.com"})

    def test_message_dedup_same_mx(self):
        self._build_mock_dns(unique=False)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
                "user3@domain-a.com",
            ],
            "test contents",
            mark=False,
            mx_dedup=True,
        )

        self.assertEqual(sorted(self.dns_queries), ["domain-a.com", "domain-b.com"])
        self.assertEqual(len(self.connections), 1)

        connection = self.connections[0]
        self.assertEqual(connection.host, "same-mx.example.com")
        self.assertEqual(len(connection.tos), 3)
        self.assertIn("user1@domain-a.com", connection.tos)
        self.assertIn("user2@domain-b.com", connection.tos)
        self.assertIn("user3@domain-a.com", connection.tos)

    def test_message_mx_failure_calls_error(self):
        errors = []

        def resolver(name):
            return _MockDNSResponse(name, fail=True)

        self._dns_resolver = resolver

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            ["user1@bad-domain.com"],
            "test contents",
            mark=False,
            callback_error=lambda c, ctx, e: errors.append(e),
        )

        self.assertEqual(len(self.connections), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("bad-domain.com", str(errors[0]))

    def test_message_mx_failure_calls_callback(self):
        results = []

        def resolver(name):
            return _MockDNSResponse(name, fail=True)

        self._dns_resolver = resolver

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            ["user1@bad-domain.com"],
            "test contents",
            mark=False,
            callback=lambda c, ctx: results.append(ctx),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(len(self.connections), 0)

    def test_message_mx_partial_failure(self):
        errors = []

        def resolver(name):
            if name == "bad-domain.com":
                return _MockDNSResponse(name, fail=True)
            return _MockDNSResponse(name, unique=True)

        self._dns_resolver = resolver

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            ["user1@good-domain.com", "user2@bad-domain.com"],
            "test contents",
            mark=False,
            callback_error=lambda c, ctx, e: errors.append(e),
        )

        self.assertEqual(len(errors), 1)
        self.assertEqual(len(self.connections), 1)
        self.assertIn("user1@good-domain.com", self.connections[0].tos)

    def test_message_mx_dedup_case_insensitive(self):
        def resolver(name):
            if name == "domain-a.com":
                return _MockDNSResponse(name, mx_host=b"MX.GOOGLE.COM.")
            return _MockDNSResponse(name, mx_host=b"mx.google.com")

        self._dns_resolver = resolver

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            ["user1@domain-a.com", "user2@domain-b.com"],
            "test contents",
            mark=False,
            mx_dedup=True,
        )

        self.assertEqual(len(self.connections), 1)
        self.assertEqual(len(self.connections[0].tos), 2)

    def test_message_sequential_one_at_a_time(self):
        self._build_mock_dns(unique=True)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
                "user3@domain-c.com",
            ],
            "test contents",
            mark=False,
            sequential=True,
        )

        self.assertEqual(len(self.connections), 1)

        self.connections[0].trigger("close", self.connections[0])
        self.assertEqual(len(self.connections), 2)

        self.connections[1].trigger("close", self.connections[1])
        self.assertEqual(len(self.connections), 3)

    def test_message_sequential_all_recipients(self):
        self._build_mock_dns(unique=True)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
            ],
            "test contents",
            mark=False,
            sequential=True,
        )

        self.assertEqual(len(self.connections), 1)

        self.connections[0].trigger("close", self.connections[0])
        self.assertEqual(len(self.connections), 2)

        hosts = set(netius.legacy.str(c.host) for c in self.connections)
        self.assertEqual(hosts, {"mx.domain-a.com", "mx.domain-b.com"})

    def test_message_parallel_all_at_once(self):
        self._build_mock_dns(unique=True)

        client = self._build_client()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
                "user3@domain-c.com",
            ],
            "test contents",
            mark=False,
            sequential=False,
        )

        self.assertEqual(len(self.connections), 3)

    def _build_client(self):
        client = netius.clients.SMTPClient()
        self.clients.append(client)
        return client

    def _build_mock_dns(self, unique=False):
        def resolver(name):
            return _MockDNSResponse(name, unique=unique)

        self._dns_resolver = resolver


class _MockDNSResponse(object):

    def __init__(self, domain, unique=False, fail=False, mx_host=None):
        if fail:
            self.answers = []
            return
        if mx_host:
            _mx_host = mx_host
        elif unique:
            _mx_host = b"mx." + domain.encode("utf-8")
        else:
            _mx_host = "same-mx.example.com"
        self.answers = [(domain, "MX", "IN", 300, (10, _mx_host))]


class _MockSMTPConnection(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.froms = None
        self.tos = None
        self.contents = None
        self.mx_host = None
        self.sequence = None
        self.address = (host, port)
        self.start_time = None
        self.greeting = None
        self.queue_response = None
        self.capabilities = []
        self.tls_version = None
        self.tls_cipher = None
        self.transcript = []
        self._bindings = {}

    def set_message_seq(self, ehlo=True):
        self.sequence = "message"

    def set_message_stls_seq(self, ehlo=True):
        self.sequence = "stls"

    def set_smtp(self, froms, tos, contents, username=None, password=None):
        self.froms = froms
        self.tos = tos
        self.contents = contents

    def bind(self, event, callback):
        methods = self._bindings.get(event, [])
        methods.append(callback)
        self._bindings[event] = methods

    def trigger(self, name, *args, **kwargs):
        methods = self._bindings.get(name, [])
        for method in methods:
            method(*args, **kwargs)
