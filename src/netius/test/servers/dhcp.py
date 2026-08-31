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

import netius.common
import netius.servers

HEADER_FORMAT = "!BBBBIHHIIII2Q64s128s"

RESPONSE_FORMAT = "!BBBBIHHIIII2Q64s128sI"

MAGIC = 0x63825363

MAC = b"\x00\x11\x22\x33\x44\x55"

SIADDR = "11.11.11.2"

GIADDR = "10.10.10.1"


class DHCPRequestTest(unittest.TestCase):

    def test_parse(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        self.assertEqual(request.op, 0x01)
        self.assertEqual(request.xid, 0x12345678)
        self.assertEqual(request.siaddr_s, SIADDR)
        self.assertEqual(request.giaddr_s, GIADDR)
        self.assertEqual(request.magic, struct.pack("!I", MAGIC))

    def test_get_type(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        self.assertEqual(request.get_type(), 0x01)
        self.assertEqual(request.get_type_s(), "discover")

    def test_get_mac(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        self.assertEqual(request.get_mac(), "00:11:22:33:44:55")

    def test_get_mac_leading(self):
        # the hardware address occupies only the first half of its field so
        # the rendering must account for the complete width of it, otherwise
        # an address whose leading octets are zero comes out rotated
        for mac in (
            b"\x00\x00\x00\x00\x00\x01",
            b"\x00\xaa\xbb\xcc\xdd\xee",
            b"\xaa\xbb\xcc\xdd\xee\xff",
        ):
            request = netius.servers.DHCPRequest(build_request(mac=mac))
            request.parse()

            expected = ":".join("%02x" % value for value in bytearray(mac))

            self.assertEqual(request.get_mac(), expected)

    def test_response(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        data = request.response("10.10.10.50", options={netius.common.OFFER_DHCP: None})
        result = struct.unpack(RESPONSE_FORMAT, data[:240])

        # the response is a reply that carries the address that has been
        # offered, while keeping the transaction of the request
        self.assertEqual(result[0], 0x02)
        self.assertEqual(result[4], 0x12345678)
        self.assertEqual(netius.common.addr_to_ip4(result[8]), "10.10.10.50")
        self.assertEqual(result[15], MAGIC)

    def test_response_relay(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        data = request.response("10.10.10.50", options={netius.common.OFFER_DHCP: None})
        result = struct.unpack(RESPONSE_FORMAT, data[:240])

        # the address of the relay agent is the one that has been sent by
        # the request, as it's the way back to the client, and never the
        # address of the server that is answering it
        self.assertEqual(netius.common.addr_to_ip4(result[10]), GIADDR)

    def test_response_chaddr(self):
        request = netius.servers.DHCPRequest(build_request())
        request.parse()

        data = request.response("10.10.10.50", options={netius.common.OFFER_DHCP: None})
        result = struct.unpack(RESPONSE_FORMAT, data[:240])

        # the hardware address is echoed untouched, as it's the value that
        # identifies the client that the response is meant for
        self.assertEqual((result[11], result[12]), request.chaddr)


def build_request(mac=MAC, type=0x01):
    # builds a discover request as it would arrive from the wire, with the
    # relay address set so that the echoing of it may be verified
    chaddr = struct.unpack("!QQ", mac + b"\0" * 10)
    header = struct.pack(
        HEADER_FORMAT,
        0x01,
        0x01,
        0x06,
        0x00,
        0x12345678,
        0x0000,
        0x0000,
        0,
        0,
        netius.common.ip4_to_addr(SIADDR),
        netius.common.ip4_to_addr(GIADDR),
        chaddr[0],
        chaddr[1],
        b"",
        b"",
    )
    options = struct.pack("!BBB", 53, 1, type) + b"\xff"
    return header + struct.pack("!I", MAGIC) + options
