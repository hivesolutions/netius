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

import netius.clients


class DNSClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self.original_build = netius.build_datagram
        self.original_protocol = netius.clients.DNSClient.protocol
        self.closed = []
        self.callbacks = []

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
        self._build_mock_protocol()

        netius.clients.DNSClient.query_s(
            "example.com", callback=lambda r: results.append(r)
        )

        self.assertEqual(len(self.callbacks), 1)
        self.assertEqual(len(self.closed), 0)

        self.callbacks[0]("response")

        self.assertEqual(results, ["response"])
        self.assertEqual(len(self.closed), 1)

    def test_query_s_closes_without_callback(self):
        self._build_mock_protocol()

        netius.clients.DNSClient.query_s("example.com", callback=None)

        self.callbacks[0]("response")

        self.assertEqual(len(self.closed), 1)

    def test_query_s_closes_on_callback_error(self):
        self._build_mock_protocol()

        def bad_callback(response):
            raise RuntimeError("callback error")

        netius.clients.DNSClient.query_s("example.com", callback=bad_callback)

        self.assertRaises(RuntimeError, self.callbacks[0], "response")

        self.assertEqual(len(self.closed), 1)

    def _build_mock_protocol(self):
        closed = self.closed
        callbacks = self.callbacks

        class MockProtocol(netius.clients.DNSProtocol):

            def query(self, name, type="a", cls="in", ns=None, callback=None):
                callbacks.append(callback)

            def close(self):
                closed.append(True)

        netius.clients.DNSClient.protocol = MockProtocol


class DNSResponseParserTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.response = netius.clients.DNSResponse(b"")

    def test_extended_types(self):
        self.assertEqual(netius.clients.dns.DNS_TYPES["SRV"], 0x21)
        self.assertEqual(netius.clients.dns.DNS_TYPES["SVCB"], 0x40)
        self.assertEqual(netius.clients.dns.DNS_TYPES["HTTPS"], 0x41)
        self.assertEqual(netius.clients.dns.DNS_TYPES["CAA"], 0x101)

    def test_parse_srv(self):
        rdata = struct.pack("!HHH", 10, 20, 443)
        rdata += b"\x04_sip\x07example\x03com\x00"
        index, payload = self.response.parse_srv(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, (10, 20, 443, b"_sip.example.com"))

    def test_parse_svcb(self):
        target = b"\x03svc\x07example\x03com\x00"
        params = b"\x00\x01\x00\x02h3"
        rdata = struct.pack("!H", 1) + target + params
        index, payload = self.response.parse_svcb(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, (1, b"svc.example.com", params))

    def test_parse_https_matches_svcb(self):
        target = b"\x03svc\x07example\x03com\x00"
        params = b"\x00\x01\x00\x02h3"
        rdata = struct.pack("!H", 1) + target + params
        _index_svcb, svcb = self.response.parse_svcb(rdata, 0, size=len(rdata))
        _index_https, https = self.response.parse_https(rdata, 0, size=len(rdata))
        self.assertEqual(svcb, https)

    def test_parse_caa(self):
        tag = b"issue"
        value = b"letsencrypt.org"
        rdata = struct.pack("!BB", 0x80, len(tag)) + tag + value
        index, payload = self.response.parse_caa(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, (0x80, b"issue", b"letsencrypt.org"))


class _MockTransport(object):

    def close(self):
        pass

    def abort(self):
        pass

    def is_closing(self):
        return False

    def sendto(self, data, addr=None):
        return 0
