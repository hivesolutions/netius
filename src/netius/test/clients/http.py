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
import json
import unittest

import netius.common
import netius.clients

try:
    import unittest.mock as mock
except ImportError:
    mock = None

RAW_MESSAGE = b"Hello World" * 32


class HTTPDeflateTest(unittest.TestCase):

    def test_deflate_wbits(self):
        # a zlib wrapped stream must be detected from the check bits of its
        # header so that the proper container is used in the decompressor
        data = zlib.compress(RAW_MESSAGE)
        self.assertEqual(netius.clients.http.deflate_wbits(data), zlib.MAX_WBITS)

        # a raw deflate stream (the one produced by Netius) has no header
        # and so it must be decoded with the negative window bits
        compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
        data = compressor.compress(RAW_MESSAGE) + compressor.flush()
        self.assertEqual(netius.clients.http.deflate_wbits(data), -zlib.MAX_WBITS)

        # a payload that is too small to carry a header falls back to the
        # zlib wrapped variant (the one defined by the specification)
        self.assertEqual(netius.clients.http.deflate_wbits(b"x"), zlib.MAX_WBITS)


class HTTPProtocolTest(unittest.TestCase):

    def test_raw_data(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )
        protocol.parser = netius.common.HTTPParser(
            protocol, type=netius.common.RESPONSE
        )

        # a payload with no content coding must be returned unchanged, the
        # same applies to a coding that is not implemented by the client
        protocol.parser.headers = {}
        self.assertEqual(protocol.raw_data(RAW_MESSAGE), RAW_MESSAGE)

        protocol.parser.headers = {"content-encoding": "br"}
        self.assertEqual(protocol.raw_data(RAW_MESSAGE), RAW_MESSAGE)
        self.assertEqual(protocol.gzip_c, None)

        # both of the deflate variants must be properly decoded, so that a
        # Netius origin may be decoded by a Netius proxy
        protocol.parser.headers = {"content-encoding": "deflate"}
        protocol.gzip_c = None
        self.assertEqual(protocol.raw_data(zlib.compress(RAW_MESSAGE)), RAW_MESSAGE)

        compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
        data = compressor.compress(RAW_MESSAGE) + compressor.flush()
        protocol.gzip_c = None
        self.assertEqual(protocol.raw_data(data), RAW_MESSAGE)

        # the gzip coding must be decoded taking into account its container
        # and the coding name is matched independently of the casing
        compressor = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        data = compressor.compress(RAW_MESSAGE) + compressor.flush()
        protocol.parser.headers = {"content-encoding": "GZIP"}
        protocol.gzip_c = None
        self.assertEqual(protocol.raw_data(data), RAW_MESSAGE)

    def test_raw_data_partial(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )
        protocol.parser = netius.common.HTTPParser(
            protocol, type=netius.common.RESPONSE
        )

        # both of the deflate variants must be decoded even when the payload
        # arrives in chunks too small to detect the container upfront
        compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
        raw = compressor.compress(RAW_MESSAGE) + compressor.flush()

        for encoding, data in (
            ("deflate", raw),
            ("deflate", zlib.compress(RAW_MESSAGE)),
        ):
            protocol.parser.headers = {"content-encoding": encoding}
            protocol.gzip_c = None
            protocol.gzip_d = None
            message = b""
            for index in range(len(data)):
                message += protocol.raw_data(data[index : index + 1])
            self.assertEqual(message, RAW_MESSAGE)

    def test_decode_zlib_file(self):
        compressor = zlib.compressobj(6, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        data = compressor.compress(RAW_MESSAGE) + compressor.flush()

        input = netius.legacy.BytesIO(data)
        output = netius.legacy.BytesIO()

        netius.clients.HTTPProtocol.decode_zlib_file(input, output, buffer_size=8)

        # the payload is decoded in chunks of the size that was asked for, so
        # that a large one never has to be held whole in memory
        output.seek(0)
        self.assertEqual(output.read(), RAW_MESSAGE)

        # a window that was named takes the place of the default one, which is
        # what tells the two of the codings apart
        compressor = zlib.compressobj(6, zlib.DEFLATED, -zlib.MAX_WBITS)
        data = compressor.compress(RAW_MESSAGE) + compressor.flush()

        input = netius.legacy.BytesIO(data)
        output = netius.legacy.BytesIO()

        netius.clients.HTTPProtocol.decode_deflate_file(input, output)

        output.seek(0)
        self.assertEqual(output.read(), RAW_MESSAGE)

    def test_send_chunked(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol()

        with mock.patch.object(protocol, "send") as send:
            protocol.send_chunked(b"hello")

        # a chunk travels behind the size of it in hexadecimal, both of them
        # closed by the pair that the framing asks for
        self.assertEqual(send.call_args[0][0], b"5\r\nhello\r\n")

        with mock.patch.object(protocol, "send") as send:
            protocol.send_chunked(b"")

        # an empty payload carries no chunk of its own, as a zero sized one
        # would be read as the end of the framing
        self.assertEqual(send.call_args[0][0], b"")

    def test_send_gzip(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol(encoding=netius.clients.http.GZIP_ENCODING)

        sent = []

        with mock.patch.object(
            protocol, "send", lambda data, **kwargs: sent.append(data)
        ):
            protocol.send_gzip(RAW_MESSAGE)
            protocol._flush_gzip()

        # every chunk of the framing carries a part of the compressed payload,
        # which put together is the one that was handed over
        payload = b"".join(sent)
        chunks = self._unchunk(payload)
        self.assertEqual(zlib.decompress(chunks, zlib.MAX_WBITS | 16), RAW_MESSAGE)

        # the compressor is released once it is flushed, so that a request
        # that follows starts one of its own
        self.assertEqual(protocol.gzip, None)

    def test_send_gzip_deflate(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol(encoding=netius.clients.http.DEFLATE_ENCODING)

        sent = []

        with mock.patch.object(
            protocol, "send", lambda data, **kwargs: sent.append(data)
        ):
            protocol.send_gzip(RAW_MESSAGE)
            protocol._flush_gzip()

        # the deflate coding carries no container of its own, which is what
        # the negative window of the compressor stands for
        chunks = self._unchunk(b"".join(sent))
        self.assertEqual(zlib.decompress(chunks, -zlib.MAX_WBITS), RAW_MESSAGE)

    def test_send_gzip_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol()

        with mock.patch.object(protocol, "send") as send:
            protocol.send_gzip(b"")

        # an empty payload never reaches the compressor, as starting one for
        # it would emit a container with nothing in it
        self.assertEqual(send.call_args[0][0], b"")
        self.assertEqual(protocol.gzip, None)

    def test__flush_gzip_unset(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol()

        with mock.patch.object(protocol, "send") as send:
            protocol._flush_gzip()

        # with no compressor to be flushed only the end of the framing is
        # sent, which is what closes the payload
        self.assertEqual(send.call_args[0][0], b"0\r\n\r\n")

    def test__close_gzip(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        protocol = self._make_protocol()

        # a protocol that started no compressor has none to be closed, and
        # asking for it must not raise
        self.assertEqual(protocol._close_gzip(), None)

        protocol.gzip = mock.MagicMock()
        protocol._close_gzip()

        self.assertEqual(protocol.gzip, None)

        # a compressor that fails to be closed is dropped quietly, as the
        # closing of a connection must not be broken by it
        protocol.gzip = mock.MagicMock()
        protocol.gzip.flush.side_effect = ValueError("broken")

        self.assertEqual(protocol._close_gzip(), None)

        # unless the caller asked for the failure, in which case it reaches it
        protocol.gzip = mock.MagicMock()
        protocol.gzip.flush.side_effect = ValueError("broken")

        self.assertRaises(ValueError, protocol._close_gzip, safe=False)

    def test_send_request_parsed_none(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )

        self.assertNotEqual(protocol.parsed, None)

        protocol.parsed = None

        result = protocol.send_request()
        self.assertEqual(result, None)

    def test_send_request_parsed_valid(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/path", asynchronous=True
        )

        self.assertNotEqual(protocol.parsed, None)
        self.assertEqual(protocol.parsed.hostname, "example.com")
        self.assertEqual(protocol.parsed.path, "/path")

    def test_close_c_clears_parsed(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )

        self.assertNotEqual(protocol.parsed, None)

        protocol.close_c()

        self.assertEqual(protocol.parsed, None)

    def test_close_c_send_request_safe(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )

        protocol.close_c()

        self.assertEqual(protocol.parsed, None)

        result = protocol.send_request()
        self.assertEqual(result, None)

    def test_on_data_chunked_trailer(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )
        protocol.parser = netius.common.HTTPParser(
            protocol, type=netius.common.RESPONSE, store=True
        )

        messages = []
        protocol.parser.bind(
            "on_data",
            lambda: messages.append(
                (protocol.parser.code, protocol.parser.get_message())
            ),
        )

        # a chunked response that ends with a trailer section must be parsed
        # as a single message, with the fields of the section discarded, and
        # the connection left ready for the response that follows it, otherwise
        # the reuse of a keep alive connection would be desynchronized
        protocol.on_data(
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n"
            b"\r\nb\r\nHello World\r\n0\r\nX-Checksum: abc\r\n\r\n"
            b"HTTP/1.1 201 Created\r\nContent-Length: 6\r\n\r\nsecond"
        )

        self.assertEqual(messages, [(200, b"Hello World"), (201, b"second")])

    def test_apply_dynamic(self):
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )

        # the codings accepted by the client must be announced in the request
        # so that the server may compress the payload of the response, note
        # that this is verified without a request as an intermediary would
        # otherwise be free to re-write the value announced by the client
        headers = {}
        protocol._apply_dynamic(headers)
        self.assertEqual(headers["accept-encoding"], "gzip, deflate")
        self.assertEqual(headers["host"], "example.com")
        self.assertEqual(headers["connection"], "keep-alive")
        self.assertEqual(headers["content-length"], "0")

        # a coding that has been explicitly defined by the caller must be
        # preserved, as the client is not the authority for it in that case
        headers = {"accept-encoding": "identity"}
        protocol._apply_dynamic(headers)
        self.assertEqual(headers["accept-encoding"], "identity")

        # with no codings defined nothing may be announced, otherwise the
        # client would receive a payload that it's not able to decode
        protocol.encodings = None
        headers = {}
        protocol._apply_dynamic(headers)
        self.assertEqual("accept-encoding" in headers, False)

        # the port of the target is only part of the host header whenever
        # it's not one of the default ones for the scheme in use
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com:8080/", asynchronous=True
        )
        headers = {}
        protocol._apply_dynamic(headers)
        self.assertEqual(headers["host"], "example.com:8080")

    def _make_protocol(self, encoding=None):
        # builds a protocol with a parser of its own, in the state that the
        # framing of a payload requires
        protocol = netius.clients.HTTPProtocol(
            "GET", "http://example.com/", asynchronous=True
        )
        protocol.parser = netius.common.HTTPParser(
            protocol, type=netius.common.RESPONSE
        )
        if not encoding == None:
            protocol.current = encoding
        return protocol

    def _unchunk(self, data):
        # takes the payload out of the framing, so that what was compressed
        # may be verified against what was handed over
        buffer = []
        while data:
            header, data = data.split(b"\r\n", 1)
            size = int(header, 16)
            if not size:
                break
            buffer.append(data[:size])
            data = data[size + 2 :]
        return b"".join(buffer)


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
        self.assertEqual(headers.get("Content-Length", "0"), "0")
        self.assertNotEqual(headers.get("User-Agent", ""), "")

        result = netius.clients.HTTPClient.method_s(
            "GET", "http://%s/image/png" % self.httpbin, asynchronous=False
        )
        self.assertEqual(result["code"], 200)
        self.assertNotEqual(len(result["data"]), 0)
        self.assertEqual(result["headers"]["Content-Type"], "image/png")
