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

try:
    import unittest.mock as mock
except ImportError:
    mock = None

RESPONSE = (
    b"HTTP/1.1 200 OK\r\n"
    b"CACHE-CONTROL: max-age=1800\r\n"
    b"ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
    b"USN: uuid:device::urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
    b"\r\n"
)
""" The raw contents of the answer that a device sends back
to a discovery, as the specification defines it """


class SSDPProtocolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.protocol = _MockSSDPProtocol()
        self.headers = []
        self.protocol.bind("headers", self._on_headers)

    def test_on_data(self):
        self.protocol.on_data(("192.168.1.1", 1900), RESPONSE)

        # the answer of a device is read as an HTTP response, the headers
        # of it reaching the ones that are bound to the event
        self.assertEqual(len(self.headers), 1)
        self.assertEqual(
            self.headers[0]["St"], "urn:schemas-upnp-org:device:InternetGatewayDevice:1"
        )
        self.assertEqual(self.headers[0]["Cache-Control"], "max-age=1800")
        self.assertEqual(
            self.headers[0]["Usn"],
            "uuid:device::urn:schemas-upnp-org:device:InternetGatewayDevice:1",
        )

    def test_on_data_partial(self):
        self.protocol.on_data(("192.168.1.1", 1900), b"HTTP/1.1 200 OK\r\n")

        # an answer that never completes carries no headers of its own,
        # so nothing is handed to the ones that wait for them
        self.assertEqual(self.headers, [])

    def test_discover(self):
        self.protocol.discover("urn:schemas-upnp-org:device:InternetGatewayDevice:1")

        data, address = self.protocol.sent[0]

        # the discovery is a search of the protocol towards the address
        # that the specification reserves for it
        self.assertEqual(address, ("239.255.255.250", 1900))
        self.assertEqual(data.startswith("M-SEARCH * HTTP/1.1\r\n"), True)
        self.assertEqual('Man: "ssdp:discover"\r\n' in data, True)
        self.assertEqual(
            "St: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n" in data, True
        )
        self.assertEqual("Mx: 3\r\n" in data, True)
        self.assertEqual("Host: 239.255.255.250:1900\r\n" in data, True)
        self.assertEqual(data.endswith("\r\n\r\n"), True)

    def test_method(self):
        self.protocol.method(
            "NOTIFY",
            "urn:target",
            "ssdp:alive",
            mx=5,
            path="/control",
            headers=dict(NTS="ssdp:alive"),
            host="192.168.1.1",
            port=1901,
            version="HTTP/1.0",
        )

        data, address = self.protocol.sent[0]

        # every one of the values that the caller names takes the place of
        # the default of it, the headers being cased as the protocol asks
        self.assertEqual(address, ("192.168.1.1", 1901))
        self.assertEqual(data.startswith("NOTIFY /control HTTP/1.0\r\n"), True)
        self.assertEqual("Mx: 5\r\n" in data, True)
        self.assertEqual("Nts: ssdp:alive\r\n" in data, True)
        self.assertEqual("Host: 192.168.1.1:1901\r\n" in data, True)

    def test_method_list(self):
        self.protocol.method(
            "M-SEARCH",
            "urn:target",
            "ssdp:discover",
            headers=dict(Ext=["first", "second"]),
        )

        data, _address = self.protocol.sent[0]

        # a header that carries more than one value is written once for
        # each of them, instead of the sequence being written as it is
        self.assertEqual("Ext: first\r\n" in data, True)
        self.assertEqual("Ext: second\r\n" in data, True)

    def test_method_data(self):
        self.protocol.method("M-SEARCH", "urn:target", "ssdp:discover", data=b"payload")

        # the payload travels in a datagram of its own, the one that comes
        # before it carrying only the head of the message
        self.assertEqual(len(self.protocol.sent), 2)
        self.assertEqual(self.protocol.sent[1][0], b"payload")

    def _on_headers(self, protocol, parser, headers):
        self.headers.append(headers)


class SSDPClientTest(unittest.TestCase):

    def test_discover_s(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("netius.build_datagram") as build_datagram:
            loop, protocol = netius.clients.SSDPClient.discover_s(
                "urn:schemas-upnp-org:device:InternetGatewayDevice:1"
            )

        # the discovery answers with the loop that is going to carry it
        # and with the protocol that speaks for it
        self.assertEqual(loop, build_datagram.return_value)
        self.assertEqual(isinstance(protocol, netius.clients.SSDPProtocol), True)

        # the endpoint is built towards the address that the specification
        # reserves for the discovery of a device
        self.assertEqual(
            build_datagram.call_args[1]["remote_addr"], ("239.255.255.250", 1900)
        )

    def test_method_s(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("netius.build_datagram") as build_datagram:
            loop, protocol = netius.clients.SSDPClient.method_s(
                "NOTIFY", "urn:target", "ssdp:alive", host="127.0.0.1", port=1901
            )

        self.assertEqual(loop, build_datagram.return_value)
        self.assertEqual(isinstance(protocol, netius.clients.SSDPProtocol), True)

        # the endpoint is built towards the contact that the caller named,
        # instead of the one that a discovery would use
        self.assertEqual(
            build_datagram.call_args[1]["remote_addr"], ("127.0.0.1", 1901)
        )

    def test_method_s_connect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = _MockSSDPProtocol()

        with mock.patch.object(
            netius.clients.SSDPClient, "protocol", lambda: protocol
        ), mock.patch("netius.build_datagram") as build_datagram:
            netius.clients.SSDPClient.method_s(
                "M-SEARCH", "urn:target", "ssdp:discover", host="127.0.0.1", port=1901
            )

        callback = build_datagram.call_args[1]["callback"]
        callback((None, protocol))

        data, address = protocol.sent[0]

        # the message is only sent once the endpoint of the datagram is
        # in place, which is what the callback of the building stands for
        self.assertEqual(address, ("127.0.0.1", 1901))
        self.assertEqual(data.startswith("M-SEARCH * HTTP/1.1\r\n"), True)


class _MockSSDPProtocol(netius.clients.SSDPProtocol):
    """
    Stand in for the protocol that keeps the datagrams that
    it sends instead of handing them to a transport.
    """

    def __init__(self, *args, **kwargs):
        netius.clients.SSDPProtocol.__init__(self, *args, **kwargs)
        self.sent = []

    def send(self, data, address, callback=None):
        self.sent.append((data, address))
