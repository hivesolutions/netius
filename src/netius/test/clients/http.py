#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2015 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2015 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import json
import unittest

import netius.clients

class HTTPClientTest(unittest.TestCase):

    def test_simple(self):
        result = netius.clients.HTTPClient.method_s(
            "GET",
            "http://httpbin.org/get",
            async = False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

        result = netius.clients.HTTPClient.method_s(
            "GET",
            "https://httpbin.org/get",
            async = False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

    def test_compression(self):
        result = netius.clients.HTTPClient.method_s(
            "GET",
            "http://httpbin.org/gzip",
            async = False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

        result = netius.clients.HTTPClient.method_s(
            "GET",
            "http://httpbin.org/deflate",
            async = False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

    def test_headers(self):
        result = netius.clients.HTTPClient.method_s(
            "GET",
            "http://httpbin.org/headers",
            async = False
        )
        payload = json.loads(result["data"].decode("utf-8"))
        headers = payload["headers"]
        self.assertEqual(result["code"], 200)
        self.assertEqual(headers["Host"], "httpbin.org")
        self.assertEqual(headers["Content-Length"], "0")
        self.assertEqual(headers["Accept-Encoding"], "gzip, deflate")
        self.assertEqual(headers["User-Agent"].startswith("netius"), True)

        result = netius.clients.HTTPClient.method_s(
            "GET",
            "http://httpbin.org/image/png",
            async = False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertEqual(result["headers"]["Connection"], "keep-alive")
        self.assertEqual(result["headers"]["Content-Type"], "image/png")
