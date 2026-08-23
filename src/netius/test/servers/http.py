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


class HTTPCodecsTest(unittest.TestCase):

    def test_register_codec(self):
        # the codecs that are shipped by default must be registered and
        # carry both the window bits and the encoding ladder value
        self.assertIn("gzip", netius.servers.http.CODECS)
        self.assertIn("deflate", netius.servers.http.CODECS)
        self.assertEqual(
            netius.servers.http.CODECS["gzip"]["encoding"], netius.common.GZIP_ENCODING
        )
        self.assertEqual(
            netius.servers.http.CODECS["deflate"]["encoding"],
            netius.common.DEFLATE_ENCODING,
        )

        # the registered codings must be the ones that the wildcard value
        # of the accept encoding header is expanded into
        self.assertIn("gzip", netius.common.CODINGS)
        self.assertIn("deflate", netius.common.CODINGS)


class HTTPConnectionTest(unittest.TestCase):

    def test_base_encoding(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        self.assertEqual(connection.base_encoding(), netius.common.GZIP_ENCODING)

        # the automatic encoding is a target and not a valid rung of the
        # encoding ladder, so it must resolve into the plain encoding
        connection = self._make_connection(encoding=netius.common.AUTO_ENCODING)
        self.assertEqual(connection.base_encoding(), netius.common.PLAIN_ENCODING)
        self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)

    def test_encoding_w(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)

        # with the dynamic mode disabled the target encoding is the one
        # that is effectively applied to the payload
        connection.owner.dynamic = False
        self.assertEqual(connection.encoding_w(), netius.common.GZIP_ENCODING)

        # with the dynamic mode enabled the encoding is clamped so that no
        # re-encoding of the payload is ever performed
        connection.owner.dynamic = True
        self.assertEqual(connection.encoding_w(), netius.common.CHUNKED_ENCODING)

        # the per response value must take precedence over the server wide
        # one, so that both postures may co-exist in the same server
        connection.dynamic = False
        self.assertEqual(connection.encoding_w(), netius.common.GZIP_ENCODING)

    def test_encoding_name(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        connection.owner.dynamic = False
        self.assertEqual(connection.encoding_name(), "gzip")

        connection.set_deflate()
        self.assertEqual(connection.encoding_name(), "deflate")

        # an explicitly resolved coding name must be the one reported, even
        # for the codings that share the ladder value with another one
        connection.encoding_c = "x-gzip"
        self.assertEqual(connection.encoding_name(), "x-gzip")

        # a payload that is not going to be compressed has no coding name
        connection.set_chunked()
        self.assertEqual(connection.encoding_name(), None)

    def test_set_base(self):
        connection = self._make_connection(encoding=netius.common.AUTO_ENCODING)
        connection.set_gzip()
        connection.encoding_c = "gzip"
        connection.encodings_a = ["gzip"]
        connection.dynamic = False

        connection.set_base()

        # the boundary of a response must take the complete set of the per
        # response encoding values back to their base state
        self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)
        self.assertEqual(connection.encoding_c, None)
        self.assertEqual(connection.encodings_a, None)
        self.assertEqual(connection.dynamic, None)

    def test_is_dynamic(self):
        connection = self._make_connection()

        connection.owner.dynamic = True
        self.assertEqual(connection.is_dynamic(), True)

        connection.owner.dynamic = False
        self.assertEqual(connection.is_dynamic(), False)

        # the per response value must take precedence over the server wide
        # one whenever it has been resolved
        connection.dynamic = True
        self.assertEqual(connection.is_dynamic(), True)

    def _make_connection(self, encoding=netius.common.PLAIN_ENCODING):
        # builds a connection without the underlying socket, replicating the
        # encoding state that the constructor would otherwise initialize
        connection = netius.servers.http.HTTPConnection.__new__(
            netius.servers.http.HTTPConnection
        )
        connection.owner = netius.servers.HTTPServer()
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.gzip_m = dict()
        connection.gzip_l = dict()
        return connection


class HTTPServerTest(unittest.TestCase):

    def test_is_auto(self):
        http_server = netius.servers.HTTPServer()
        self.assertEqual(http_server.is_auto(), False)

        http_server = netius.servers.HTTPServer(encoding="auto")
        self.assertEqual(http_server.is_auto(), True)
        self.assertEqual(http_server.encoding, netius.common.AUTO_ENCODING)

    def test_is_compressible(self):
        http_server = netius.servers.HTTPServer()

        # the media types matched by prefix, by structured syntax suffix
        # and by exact value must all be considered compressible
        self.assertEqual(http_server.is_compressible("text/html"), True)
        self.assertEqual(http_server.is_compressible("text/html; charset=utf-8"), True)
        self.assertEqual(http_server.is_compressible("application/json"), True)
        self.assertEqual(http_server.is_compressible("application/ld+json"), True)
        self.assertEqual(http_server.is_compressible("image/svg+xml"), True)
        self.assertEqual(http_server.is_compressible("APPLICATION/JSON"), True)

        # the media types that are already compressed, the latency sensitive
        # streams and the unknown ones must never be compressed
        self.assertEqual(http_server.is_compressible("image/jpeg"), False)
        self.assertEqual(http_server.is_compressible("video/mp4"), False)
        self.assertEqual(http_server.is_compressible("application/zip"), False)
        self.assertEqual(http_server.is_compressible("text/event-stream"), False)
        self.assertEqual(http_server.is_compressible(None), False)
        self.assertEqual(http_server.is_compressible(""), False)

    def test__apply_connection(self):
        http_server = netius.servers.HTTPServer()
        connection = self._make_connection(netius.common.GZIP_ENCODING)

        headers = {"Content-Length": "1024", "Accept-Ranges": "bytes"}
        http_server._apply_connection(connection, headers)

        # a compressed payload must announce both the coding and the chunked
        # framing, dropping the values that no longer apply to it
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertEqual(headers["Transfer-Encoding"], "chunked")
        self.assertEqual("Content-Length" in headers, False)
        self.assertEqual("Accept-Ranges" in headers, False)

        # a coding that has already been set by the back-end must never be
        # overwritten, as the payload is the one produced by it
        headers = {"Content-Encoding": "br"}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Content-Encoding"], "br")

        # the coding that is announced must be the one applied to the wire
        # and not the (unclamped) target one of the connection
        connection.dynamic = True
        headers = {"Content-Length": "1024"}
        http_server._apply_connection(connection, headers)
        self.assertEqual("Content-Encoding" in headers, False)
        self.assertEqual(headers["Transfer-Encoding"], "chunked")

    def test__apply_connection_vary(self):
        http_server = netius.servers.HTTPServer()
        connection = self._make_connection(netius.common.PLAIN_ENCODING)

        # a response whose representation does not depend on the codings
        # accepted by the client must not announce the vary header
        headers = {}
        http_server._apply_connection(connection, headers)
        self.assertEqual("Vary" in headers, False)

        # a response that was eligible for compression must announce the
        # vary header even in case no compression was performed
        connection.encodings_a = []
        headers = {}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Vary"], "Accept-Encoding")

        # the vary announcement may be disabled through configuration, for
        # the deployments where it's handled by another component
        http_server.compress_vary = False
        headers = {}
        http_server._apply_connection(connection, headers)
        self.assertEqual("Vary" in headers, False)

    def test__apply_vary(self):
        http_server = netius.servers.HTTPServer()

        headers = {}
        http_server._apply_vary(headers, "Accept-Encoding")
        self.assertEqual(headers["Vary"], "Accept-Encoding")

        # the field name must be appended to the value that has already been
        # defined by the back-end instead of replacing it
        headers = {"Vary": "Origin"}
        http_server._apply_vary(headers, "Accept-Encoding")
        self.assertEqual(headers["Vary"], "Origin, Accept-Encoding")

        # a field name that is already part of the value must not be added
        # a second time, independently of the casing used
        headers = {"Vary": "Origin, accept-encoding"}
        http_server._apply_vary(headers, "Accept-Encoding")
        self.assertEqual(headers["Vary"], "Origin, accept-encoding")

        # a repeated header is stored as a sequence and must be normalized
        # into a single value before the field name is appended
        headers = {"Vary": ["Origin", "Cookie"]}
        http_server._apply_vary(headers, "Accept-Encoding")
        self.assertEqual(headers["Vary"], "Origin, Cookie, Accept-Encoding")

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

    def _make_connection(self, encoding):
        # builds a connection without the underlying socket, replicating the
        # encoding state that the constructor would otherwise initialize
        connection = netius.servers.http.HTTPConnection.__new__(
            netius.servers.http.HTTPConnection
        )
        connection.owner = netius.servers.HTTPServer()
        connection.owner.dynamic = False
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        return connection
