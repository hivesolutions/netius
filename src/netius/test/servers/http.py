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

import netius.servers


class HTTPServerTest(unittest.TestCase):

    def test__headers_upper(self):
        http_server = netius.servers.HTTPServer()
        headers = {"content-type": "plain/text", "content-length": "12"}
        http_server._headers_upper(headers)

        self.assertEqual(
            headers, {"Content-Type": "plain/text", "Content-Length": "12"}
        )

        headers = {"content-Type": "plain/text", "content-LEngtH": "12"}
        http_server._headers_upper(headers)

        self.assertEqual(
            headers, {"Content-Type": "plain/text", "Content-Length": "12"}
        )

    def test__headers_normalize(self):
        http_server = netius.servers.HTTPServer()
        headers = {"Content-Type": ["plain/text"], "Content-Length": ["12"]}
        http_server._headers_normalize(headers)

        self.assertEqual(
            headers, {"Content-Type": "plain/text", "Content-Length": "12"}
        )

        headers = {
            "Content-Type": ["application/json", "charset=utf-8"],
            "Content-Length": "12",
        }
        http_server._headers_normalize(headers)

        self.assertEqual(
            headers,
            {"Content-Type": "application/json;charset=utf-8", "Content-Length": "12"},
        )
