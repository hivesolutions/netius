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

import zlib
import unittest

import netius.common
import netius.servers

try:
    import unittest.mock as mock
except ImportError:
    mock = None


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

    def test_send_gzip(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # with no accumulation requested every chunk must be flushed, so that
        # its payload becomes immediately available to the client
        sent = self._send_gzip(0, (b"chunk-1", b"chunk-2", b"chunk-3"))
        self.assertEqual(sent, [7, 7, 7])

        # with the accumulation enabled the payload is withheld until enough
        # of it is pending, improving the ratio of a chunked back-end
        sent = self._send_gzip(16384, (b"chunk-1", b"chunk-2", b"chunk-3"))
        self.assertEqual(sent, [0, 0, 0])

    def test_send_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # an informational or a no content response may never announce a
        # length for a payload that it's not allowed to carry
        headers = self._send_response(code=204, data=b"payload")
        self.assertEqual("content-length" in headers, False)
        headers = self._send_response(code=100, data=b"payload")
        self.assertEqual("content-length" in headers, False)

        # an explicitly provided length must also be dropped for these
        # responses, as their framing is defined by the status code alone
        headers = self._send_response(code=204, headers=dict([("content-length", "7")]))
        self.assertEqual("content-length" in headers, False)

        # the response to a HEAD request must announce the length of the
        # payload of the equivalent GET while carrying no payload at all
        headers = self._send_response(code=200, data=b"payload", method="HEAD")
        self.assertEqual(headers["content-length"], "7")

        # a normal response must announce the exact length of the payload
        # that is going to be sent to the client
        headers = self._send_response(code=200, data=b"payload")
        self.assertEqual(headers["content-length"], "7")

    def test_send_header(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a header value that carries a carriage return or a line feed must
        # be rejected as it would otherwise split the response in two
        self.assertRaises(
            netius.GeneratorError,
            lambda: self._send_header(dict(location="/a\r\nX-Injected: 1")),
        )
        self.assertRaises(
            netius.GeneratorError,
            lambda: self._send_header(dict(location="/a\nX-Injected: 1")),
        )
        self.assertRaises(
            netius.GeneratorError,
            lambda: self._send_header(dict(location="/a\rX-Injected: 1")),
        )

        # a valid set of headers must be serialized using the canonical form
        # of the name and the complete line terminator sequence
        data = self._send_header(dict(location="/a"))
        self.assertEqual("Location: /a\r\n" in data, True)

    def test_resolve_encoding(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the chunked framing may only be used with a client that speaks at
        # least the HTTP 1.1 version, as the previous ones have no support
        # for it and would take the framing as part of the payload
        connection = self._make_connection(encoding=netius.common.CHUNKED_ENCODING)
        connection.resolve_encoding(mock.Mock(version=netius.common.HTTP_10))
        self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)

        connection = self._make_connection(encoding=netius.common.CHUNKED_ENCODING)
        connection.resolve_encoding(mock.Mock(version=netius.common.HTTP_11))
        self.assertEqual(connection.current, netius.common.CHUNKED_ENCODING)

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

    def _send_gzip(self, compress_flush, chunks):
        # sends the provided chunks through the gzip encoding and returns the
        # amount of payload that becomes decodable for each one of them
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        connection.owner.compress_flush = compress_flush
        with mock.patch.object(connection, "send_chunked") as send_chunked:
            for chunk in chunks:
                connection.send_gzip(chunk)
            sent = [call[0][0] for call in send_chunked.call_args_list]
        decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
        return [len(decompressor.decompress(data or b"")) for data in sent]

    def test_on_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the connection must stop being a persistent one once the number of
        # served requests reaches the bound that is defined for the server
        connection = self._make_connection()
        connection.owner.requests_limit = 2
        connection.parser = mock.Mock(keep_alive=True)
        with mock.patch.object(connection.owner, "on_data_http"):
            connection.on_data()
            self.assertEqual(connection.parser.keep_alive, True)
            connection.on_data()
            self.assertEqual(connection.parser.keep_alive, False)

        # a bound set to zero means that no limit is enforced, so that the
        # connection may be kept alive for as long as it's required
        connection = self._make_connection()
        connection.owner.requests_limit = 0
        connection.parser = mock.Mock(keep_alive=True)
        with mock.patch.object(connection.owner, "on_data_http"):
            connection.on_data()
            self.assertEqual(connection.parser.keep_alive, True)

    def _send_response(self, code=200, data=None, headers=None, method="GET"):
        # runs the sending of a response over a connection with no socket,
        # returning the headers that have been used in the operation
        connection = self._make_connection()
        connection.parser = mock.Mock(method=method)
        with mock.patch.object(connection, "send_header") as send_header:
            with mock.patch.object(connection, "send_part"):
                connection.send_response(code=code, data=data, headers=headers)
        return send_header.call_args[1]["headers"]

    def _send_header(self, headers):
        # runs the sending of the headers of a response over a connection with
        # no socket, returning the raw data that would be sent to the client
        connection = self._make_connection()
        connection.parser = mock.Mock(method="GET")
        with mock.patch.object(connection, "send_plain") as send_plain:
            with mock.patch.object(connection.owner, "on_send_http"):
                connection.send_header(headers=headers)
            return send_plain.call_args[0][0]

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
        connection.requests = 0
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
        # overwritten and its payload must not be encoded once again, as the
        # coding announced would no longer describe the complete payload
        connection = self._make_connection(netius.common.GZIP_ENCODING)
        headers = {"Content-Encoding": "br"}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Content-Encoding"], "br")
        self.assertEqual(connection.is_compressed(), False)

        # the explicit identity coding does not describe any transformation,
        # so the payload remains eligible for the compression
        connection = self._make_connection(netius.common.GZIP_ENCODING)
        headers = {"Content-Encoding": "identity"}
        http_server._apply_connection(connection, headers)
        self.assertEqual(connection.is_compressed(), True)

        connection = self._make_connection(netius.common.GZIP_ENCODING)

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

    def test__apply_weak(self):
        http_server = netius.servers.HTTPServer()
        connection = self._make_connection(netius.common.GZIP_ENCODING)

        # a payload that gets encoded by the server is no longer the octet
        # sequence identified by a strong entity tag, so the tag is weakened
        headers = {"Etag": '"abc"'}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Etag"], 'W/"abc"')

        # an entity tag that is already a weak one must be kept untouched
        # as there's nothing left to be weakened on it
        headers = {"Etag": 'W/"abc"'}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Etag"], 'W/"abc"')

        # a payload that is not encoded by the server keeps the strong tag
        # as the octet sequence is exactly the one of the origin
        connection = self._make_connection(netius.common.PLAIN_ENCODING)
        headers = {"Etag": '"abc"'}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Etag"], '"abc"')

        # a payload that already carries a coding is not encoded once again
        # by the server, so the entity tag still describes it
        connection = self._make_connection(netius.common.GZIP_ENCODING)
        headers = {"Etag": '"abc"', "Content-Encoding": "gzip"}
        http_server._apply_connection(connection, headers)
        self.assertEqual(headers["Etag"], '"abc"')

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
