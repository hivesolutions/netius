#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Appier Framework
# Copyright (C) 2008-2014 Hive Solutions Lda.
#
# This file is part of Hive Appier Framework.
#
# Hive Appier Framework is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Appier Framework is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Appier Framework. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
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

class HTTPParserTest(unittest.TestCase):

    def test_simple(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
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

    def test_chunked(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
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

    def test_file(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True,
            file_limit = -1
        )
        parser.parse(CHUNKED_REQUEST)
        message = parser.get_message()
        self.assertEqual(message, b"Hello World")
        self.assertNotEqual(parser.message_f, None)
        self.assertNotEqual(parser.message_f.read, None)

    def test_no_store(self):
        parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = False,
            file_limit = -1
        )
        parser.parse(CHUNKED_REQUEST)
        message = parser.get_message()
        self.assertEqual(message, b"")

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
