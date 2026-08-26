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

try:
    import unittest.mock as mock
except ImportError:
    mock = None


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

    def test_parse_an(self):
        name = b"\x03svc\x07example\x03com\x00"
        params = b"\x00\x01\x00\x02h3"
        rdata = struct.pack("!H", 1) + name + params
        record = name + struct.pack("!HHLH", 0x40, 0x01, 300, len(rdata)) + rdata
        index, answer = self.response.parse_an(record, 0)
        # the record size is the only way of knowing where the parameters of
        # the record end, without it they would be reported as empty
        self.assertEqual(index, len(record))
        self.assertEqual(
            answer,
            (b"svc.example.com", "SVCB", "IN", 300, (1, b"svc.example.com", params)),
        )

    def test_parse_a(self):
        rdata = struct.pack("!BBBB", 127, 0, 0, 1)
        index, payload = self.response.parse_a(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, "127.0.0.1")

    def test_parse_aaaa(self):
        rdata = struct.pack("!QQ", 0x20010DB800000000, 0x1)
        index, payload = self.response.parse_aaaa(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, "2001:0db8:0000:0000:0000:0000:0000:0001")

    def test_parse_mx(self):
        rdata = struct.pack("!H", 10) + b"\x04mail\x07example\x03com\x00"
        index, payload = self.response.parse_mx(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, (10, b"mail.example.com"))

    def test_parse_cname(self):
        rdata = b"\x03www\x07example\x03com\x00"
        index, payload = self.response.parse_cname(rdata, 0, size=len(rdata))
        self.assertEqual(index, len(rdata))
        self.assertEqual(payload, b"www.example.com")

    def test_parse_ns(self):
        rdata = b"\x03ns1\x07example\x03com\x00"
        # the NS record is not decoded yet, so no payload is returned for
        # it, the answer is still consumed by the caller
        self.assertEqual(self.response.parse_ns(rdata, 0, size=len(rdata)), None)

    def test_parse_ar(self):
        rdata = struct.pack("!BBBB", 127, 0, 0, 1)
        # the same as the NS record, the additional record is not decoded
        # yet and as such no payload is returned for it
        self.assertEqual(self.response.parse_ar(rdata, 0, size=len(rdata)), None)

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

    def test_parse_svcb_invalid_size(self):
        target = b"\x03svc\x07example\x03com\x00"
        rdata = struct.pack("!H", 1) + target
        # a record size smaller than the data that has already been read would
        # move the index backwards, corrupting the records that follow it
        self.assertRaises(
            netius.ParserError, lambda: self.response.parse_svcb(rdata, 0, size=4)
        )

    def test_parse_svcb_overflow_size(self):
        target = b"\x03svc\x07example\x03com\x00"
        rdata = struct.pack("!H", 1) + target + b"\x00\x01"
        # a record size that goes beyond the end of the message would truncate
        # the parameters and leave the index outside of the buffer
        self.assertRaises(
            netius.ParserError,
            lambda: self.response.parse_svcb(rdata, 0, size=len(rdata) + 1),
        )

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

    def test_parse_caa_invalid_size(self):
        rdata = struct.pack("!BB", 0x00, 200) + b"issue" + b"letsencrypt.org"
        # the length of the tag overflows the advertised record size, so the
        # value would be read from outside of the record
        self.assertRaises(
            netius.ParserError, lambda: self.response.parse_caa(rdata, 0, size=7)
        )

    def test_parse_caa_overflow_size(self):
        tag = b"issue"
        rdata = struct.pack("!BB", 0x80, len(tag)) + tag + b"lets"
        # a record size that goes beyond the end of the message would truncate
        # the value and leave the index outside of the buffer
        self.assertRaises(
            netius.ParserError,
            lambda: self.response.parse_caa(rdata, 0, size=len(rdata) + 1),
        )

    def test_parse_label_pointer(self):
        data = b"\x00\x00\x07example\x03com\x00\x03www\xc0\x02"
        index, label = self.response.parse_label(data, 15)
        # the label is compressed, the last two bytes are a pointer to the
        # name that has been defined at the offset two of the message
        self.assertEqual(index, len(data))
        self.assertEqual(label, b"www.example.com")


class DNSProtocolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.original_ns_file_l = netius.clients.DNSProtocol.ns_file_l

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        netius.clients.DNSProtocol.ns_file_l = self.original_ns_file_l

    def test_ns_system(self):

        class MockProtocol(netius.clients.DNSProtocol):

            ns_conf_l = []
            ns_file_l = []
            ns_google_l = []
            ns_cloudfare_l = []

            @classmethod
            def ns_conf(cls, type="ip4", force=False):
                return cls.ns_conf_l

            @classmethod
            def ns_file(cls, type="ip4", force=False):
                return cls.ns_file_l

            @classmethod
            def ns_google(cls, type="ip4"):
                return cls.ns_google_l

            @classmethod
            def ns_cloudfare(cls, type="ip4"):
                return cls.ns_cloudfare_l

        # the name servers are resolved in a chain, the configuration comes
        # first, then the resolve file and only then the public ones
        self.assertEqual(MockProtocol.ns_system(), None)

        MockProtocol.ns_cloudfare_l = ["1.1.1.1"]

        self.assertEqual(MockProtocol.ns_system(), "1.1.1.1")

        MockProtocol.ns_google_l = ["8.8.8.8"]

        self.assertEqual(MockProtocol.ns_system(), "8.8.8.8")

        MockProtocol.ns_file_l = ["10.0.0.1"]

        self.assertEqual(MockProtocol.ns_system(), "10.0.0.1")

        MockProtocol.ns_conf_l = ["10.0.0.2"]

        self.assertEqual(MockProtocol.ns_system(), "10.0.0.2")

    def test_ns_conf(self):
        self.assertEqual(netius.clients.DNSProtocol.ns_conf(), [])

        with netius.conf_override("NAMESERVERS", "10.0.0.1;10.0.0.2"):
            self.assertEqual(
                netius.clients.DNSProtocol.ns_conf(), ["10.0.0.1", "10.0.0.2"]
            )

            # the type specific configuration takes precedence over the
            # generic one, so that each family may be set apart
            with netius.conf_override("NAMESERVERS_IP4", "10.0.0.3"):
                self.assertEqual(netius.clients.DNSProtocol.ns_conf(), ["10.0.0.3"])

    def test_ns_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        data = b"# comment\nnameserver 10.0.0.1\nnameserver invalid\nnameserver\n"
        file = mock.mock_open(read_data=data)

        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("netius.clients.dns.open", file, create=True):
                ns = netius.clients.DNSProtocol.ns_file(force=True)

        # only the entries that are valid addresses of the requested type
        # are considered, the remaining lines of the file are ignored
        self.assertEqual(ns, ["10.0.0.1"])

    def test_ns_file_missing(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("os.path.exists", return_value=False):
            ns = netius.clients.DNSProtocol.ns_file(force=True)

        # without the resolve file there's no way of knowing the name
        # servers of the system, so an invalid value is returned
        self.assertEqual(ns, None)

    def test_ns_google(self):
        self.assertEqual(netius.clients.DNSProtocol.ns_google(), ["8.8.8.8", "8.8.4.4"])
        self.assertEqual(
            netius.clients.DNSProtocol.ns_google(type="ip6"),
            ["2001:4860:4860::8888", "2001:4860:4860::8844"],
        )
        self.assertEqual(netius.clients.DNSProtocol.ns_google(type="undefined"), [])

    def test_ns_cloudfare(self):
        self.assertEqual(
            netius.clients.DNSProtocol.ns_cloudfare(), ["1.1.1.1", "1.0.0.1"]
        )
        self.assertEqual(
            netius.clients.DNSProtocol.ns_cloudfare(type="ip6"),
            ["2606:4700:4700::1111", "2606:4700:4700::1001"],
        )
        self.assertEqual(netius.clients.DNSProtocol.ns_cloudfare(type="undefined"), [])

    def test_query(self):
        protocol = netius.clients.DNSProtocol()
        transport = _MockTransport()
        protocol._transport = transport

        protocol.query("example.com", type="mx", ns="10.0.0.1")

        self.assertEqual(len(protocol.requests), 1)
        self.assertEqual(len(transport.data), 1)

        data, address = transport.data[0]

        self.assertEqual(address, ("10.0.0.1", 53))

        # the query that has been sent is parsed back so that the name and
        # the type that were requested may be verified on the wire
        query = netius.clients.DNSResponse(data)
        query.parse()

        self.assertEqual(query.get_id(), protocol.requests[0].id)
        self.assertEqual(query.queries, [(b"example.com", "MX", "IN")])

    def test_on_data(self):
        responses = []
        protocol = netius.clients.DNSProtocol()
        request = netius.clients.DNSRequest(
            "example.com", callback=lambda r: responses.append(r)
        )
        protocol.add_request(request)

        protocol.on_data(("10.0.0.1", 53), self._build_answer(request.id))

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].answers[0][0], b"example.com")
        self.assertEqual(responses[0].answers[0][1], "A")
        self.assertEqual(responses[0].answers[0][4], "127.0.0.1")

        # the request is answered only once, meaning that it's no longer
        # pending after the response has been handled
        self.assertEqual(protocol.requests, [])

    def test_on_data_dns_unknown(self):
        responses = []
        protocol = netius.clients.DNSProtocol()
        request = netius.clients.DNSRequest(
            "example.com", callback=lambda r: responses.append(r)
        )
        protocol.add_request(request)

        other = netius.clients.DNSRequest("example.org")
        response = netius.clients.DNSResponse(self._build_answer(other.id))
        response.parse()
        protocol.on_data_dns(("10.0.0.1", 53), response)

        # a response that does not match any of the pending requests is
        # ignored, leaving the pending request untouched
        self.assertEqual(responses, [])
        self.assertEqual(protocol.requests, [request])

    def test_on_data_dns_no_callback(self):
        protocol = netius.clients.DNSProtocol()
        request = netius.clients.DNSRequest("example.com")
        protocol.add_request(request)

        response = netius.clients.DNSResponse(self._build_answer(request.id))
        response.parse()
        protocol.on_data_dns(("10.0.0.1", 53), response)

        # the request is removed from the pending ones even though there's
        # no callback to be called with the response
        self.assertEqual(protocol.requests, [])

    def _build_answer(self, id, name=b"\x07example\x03com\x00"):
        header = struct.pack("!HBBHHHH", id, 0x80, 0x00, 0x1, 0x1, 0x0, 0x0)
        query = name + struct.pack("!HH", 0x01, 0x01)
        rdata = struct.pack("!BBBB", 127, 0, 0, 1)
        answer = name + struct.pack("!HHLH", 0x01, 0x01, 300, len(rdata)) + rdata
        return header + query + answer


class _MockTransport(object):

    def __init__(self):
        self.data = []

    def close(self):
        pass

    def abort(self):
        pass

    def is_closing(self):
        return False

    def sendto(self, data, addr=None):
        self.data.append((data, addr))
        return 0
