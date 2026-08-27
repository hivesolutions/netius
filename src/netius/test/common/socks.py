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

from netius.common import socks

SOCKS4_REQUEST = (
    struct.pack("!B", 4) + struct.pack("!BHI", 1, 80, 0x7F000001) + b"netius" + b"\0"
)

SOCKS4A_REQUEST = (
    struct.pack("!B", 4)
    + struct.pack("!BHI", 1, 80, 0x00000001)
    + b"netius"
    + b"\0"
    + b"example.com"
    + b"\0"
)

SOCKS5_GREETING = struct.pack("!B", 5) + struct.pack("!BB", 1, 0)

SOCKS5_IPV4 = (
    SOCKS5_GREETING
    + struct.pack("!BBBB", 5, 1, 0, socks.IPV4)
    + struct.pack("!I", 0x7F000001)
    + struct.pack("!H", 8080)
)

SOCKS5_IPV6 = (
    SOCKS5_GREETING
    + struct.pack("!BBBB", 5, 1, 0, socks.IPV6)
    + b"\x20\x01"
    + b"\0" * 13
    + b"\x01"
    + struct.pack("!H", 443)
)

SOCKS5_DOMAIN = (
    SOCKS5_GREETING
    + struct.pack("!BBBB", 5, 1, 0, socks.DOMAIN)
    + struct.pack("!B", 11)
    + b"example.com"
    + struct.pack("!H", 80)
)


class SOCKSParserTest(unittest.TestCase):

    def test_build(self):
        parser = socks.SOCKSParser(self)
        try:
            # the states are ordered according to their integer definition
            # so that the parsing may index them directly by the state
            self.assertEqual(len(parser.states), 10)
            self.assertEqual(parser.state_l, 10)
            self.assertEqual(parser.states[0], parser._parse_version)
            self.assertEqual(parser.states[-1], parser._parse_port)
        finally:
            parser.destroy()

    def test_destroy(self):
        parser = socks.SOCKSParser(self)

        parser.destroy()

        # the destruction releases the states, as no further usage of the
        # parser is expected once it has been destroyed
        self.assertEqual(parser.states, ())
        self.assertEqual(parser.state_l, 0)

    def test_reset(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_IPV4)

            self.assertEqual(parser.state, socks.FINISH_STATE)

            parser.reset()

            self.assertEqual(parser.state, socks.VERSION_STATE)
            self.assertEqual(parser.version, None)
            self.assertEqual(parser.command, None)
            self.assertEqual(parser.port, None)
            self.assertEqual(parser.address, None)
            self.assertEqual(parser.buffer, [])
        finally:
            parser.destroy()

    def test_clear(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.version = 5

            # a parser that is at the initial state has nothing to be
            # cleared, so the operation is ignored unless it's forced
            parser.clear()

            self.assertEqual(parser.version, 5)

            parser.clear(force=True)

            self.assertEqual(parser.version, None)
        finally:
            parser.destroy()

    def test_parse_socks4(self):
        parser = socks.SOCKSParser(self)
        try:
            count = parser.parse(SOCKS4_REQUEST)

            self.assertEqual(count, len(SOCKS4_REQUEST))
            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.version, 4)
            self.assertEqual(parser.command, 1)
            self.assertEqual(parser.port, 80)
            self.assertEqual(parser.address_s, "127.0.0.1")
            self.assertEqual(parser.user_id, "netius")
            self.assertEqual(parser.is_extended, False)
            self.assertEqual(parser.domain, None)
        finally:
            parser.destroy()

    def test_parse_socks4a(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS4A_REQUEST)

            # an address under the 0.0.0.x range marks the request as an
            # extended one, meaning that a domain follows the user identifier
            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.is_extended, True)
            self.assertEqual(parser.user_id, "netius")
            self.assertEqual(parser.domain, "example.com")
            self.assertEqual(parser.get_host(), "example.com")
        finally:
            parser.destroy()

    def test_parse_socks5_ipv4(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_IPV4)

            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.version, 5)
            self.assertEqual(parser.auth_count, 1)
            self.assertEqual(parser.auth_methods, (0,))
            self.assertEqual(parser.type, socks.IPV4)
            self.assertEqual(parser.size, 4)
            self.assertEqual(parser.address_s, "127.0.0.1")
            self.assertEqual(parser.port, 8080)
        finally:
            parser.destroy()

    def test_parse_socks5_ipv6(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_IPV6)

            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.type, socks.IPV6)
            self.assertEqual(parser.size, 16)
            self.assertEqual(parser.address, (0x2001 << 112) + 1)
            self.assertEqual(parser.port, 443)
        finally:
            parser.destroy()

    def test_parse_socks5_domain(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_DOMAIN)

            # the size of a domain based address is read from the request
            # itself, instead of being implied by the type of the address
            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.type, socks.DOMAIN)
            self.assertEqual(parser.size, 11)
            self.assertEqual(parser.address_s, "example.com")
            self.assertEqual(parser.port, 80)
        finally:
            parser.destroy()

    def test_parse_partial(self):
        parser = socks.SOCKSParser(self)
        try:
            # the request is fed one byte at a time, so that every state has
            # to hold the partial data until enough of it has been gathered
            for index in range(len(SOCKS5_DOMAIN)):
                parser.parse(SOCKS5_DOMAIN[index : index + 1])

            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.address_s, "example.com")
            self.assertEqual(parser.port, 80)
        finally:
            parser.destroy()

    def test_parse_split(self):
        # the transport is free to break a request at any point, including
        # in the middle of one of the fields of a fixed size
        for index in range(1, len(SOCKS5_IPV6)):
            parser = socks.SOCKSParser(self)
            try:
                parser.parse(SOCKS5_IPV6[:index])
                parser.parse(SOCKS5_IPV6[index:])

                self.assertEqual(parser.state, socks.FINISH_STATE)
                self.assertEqual(parser.address, (0x2001 << 112) + 1)
                self.assertEqual(parser.port, 443)
            finally:
                parser.destroy()

    def test_parse_restart(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_IPV4)

            self.assertEqual(parser.state, socks.FINISH_STATE)

            # a parser that has finished restarts on the next parse, so that
            # a new request may be handled by the very same instance
            parser.parse(SOCKS4_REQUEST)

            self.assertEqual(parser.state, socks.FINISH_STATE)
            self.assertEqual(parser.version, 4)
            self.assertEqual(parser.user_id, "netius")
        finally:
            parser.destroy()

    def test_parse_invalid(self):
        parser = socks.SOCKSParser(self)
        try:
            # a version that is neither the fourth nor the fifth one has no
            # state to move to, so it must be rejected instead of ignored
            self.assertRaises(netius.ParserError, parser.parse, struct.pack("!B", 6))
        finally:
            parser.destroy()

    def test_get_host(self):
        parser = socks.SOCKSParser(self)
        try:
            parser.parse(SOCKS5_IPV4)

            self.assertEqual(parser.get_host(), "127.0.0.1")

            # the domain takes precedence over the address, as it's the name
            # that the client has asked to be connected to
            parser.domain = "example.com"

            self.assertEqual(parser.get_host(), "example.com")
        finally:
            parser.destroy()

    def test_get_address(self):
        parser = socks.SOCKSParser(self)
        try:
            # the address is rebuilt as the very same sequence of bytes that
            # has been parsed out of the request, for every kind of address
            parser.parse(SOCKS5_IPV4)

            self.assertEqual(parser.get_address(), struct.pack("!I", 0x7F000001))

            parser.parse(SOCKS5_IPV6)

            self.assertEqual(parser.get_address(), b"\x20\x01" + b"\0" * 13 + b"\x01")

            parser.parse(SOCKS5_DOMAIN)

            self.assertEqual(
                parser.get_address(), struct.pack("!B", 11) + b"example.com"
            )
        finally:
            parser.destroy()

    def test_get_address_unset(self):
        parser = socks.SOCKSParser(self)
        try:
            # a request that has not been parsed yet has no kind of address
            # associated with it, so there's nothing to be rebuilt
            self.assertEqual(parser.get_address(), None)
        finally:
            parser.destroy()
