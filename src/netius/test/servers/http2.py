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

import netius.common
import netius.servers
import netius.servers.http2

try:
    import hpack
except ImportError:
    hpack = None


class HTTP2ServerTest(unittest.TestCase):

    def test__has_hpack(self):
        result = netius.servers.HTTP2Server._has_hpack()
        self.assertEqual(result in (True, False), True)

    def test__has_alpn(self):
        result = netius.servers.HTTP2Server._has_alpn()
        self.assertEqual(result in (True, False), True)

    def test__has_npn(self):
        result = netius.servers.HTTP2Server._has_npn()
        self.assertEqual(result in (True, False), True)

    def test_info_dict(self):
        http2_server = netius.servers.HTTP2Server()
        info = http2_server.info_dict()

        self.assertEqual(info["legacy"], True)
        self.assertEqual(info["safe"], False)
        self.assertEqual(info["has_h2"], http2_server._has_h2())
        self.assertEqual(info["has_all_h2"], http2_server._has_all_h2())

    def test_get_protocols(self):
        http2_server = netius.servers.HTTP2Server(legacy=True, safe=True)
        protocols = http2_server.get_protocols()

        self.assertEqual(protocols, ["http/1.1", "http/1.0"])

        http2_server = netius.servers.HTTP2Server(legacy=False, safe=True)
        protocols = http2_server.get_protocols()

        self.assertEqual(protocols, [])

        http2_server = netius.servers.HTTP2Server(legacy=True, safe=False)
        protocols = http2_server.get_protocols()

        if http2_server.has_h2:
            self.assertEqual(protocols, ["h2", "http/1.1", "http/1.0"])
        else:
            self.assertEqual(protocols, ["http/1.1", "http/1.0"])


class HTTP2ConnectionTest(unittest.TestCase):

    def setUp(self):
        self.settings = dict(netius.common.HTTP2_SETTINGS_OPTIMAL)
        self.settings_r = dict(netius.common.HTTP2_SETTINGS)
        self.window = netius.common.HTTP2_WINDOW

    def test_set_settings(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.settings_r = self.settings_r
        connection.parser = netius.common.HTTP2Parser(self, store=True)

        try:
            self.assertEqual(connection.parser._encoder, None)

            connection.set_settings(
                {netius.common.http2.SETTINGS_HEADER_TABLE_SIZE: 8192}
            )
            self.assertEqual(connection.parser._encoder, None)
            self.assertEqual(
                connection.settings_r[netius.common.http2.SETTINGS_HEADER_TABLE_SIZE],
                8192,
            )

            self.assertEqual(connection.parser.encoder.header_table_size, 8192)

            connection.set_settings(
                {netius.common.http2.SETTINGS_HEADER_TABLE_SIZE: 16384}
            )
            self.assertEqual(connection.parser._encoder.header_table_size, 16384)
        finally:
            connection.parser.clear(force=True)
