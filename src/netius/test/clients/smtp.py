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

        self.original_query_s = netius.clients.DNSClient.query_s
        self.original_connect = netius.clients.SMTPClient.connect
        self.original_ensure_loop = netius.clients.SMTPClient.ensure_loop
        self.connections = []
        self.dns_queries = []

        connections = self.connections

        def mock_connect(self, host, port):
            connection = _MockSMTPConnection(host, port)
            connections.append(connection)
            return connection

        def mock_ensure_loop(self):
            pass

        netius.clients.SMTPClient.connect = mock_connect
        netius.clients.SMTPClient.ensure_loop = mock_ensure_loop

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        netius.clients.DNSClient.query_s = self.original_query_s
        netius.clients.SMTPClient.connect = self.original_connect
        netius.clients.SMTPClient.ensure_loop = self.original_ensure_loop

    def test_message_dedup_same_mx(self):
        self._build_mock_dns(unique=False)

        client = netius.clients.SMTPClient()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
                "user3@domain-a.com",
            ],
            "test contents",
            mark=False,
        )

        self.assertEqual(sorted(self.dns_queries), ["domain-a.com", "domain-b.com"])
        self.assertEqual(len(self.connections), 1)

        connection = self.connections[0]
        self.assertEqual(connection.host, "same-mx.example.com")
        self.assertEqual(len(connection.tos), 3)
        self.assertIn("user1@domain-a.com", connection.tos)
        self.assertIn("user2@domain-b.com", connection.tos)
        self.assertIn("user3@domain-a.com", connection.tos)

    def test_message_separate_different_mx(self):
        self._build_mock_dns(unique=True)

        client = netius.clients.SMTPClient()
        client.message(
            ["sender@example.com"],
            [
                "user1@domain-a.com",
                "user2@domain-b.com",
            ],
            "test contents",
            mark=False,
        )

        self.assertEqual(len(self.connections), 2)

        hosts = set(netius.legacy.str(c.host) for c in self.connections)
        self.assertEqual(hosts, {"mx.domain-a.com", "mx.domain-b.com"})

    def test_message_single_domain(self):
        self._build_mock_dns(unique=True)

        client = netius.clients.SMTPClient()
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

    def test_message_direct_host(self):
        client = netius.clients.SMTPClient()
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
        self.assertEqual(connection.tos, ["user1@domain-a.com"])

    def _build_mock_dns(self, unique=False):
        dns_queries = self.dns_queries

        def mock_query_s(name, type="a", cls_="in", ns=None, callback=None, loop=None):
            dns_queries.append(name)
            response = _MockDNSResponse(name, unique=unique)
            if callback:
                callback(response)

        netius.clients.DNSClient.query_s = staticmethod(mock_query_s)


class _MockDNSResponse(object):

    def __init__(self, domain, unique=False):
        if unique:
            mx_host = b"mx." + domain.encode("utf-8")
        else:
            mx_host = "same-mx.example.com"
        self.answers = [(domain, "MX", "IN", 300, (10, mx_host))]


class _MockSMTPConnection(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.froms = None
        self.tos = None
        self.contents = None
        self.mx_host = None
        self._bindings = {}

    def set_message_seq(self, ehlo=True):
        pass

    def set_message_stls_seq(self, ehlo=True):
        pass

    def set_smtp(self, froms, tos, contents, username=None, password=None):
        self.froms = froms
        self.tos = tos
        self.contents = contents

    def bind(self, event, callback):
        self._bindings[event] = callback
