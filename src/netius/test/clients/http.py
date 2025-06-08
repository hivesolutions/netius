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

import json
import unittest

import netius.clients


class HTTPClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if netius.conf("NO_NETWORK", False, cast=bool):
            self.skipTest("Network access is disabled")

        self.httpbin = netius.conf("HTTPBIN", "httpbin.org")

    def test_simple(self):
        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/get" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

        result = netius.clients.HTTPClient.method_s(
            "GET", "https://%s/get" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

    def test_timeout(self):
        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/delay/3" % self.httpbin, timeout=1, asynchronous=False
        )
        self.assertEqual(result["error"], "timeout")
        self.assertEqual(result["message"].startswith("Timeout on receive"), True)

        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/delay/1" % self.httpbin, timeout=30, asynchronous=False
        )
        self.assertEqual(result.get("error", None), None)
        self.assertEqual(result.get("message", None), None)
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

    def test_compression(self):
        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/gzip" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/deflate" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertNotEqual(json.loads(result["data"].decode("utf-8")), None)

    def test_headers(self):
        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/headers" % self.httpbin, asynchronous=False
        )
        payload = json.loads(result["data"].decode("utf-8"))
        headers = payload["headers"]
        self.assertEqual(result["code"], 200)
        self.assertEqual(headers["Host"], self.httpbin)
        self.assertEqual(headers["Accept-Encoding"], "gzip, deflate")
        self.assertEqual(headers.get("Content-Length", "0"), "0")
        self.assertNotEqual(headers.get("User-Agent", ""), "")

        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/image/png" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertEqual(result["headers"]["Content-Type"], "image/png")
