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


class DNSClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.original_build = netius.build_datagram
        self.original_protocol = netius.clients.DNSClient.protocol
        self.closed = []
        self.mock_protocol = None

        def mock_build(protocol_factory, callback=None, **kwargs):
            protocol = protocol_factory()
            transport = _MockTransport()
            protocol._transport = transport
            if callback:
                callback((transport, protocol))
            return None

        netius.build_datagram = mock_build

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        netius.build_datagram = self.original_build
        netius.clients.DNSClient.protocol = self.original_protocol

    def test_query_s_closes_protocol(self):
        results = []
        mock = self._build_mock_protocol()

        netius.clients.DNSClient.query_s(
            "example.com", callback=lambda r: results.append(r)
        )

        self.assertNotEqual(mock._query_callback, None)
        self.assertEqual(len(self.closed), 0)

        mock._query_callback("response")

        self.assertEqual(results, ["response"])
        self.assertEqual(len(self.closed), 1)

    def test_query_s_closes_without_callback(self):
        mock = self._build_mock_protocol()

        netius.clients.DNSClient.query_s("example.com", callback=None)

        mock._query_callback("response")

        self.assertEqual(len(self.closed), 1)

    def test_query_s_closes_on_callback_error(self):
        mock = self._build_mock_protocol()

        def bad_callback(response):
            raise RuntimeError("callback error")

        netius.clients.DNSClient.query_s("example.com", callback=bad_callback)

        self.assertRaises(RuntimeError, mock._query_callback, "response")

        self.assertEqual(len(self.closed), 1)

    def _build_mock_protocol(self):
        closed = self.closed

        class MockProtocol(netius.clients.DNSProtocol):
            _query_callback = None

            def query(self, name, type="a", cls="in", ns=None, callback=None):
                MockProtocol._query_callback = callback

            def close(self):
                closed.append(True)

        netius.clients.DNSClient.protocol = MockProtocol
        return MockProtocol


class _MockTransport(object):

    def close(self):
        pass

    def abort(self):
        pass

    def is_closing(self):
        return False

    def sendto(self, data, addr=None):
        return 0
