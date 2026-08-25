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

SIMPLE_REQUEST = b"GET http://localhost HTTP/1.1\r\n\
Host: localhost\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

CHUNKED_REQUEST = b"GET http://localhost HTTP/1.1\r\n\
Host: localhost\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
Transfer-Encoding: chunked\r\n\
\r\n\
b\r\n\
Hello World\r\n\
0\r\n\
\r\n"

EXTRA_SPACES_REQUEST = b"GET / HTTP/1.1\r\n\
Host: localhost\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT   \r\n\
Server:Test Service/1.0.0  \r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

INVALID_HEADERS_REQUEST = b"GET / HTTP/1.1\r\n\
Host: localhost\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT   \r\n\
Server:Test Service/1.0.0  \r\n\
Content-Length: 11\r\n\
X-Invalid-Header: Ol\xc3\xa1 Mundo\r\n\
\r\n\
Hello World"

INVALID_HEADERS_TAB_REQUEST = b"GET / HTTP/1.1\r\n\
Content-Length: 11\r\n\
X-Invalid-Tab-Header:\t withtab\r\n\
\r\n\
Hello World"

INVALID_HEADERS_NEWLINE_REQUEST = b"GET / HTTP/1.1\r\n\
Content-Length: 11\r\n\
X-Invalid-Tab-Header: withnewline\n\r\n\
\r\n\
Hello World"

INVALID_CHUNKED_REQUEST = b"GET / HTTP/1.1\r\n\
Content-Length: 5\r\n\
Transfer-Encoding: chunked\r\n\
\r\n\
2\r\n\
12"

INVALID_TRANSFER_ENCODING_REQUEST = b"GET / HTTP/1.1\r\n\
Content-Length: 11\r\n\
Transfer-Encoding: gzip\r\n\
\r\n\
Hello World"

INVALID_STATUS_REQUEST = b"GET /\r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"

NO_LENGTH_RESPONSE = b"HTTP/1.1 200 OK\r\n\
Date: Wed, 1 Jan 2014 00:00:00 GMT\r\n\
Server: Test Service/1.0.0\r\n\
\r\n\
Hello World"

INTERIM_RESPONSE = b"HTTP/1.1 100 Continue\r\n\
\r\n\
HTTP/1.1 200 OK\r\n\
Content-Length: 2\r\n\
\r\n\
hi"

INTERIM_LENGTH_RESPONSE = b"HTTP/1.1 100 Continue\r\n\
Content-Length: 5\r\n\
\r\n\
HTTP/1.1 200 OK\r\n\
Content-Length: 2\r\n\
\r\n\
hi"

ENCODINGS_REQUEST = b"GET / HTTP/1.1\r\n\
Host: localhost\r\n\
Accept-Encoding: deflate;q=0.5, gzip;q=1.0\r\n\
Content-Length: 11\r\n\
\r\n\
Hello World"


class HTTPEncodingsTest(unittest.TestCase):

    def test_parse_encodings(self):
        self.assertEqual(
            netius.common.parse_encodings("gzip, deflate"), ["gzip", "deflate"]
        )
        self.assertEqual(
            netius.common.parse_encodings(" GZIP , Deflate "), ["gzip", "deflate"]
        )

        # the codings must be ordered by descending quality value, using
        # the order defined by the peer as the tie breaker
        self.assertEqual(
            netius.common.parse_encodings("deflate;q=0.5, gzip;q=1.0"),
            ["gzip", "deflate"],
        )
        self.assertEqual(
            netius.common.parse_encodings("gzip;q=0.5, deflate;q=0.5"),
            ["gzip", "deflate"],
        )

        # the codings explicitly rejected by the peer must not be part of
        # the resulting sequence, the same applies to the identity one
        self.assertEqual(netius.common.parse_encodings("gzip;q=0"), [])
        self.assertEqual(
            netius.common.parse_encodings("gzip;q=0, deflate"), ["deflate"]
        )
        self.assertEqual(netius.common.parse_encodings("identity;q=0, gzip"), ["gzip"])

        # the wildcard coding must be expanded into the codings that may
        # be produced, keeping its position in the preference order
        self.assertEqual(netius.common.parse_encodings("*"), ["gzip", "deflate"])
        self.assertEqual(
            netius.common.parse_encodings("deflate;q=1.0, *;q=0.5"),
            ["deflate", "gzip"],
        )
        self.assertEqual(netius.common.parse_encodings("gzip, *;q=0"), ["gzip"])

        # a coding explicitly rejected by the peer must never be brought
        # back by the wildcard, as the explicit definition takes precedence
        self.assertEqual(netius.common.parse_encodings("gzip;q=0, *"), ["deflate"])
        self.assertEqual(netius.common.parse_encodings("*, gzip;q=0"), ["deflate"])
        self.assertEqual(
            netius.common.parse_encodings("br, gzip;q=0, *"), ["br", "deflate"]
        )

        # an unset or empty header value means that no coding is accepted
        # and a sequence of values is joined as a single one
        self.assertEqual(netius.common.parse_encodings(""), [])
        self.assertEqual(netius.common.parse_encodings("  "), [])
        self.assertEqual(
            netius.common.parse_encodings(["gzip", "deflate"]), ["gzip", "deflate"]
        )

        # an invalid quality value is considered to be a rejection of the
        # coding, avoiding the sending of an unexpected coding, note that
        # only the values between zero and one with at most three decimal
        # places are considered to be valid ones
        self.assertEqual(netius.common.parse_encodings("gzip;q=invalid"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=nan"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=inf"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=2"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=1.1"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=0.0001"), [])
        self.assertEqual(netius.common.parse_encodings("gzip;q=1.000"), ["gzip"])
        self.assertEqual(netius.common.parse_encodings("gzip;q=0.5"), ["gzip"])


class HTTPParserTest(unittest.TestCase):

    def test_simple(self):
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(SIMPLE_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
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
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
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
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(EXTRA_SPACES_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
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

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(INVALID_HEADERS_REQUEST)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
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

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Invalid header value",
                    lambda: parser.parse(INVALID_HEADERS_TAB_REQUEST),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Invalid header value",
                    lambda: parser.parse(INVALID_HEADERS_TAB_REQUEST),
                )
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Invalid header line",
                    lambda: parser.parse(INVALID_HEADERS_NEWLINE_REQUEST),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Invalid header line",
                    lambda: parser.parse(INVALID_HEADERS_NEWLINE_REQUEST),
                )
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Transfer encoding with content length set",
                    lambda: parser.parse(INVALID_CHUNKED_REQUEST),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Transfer encoding with content length set",
                    lambda: parser.parse(INVALID_CHUNKED_REQUEST),
                )
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Invalid transfer encoding",
                    lambda: parser.parse(INVALID_TRANSFER_ENCODING_REQUEST),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Invalid transfer encoding",
                    lambda: parser.parse(INVALID_TRANSFER_ENCODING_REQUEST),
                )
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Invalid status line ",
                    lambda: parser.parse(INVALID_STATUS_REQUEST),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Invalid status line ",
                    lambda: parser.parse(INVALID_STATUS_REQUEST),
                )
        finally:
            parser.clear()

    def test_line(self):
        # the initial line must be terminated by the complete carriage return
        # and line feed sequence, as a bare line feed would allow an extra
        # request to be smuggled through a more permissive intermediary
        self._assert_error(b"GET / HTTP/1.1\nHost: localhost\r\n\r\n")

        # the method token must respect the syntax that is defined for it
        # meaning that only the token characters are allowed in it
        self._assert_error(b"GE T / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self._assert_error(b"G\x00T / HTTP/1.1\r\nHost: localhost\r\n\r\n")

        # neither a control character nor a carriage return may be part of
        # the target of the request, as that would allow the injection of
        # an extra header or even of a complete extra request
        self._assert_error(b"GET /a\rb HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self._assert_error(b"GET /a\x00b HTTP/1.1\r\nHost: localhost\r\n\r\n")

        # the version of the protocol must be provided using the single
        # digit major and minor form, otherwise the line is an invalid one
        self._assert_error(b"GET / HTTP/9\r\nHost: localhost\r\n\r\n")
        self._assert_error(b"GET / HTTP/1.1.1\r\nHost: localhost\r\n\r\n")

        # an unknown but syntactically valid version must be accepted and
        # downgraded to the oldest version of the protocol
        parser = self._parse(b"GET / HTTP/2.0\r\n\r\n")
        self.assertEqual(parser.version, netius.common.HTTP_10)

        # the status code of a response must be a sequence of exactly three
        # digits so that the class of the response may be determined
        self._assert_error(b"HTTP/1.1 XX OK\r\n\r\n", type=netius.common.RESPONSE)
        self._assert_error(b"HTTP/1.1 20 OK\r\n\r\n", type=netius.common.RESPONSE)

        # an initial line that goes beyond the allowed bounds must be
        # rejected with the code that is specific for that situation
        self._assert_error(
            b"GET /" + b"a" * 9000 + b" HTTP/1.1\r\nHost: localhost\r\n\r\n",
            code=414,
        )

    def test_headers(self):
        # a bare carriage return or line feed inside the headers section must
        # be rejected as either of them would allow the injection of an
        # extra header into the message (response splitting)
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: a\nX-Other: b\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: a\rX-Other: b\r\n\r\n"
        )

        # the obsolete line folding of a header value is not supported and
        # must be rejected instead of being silently joined together
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: a\r\n  folded\r\n\r\n"
        )

        # the headers section must respect both the size and the count bounds
        # defined for the parser, otherwise a peer would be able to exhaust
        # the memory that is available to the server
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: "
            + b"a" * 70000
            + b"\r\n\r\n",
            code=431,
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            + b"X-Header: a\r\n" * 200
            + b"\r\n",
            code=431,
        )

        # the bounds of the parser must be configurable ones so that a more
        # permissive or a more restrictive posture may be taken
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: a\r\n\r\n",
            code=431,
            headers_count=1,
        )

        # the count bound is an inclusive one, a message with exactly the
        # allowed number of headers must still be accepted
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nX-Header: a\r\n\r\n",
            headers_count=2,
        )
        self.assertEqual(parser.state, netius.common.http.FINISH_STATE)

    def test_framing(self):
        # a duplicated content length makes the framing of the message an
        # ambiguous one and so it must be rejected even if the values agree
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 5\r\nContent-Length: 5\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 5\r\nContent-Length: 6\r\n\r\n"
        )

        # only a sequence of digits is a valid content length, both the signed
        # and the non numeric values must be rejected as a lenient parsing of
        # them is a well known request smuggling primitive
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: abc\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: -1\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: +5\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: \r\n\r\n"
        )

        # the codings of the transfer encoding are case insensitive ones and
        # may be provided as a list, the chunked one must be the final coding
        # so that the framing of the message may be determined
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: Chunked\r\n\r\n0\r\n\r\n"
        )
        self.assertEqual(parser.chunked, True)
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: identity, chunked\r\n\r\n0\r\n\r\n"
        )
        self.assertEqual(parser.chunked, True)
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked, identity\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n" b"Transfer-Encoding: gzip\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
        )

        # the transfer encoding and the content length must never be defined
        # at the same time, as the framing would then be an ambiguous one
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 6\r\nTransfer-Encoding: chunked\r\n\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Content-Length: 6\r\nTransfer-Encoding: identity\r\n\r\n"
        )

        # a request compliant with HTTP 1.1 must provide one and only one host
        # header, otherwise the target of the request is an ambiguous one
        self._assert_error(b"GET / HTTP/1.1\r\n\r\n")
        self._assert_error(b"GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n")

        # the host header is not a mandatory one for the previous versions of
        # the protocol, as it has only been introduced with HTTP 1.1
        parser = self._parse(b"GET / HTTP/1.0\r\n\r\n")
        self.assertEqual(parser.version, netius.common.HTTP_10)

        # under HTTP 1.1 the connection is a persistent one unless the close
        # token is present in the connection header, note that the header may
        # carry multiple tokens and be defined multiple times
        parser = self._parse(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        self.assertEqual(parser.keep_alive, True)
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive, Upgrade\r\n\r\n"
        )
        self.assertEqual(parser.keep_alive, True)
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade, close\r\n\r\n"
        )
        self.assertEqual(parser.keep_alive, False)
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\n"
            b"Connection: close\r\n\r\n"
        )
        self.assertEqual(parser.keep_alive, False)

        # under the previous versions of the protocol the opposite applies and
        # the connection is only a persistent one if explicitly requested
        parser = self._parse(b"GET / HTTP/1.0\r\n\r\n")
        self.assertEqual(parser.keep_alive, False)
        parser = self._parse(b"GET / HTTP/1.0\r\nConnection: Keep-Alive\r\n\r\n")
        self.assertEqual(parser.keep_alive, True)

    def test_chunked_malformed(self):
        # the size of a chunk must be a sequence of hexadecimal digits, the
        # signed and the prefixed values must be rejected as they would be
        # interpreted in a different way by a more permissive parser
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n-5\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n0x5\r\n"
        )
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\nzz\r\n"
        )

        # the size of a chunk must be terminated by the complete carriage
        # return and line feed sequence, otherwise the last digit of it would
        # be taken as the terminator (the framing would then be an invalid one)
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n12\nAAAAAAAAAAAAAAAAAA\r\n"
        )

        # the extensions of a chunk must still be accepted as they are a
        # valid part of the chunked coding (simply ignored)
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\nb;name=value\r\nHello World\r\n0\r\n\r\n"
        )
        self.assertEqual(parser.get_message(), b"Hello World")

        # the announced size of a chunk must be within the allowed bounds, as
        # a value that no implementation is able to honour would desynchronize
        # the message stream of a more permissive peer
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\nffffffffffffffff\r\n"
        )

        # the bound of the size is a configurable one, a chunk that announces
        # exactly the limit is accepted while a larger one is rejected
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\n10\r\n",
            chunk_limit=16,
        )
        self.assertEqual(parser.chunk_d, 16)
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n11\r\n",
            chunk_limit=16,
        )

    def test_chunked_trailer(self):
        # the trailer section that follows the last chunk must be explicitly
        # consumed, otherwise its fields would be taken as the initial line
        # of an extra (smuggled) request
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\nb\r\nHello World\r\n0\r\nX-Checksum: abc\r\n\r\n"
        )
        self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
        self.assertEqual(parser.get_message(), b"Hello World")

        # a message carrying a trailer section may still be followed by another
        # one under the same connection, meaning that pipelining is preserved
        parser = self._parse(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\nb\r\nHello World\r\n0\r\nX-Checksum: abc\r\n\r\n"
            b"GET /next HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
        self.assertEqual(parser.path_s, "/next")

        # the trailer section may be received in multiple parts, in which case
        # it must be buffered until the end of the section is found
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            data = (
                b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
                b"\r\nb\r\nHello World\r\n0\r\nX-A: 1\r\nX-B: 2\r\n\r\n"
            )
            for index in range(len(data)):
                parser.parse(data[index : index + 1])
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
            self.assertEqual(parser.get_message(), b"Hello World")
        finally:
            parser.clear()

        # a bare carriage return or line feed in the trailer section must be
        # rejected as either of them would allow the injection of an extra field
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\n0\r\nX-A: 1\nX-B: 2\r\n\r\n"
        )

        # the size of the trailer section is bound by the same value that bounds
        # the headers section, avoiding the unbounded buffering of data
        self._assert_error(
            b"GET / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n"
            b"\r\n0\r\nX-Pad: " + b"a" * 70000 + b"\r\n\r\n",
            code=431,
        )

    def test_file(self):
        parser = netius.common.HTTPParser(
            self, type=netius.common.REQUEST, store=True, file_limit=-1
        )
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            message_b = parser.get_message_b()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
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
            self, type=netius.common.REQUEST, store=False, file_limit=-1
        )
        try:
            parser.parse(CHUNKED_REQUEST)
            message = parser.get_message()
            self.assertEqual(message, b"")
        finally:
            parser.clear()

    def test_get_encodings(self):
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(ENCODINGS_REQUEST)

            # the codings must be resolved from the accept encoding header
            # and ordered by descending quality value, the result is cached
            self.assertEqual(parser.get_encodings(), ["gzip", "deflate"])
            self.assertEqual(parser.encodings, ["gzip", "deflate"])
            self.assertEqual(parser.get_encodings(), ["gzip", "deflate"])
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
        try:
            parser.parse(SIMPLE_REQUEST)

            # a request with no accept encoding header must not accept any
            # of the codings, so that no unexpected coding is ever sent
            self.assertEqual(parser.get_encodings(), [])
        finally:
            parser.clear()

    def test_clear(self):
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST, store=True)
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

    def test_no_length_response(self):
        parser = netius.common.HTTPParser(self, type=netius.common.RESPONSE, store=True)
        try:
            parser.parse(NO_LENGTH_RESPONSE)
            message = parser.get_message()
            headers = parser.get_headers()
            self.assertEqual(parser.state, netius.common.http.MESSAGE_STATE)
            self.assertEqual(parser.code, 200)
            self.assertEqual(parser.status, "OK")
            self.assertEqual(parser.version, netius.common.HTTP_11)
            self.assertEqual(parser.content_l, -1)
            self.assertEqual(message, b"Hello World")
            self.assertEqual(headers["Date"], "Wed, 1 Jan 2014 00:00:00 GMT")
            self.assertEqual(headers["Server"], "Test Service/1.0.0")

            parser.parse_closed()
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
        finally:
            parser.clear()

    def test_interim_response(self):
        parser = netius.common.HTTPParser(self, type=netius.common.RESPONSE, store=True)
        seen = []
        parser.bind("on_data", lambda: seen.append((parser.code, parser.get_message())))
        try:
            # an informational response is always terminated by the empty line
            # that follows its headers, so the final response that comes after
            # it must be parsed as a message of its own
            parser.parse(INTERIM_RESPONSE)

            self.assertEqual(seen, [(100, b""), (200, b"hi")])
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
        finally:
            parser.clear()

        parser = netius.common.HTTPParser(self, type=netius.common.RESPONSE, store=True)
        seen = []
        parser.bind("on_data", lambda: seen.append((parser.code, parser.get_message())))
        try:
            # the length announced by a bodyless response describes the entity
            # and never the framing, so it must not be taken as a payload
            parser.parse(INTERIM_LENGTH_RESPONSE)

            self.assertEqual(seen, [(100, b""), (200, b"hi")])
            self.assertEqual(parser.state, netius.common.http.FINISH_STATE)
        finally:
            parser.clear()

    def _parse(self, data, type=netius.common.REQUEST, **kwargs):
        parser = netius.common.HTTPParser(self, type=type, store=True, **kwargs)
        parser.parse(data)
        return parser

    def _assert_error(self, data, code=400, type=netius.common.REQUEST, **kwargs):
        try:
            self._parse(data, type=type, **kwargs)
        except netius.ParserError as error:
            self.assertEqual(error.code, code)
        else:
            self.fail("Parser error not raised for '%s'" % data)
