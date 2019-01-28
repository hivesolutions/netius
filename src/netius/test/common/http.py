#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2019 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2019 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius.common

SIMPLE_REQUEST = b"GET http://localhost HTTP/1.1\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

CHUNKED_REQUEST = b"GET http://localhost HTTP/1.1\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
Transfer-Encoding: chunked\r\n\
\r\n\
b\r\n\
Hello World\r\n\
0\r\n\
\r\n"

EXTRA_SPACES_REQUEST = b"GET / HTTP/1.1\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT   \r\n\
Server:Test Service/1.0.0  \r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

INVALID_HEADERS_REQUEST = b"GET / HTTP/1.1\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT   \r\n\
Server:Test Service/1.0.0  \r\n\
Content-Length: 11\r\n\
X-Invalid-Header: Ol\xc3\xa1 Mundo\r\n\
\r\n\
Hello World"

INVALID_STATUS_REQUEST = b"GET /\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

class HTTPParserTest(unittest.TestCase):

    def test_simple(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        try:
            parser.parse(SIMPLE_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.method, "get")
            self.assertEqual(parser.version, netius.common.HTTP_11)
            self.assertEqual(parser.path_s, "http://localhost")
            self.assertEqual(parser.content_l, 11)
            self.assertEqual(message, b"Hello World")
            self.assertEqual(headers["Date"], "Wed, 1 Jan 2014 00:00:00 GMT")
            self.assertEqual(headers["Server"], "Test Service/1.0.0")
            self.assertEqual(headers["Content-Length"], "11")
        finally:
            parser.clear()

    def test_chunked(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.method, "get")
            self.assertEqual(parser.version, netius.common.HTTP_11)
            self.assertEqual(parser.path_s, "http://localhost")
            self.assertEqual(parser.transfer_e, "chunked")
            self.assertEqual(message, b"Hello World")
            self.assertEqual(headers["Date"], "Wed, 1 Jan 2014 00:00:00 GMT")
            self.assertEqual(headers["Server"], "Test Service/1.0.0")
            self.assertEqual(headers["Transfer-Encoding"], "chunked")
        finally:
            parser.clear()

    def test_malformed(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        try:
            parser.parse(EXTRA_SPACES_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.method, "get")
            self.assertEqual(parser.version, netius.common.HTTP_11)
            self.assertEqual(parser.path_s, "/")
            self.assertEqual(parser.content_l, 11)
            self.assertEqual(message, b"Hello World")
            self.assertEqual(headers["Date"], "Wed, 1 Jan 2014 00:00:00 GMT")
            self.assertEqual(headers["Server"], "Test Service/1.0.0")
            self.assertEqual(headers["Content-Length"], "11")
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        try:
            parser.parse(INVALID_HEADERS_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.method, "get")
            self.assertEqual(parser.version, netius.common.HTTP_11)
            self.assertEqual(parser.path_s, "/")
            self.assertEqual(parser.content_l, 11)
            self.assertEqual(message, b"Hello World")
            self.assertEqual(headers["Date"], "Wed, 1 Jan 2014 00:00:00 GMT")
            self.assertEqual(headers["Server"], "Test Service/1.0.0")
            self.assertEqual(headers["Content-Length"], "11")
            self.assertEqual(headers["X-Invalid-Header"], "Ol\xc3\xa1 Mundo")
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        try:
            self.assertRaises(
                netius.ParserError,
                lambda: parser.parse(INVALID_STATUS_REQUEST)
            )
        finally:
            parser.clear()

    def test_file(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True,
            file_limit = -1
        )
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            message_b = parser.get_message_b()
            self.assertEqual(message, b"Hello World")
            self.assertNotEqual(parser.message_f, None)
            self.assertNotEqual(parser.message_f.read, None)
            self.assertNotEqual(message_b, None)
            self.assertNotEqual(message_b.read, None)
            self.assertEqual(message_b.read(), b"Hello World")
            self.assertEqual(parser.message, [])
        finally:
            parser.clear()

    def test_no_store(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = False,
            file_limit = -1
        )
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            self.assertEqual(message, b"")
        finally:
            parser.clear()

    def test_clear(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        parser.parse(SIMPLE_REQUEST)
        parser.clear()
        self.assertEqual(parser.type, netius.common.REQUEST)
        self.assertEqual(parser.store, True)
        self.assertEqual(parser.state, netius.common.http.LINE_STATE)
        self.assertEqual(parser.buffer, [])
        self.assertEqual(parser.headers, {})
        self.assertEqual(parser.message, [])
        self.assertEqual(parser.method, None)
        self.assertEqual(parser.version, None)
        self.assertEqual(parser.code, None)
        self.assertEqual(parser.keep_alive, False)
        self.assertEqual(parser.line_s, None)
        self.assertEqual(parser.headers_s, None)
        self.assertEqual(parser.method_s, None)
        self.assertEqual(parser.path_s, None)
        self.assertEqual(parser.version_s, None)
        self.assertEqual(parser.code_s, None)
        self.assertEqual(parser.status_s, None)
        self.assertEqual(parser.connection_s, None)
        self.assertEqual(parser.message_s, None)
        self.assertEqual(parser.message_f, None)
        self.assertEqual(parser.content_l, -1)
        self.assertEqual(parser.message_l, 0)
        self.assertEqual(parser.transfer_e, None)
        self.assertEqual(parser.encodings, None)
        self.assertEqual(parser.chunked, False)
        self.assertEqual(parser.chunk_d, 0)
        self.assertEqual(parser.chunk_l, 0)
        self.assertEqual(parser.chunk_s, 0)
        self.assertEqual(parser.chunk_e, 0)
