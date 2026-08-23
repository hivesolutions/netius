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

import struct
import unittest

import netius.common
import netius.servers.http2

try:
    import hpack
except ImportError:
    hpack = None


def _pack_frame(type, flags=0x00, stream=0x00, payload=b""):
    size = len(payload)
    size_h = size >> 16
    size_l = size & 0xFFFF
    header = struct.pack("!BHBBI", size_h, size_l, type, flags, stream)
    return header + payload


SETTINGS_FRAME = _pack_frame(
    netius.common.SETTINGS,
    payload=struct.pack("!HI", netius.common.http2.SETTINGS_MAX_CONCURRENT_STREAMS, 64)
    + struct.pack("!HI", netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE, 131072),
)

SETTINGS_ACK_FRAME = _pack_frame(netius.common.SETTINGS, flags=0x01)

PING_FRAME = _pack_frame(
    netius.common.PING, payload=b"\x01\x02\x03\x04\x05\x06\x07\x08"
)

GOAWAY_FRAME = _pack_frame(
    netius.common.GOAWAY, payload=struct.pack("!II", 3, 0x00) + b"bye"
)

WINDOW_UPDATE_FRAME = _pack_frame(
    netius.common.WINDOW_UPDATE, payload=struct.pack("!I", 4096)
)


class HTTP2ParserTest(unittest.TestCase):

    def setUp(self):
        self.settings = dict(netius.common.HTTP2_SETTINGS_OPTIMAL)
        self.settings_r = dict(netius.common.HTTP2_SETTINGS)
        self.window = netius.common.HTTP2_WINDOW

    def test_assert_header(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            parser.length = (
                self.settings[netius.common.http2.SETTINGS_MAX_FRAME_SIZE] + 1
            )
            parser.stream = 0x01
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE",
                    parser.assert_header,
                )
            else:
                self.assertRaises(netius.ParserError, parser.assert_header)
        finally:
            parser.clear(force=True)

    def test_assert_settings(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            parser.stream = 0x01
            parser.length = 0
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Stream must be set to 0x00 for SETTINGS",
                    lambda: parser.assert_settings([], False),
                )
            else:
                self.assertRaises(
                    netius.ParserError, lambda: parser.assert_settings([], False)
                )

            parser.stream = 0x00
            parser.length = 4
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS with ACK must be zero length",
                    lambda: parser.assert_settings([], True),
                )
            else:
                self.assertRaises(
                    netius.ParserError, lambda: parser.assert_settings([], True)
                )

            parser.stream = 0x00
            parser.length = 5
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Size of SETTINGS frame must be a multiple of 6",
                    lambda: parser.assert_settings([], False),
                )
            else:
                self.assertRaises(
                    netius.ParserError, lambda: parser.assert_settings([], False)
                )

            parser.stream = 0x00
            parser.length = 6
            settings = [(netius.common.http2.SETTINGS_ENABLE_PUSH, 2)]
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS_ENABLE_PUSH different from 0 or 1",
                    lambda: parser.assert_settings(settings, False),
                )
            else:
                self.assertRaises(
                    netius.ParserError,
                    lambda: parser.assert_settings(settings, False),
                )

            parser.stream = 0x00
            parser.length = 6
            settings = [(netius.common.http2.SETTINGS_MAX_FRAME_SIZE, 1024)]
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE too small",
                    lambda: parser.assert_settings(settings, False),
                )
            else:
                self.assertRaises(
                    netius.ParserError,
                    lambda: parser.assert_settings(settings, False),
                )

            parser.stream = 0x00
            parser.length = 6
            settings = [(netius.common.http2.SETTINGS_MAX_FRAME_SIZE, 16777216)]
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE too large",
                    lambda: parser.assert_settings(settings, False),
                )
            else:
                self.assertRaises(
                    netius.ParserError,
                    lambda: parser.assert_settings(settings, False),
                )
        finally:
            parser.clear(force=True)

    def test_assert_push_promise(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "PUSH_PROMISE not allowed for server",
                    lambda: parser.assert_push_promise(0x02),
                )
            else:
                self.assertRaises(
                    netius.ParserError, lambda: parser.assert_push_promise(0x02)
                )
        finally:
            parser.clear(force=True)

    def test_assert_ping(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            parser.stream = 0x01
            parser.length = 8
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Stream must be set to 0x00 for PING",
                    parser.assert_ping,
                )
            else:
                self.assertRaises(netius.ParserError, parser.assert_ping)

            parser.stream = 0x00
            parser.length = 4
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Size of PING frame must be 8",
                    parser.assert_ping,
                )
            else:
                self.assertRaises(netius.ParserError, parser.assert_ping)

            parser.stream = 0x00
            parser.length = 8
            parser.assert_ping()
        finally:
            parser.clear(force=True)

    def test_assert_goaway(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            parser.stream = 0x01
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Stream must be set to 0x00 for GOAWAY",
                    parser.assert_goaway,
                )
            else:
                self.assertRaises(netius.ParserError, parser.assert_goaway)

            parser.stream = 0x00
            parser.assert_goaway()
        finally:
            parser.clear(force=True)

    def test_assert_window_update(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "WINDOW_UPDATE increment must not be zero",
                    lambda: parser.assert_window_update(None, 0),
                )
            else:
                self.assertRaises(
                    netius.ParserError,
                    lambda: parser.assert_window_update(None, 0),
                )

            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Window value for the connection too large",
                    lambda: parser.assert_window_update(None, 2147483647),
                )
            else:
                self.assertRaises(
                    netius.ParserError,
                    lambda: parser.assert_window_update(None, 2147483647),
                )

            parser.assert_window_update(None, 4096)
        finally:
            parser.clear(force=True)

    def test_parse_settings(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            parser.bind(
                "on_settings", lambda settings, ack: events.append((settings, ack))
            )
            count = parser.parse(SETTINGS_FRAME)
            self.assertEqual(count, len(SETTINGS_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.SETTINGS)
            self.assertEqual(parser.stream, 0x00)
            self.assertEqual(len(events), 1)
            settings, ack = events[0]
            self.assertEqual(ack, 0x00)
            self.assertEqual(
                dict(settings),
                {
                    netius.common.http2.SETTINGS_MAX_CONCURRENT_STREAMS: 64,
                    netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE: 131072,
                },
            )
        finally:
            parser.clear(force=True)

    def test_parse_settings_ack(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            parser.bind(
                "on_settings", lambda settings, ack: events.append((settings, ack))
            )
            count = parser.parse(SETTINGS_ACK_FRAME)
            self.assertEqual(count, len(SETTINGS_ACK_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.SETTINGS)
            self.assertEqual(parser.length, 0)
            self.assertEqual(len(events), 1)
            settings, ack = events[0]
            self.assertEqual(settings, [])
            self.assertEqual(ack, 0x01)
        finally:
            parser.clear(force=True)

    def test_parse_settings_ack_then_ping(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            payloads = []
            parser.bind(
                "on_settings", lambda settings, ack: events.append(("settings", ack))
            )
            parser.bind("on_ping", lambda data, ack: events.append(("ping", ack)))
            parser.bind("on_payload", lambda: payloads.append(parser.type))
            count = parser.parse(SETTINGS_ACK_FRAME + PING_FRAME)
            self.assertEqual(count, len(SETTINGS_ACK_FRAME) + len(PING_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.PING)
            self.assertEqual(parser.last_type, netius.common.SETTINGS)
            self.assertEqual(parser.last_stream, 0x00)
            self.assertEqual(events, [("settings", 0x01), ("ping", 0x00)])
            self.assertEqual(payloads, [netius.common.SETTINGS, netius.common.PING])
        finally:
            parser.clear(force=True)

    def test_parse_ping(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            parser.bind("on_ping", lambda data, ack: events.append((data, ack)))
            count = parser.parse(PING_FRAME)
            self.assertEqual(count, len(PING_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.PING)
            self.assertEqual(len(events), 1)
            data, ack = events[0]
            self.assertEqual(data, b"\x01\x02\x03\x04\x05\x06\x07\x08")
            self.assertEqual(ack, 0x00)
        finally:
            parser.clear(force=True)

    def test_parse_goaway(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            parser.bind(
                "on_goaway",
                lambda last_stream, error_code, extra: events.append(
                    (last_stream, error_code, extra)
                ),
            )
            count = parser.parse(GOAWAY_FRAME)
            self.assertEqual(count, len(GOAWAY_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.GOAWAY)
            self.assertEqual(len(events), 1)
            last_stream, error_code, extra = events[0]
            self.assertEqual(last_stream, 3)
            self.assertEqual(error_code, 0x00)
            self.assertEqual(extra, b"bye")
        finally:
            parser.clear(force=True)

    def test_parse_window_update(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            events = []
            parser.bind(
                "on_window_update",
                lambda stream, increment: events.append((stream, increment)),
            )
            count = parser.parse(WINDOW_UPDATE_FRAME)
            self.assertEqual(count, len(WINDOW_UPDATE_FRAME))
            self.assertEqual(parser.state, netius.common.http2.FINISH_STATE)
            self.assertEqual(parser.type, netius.common.WINDOW_UPDATE)
            self.assertEqual(len(events), 1)
            stream, increment = events[0]
            self.assertEqual(stream, None)
            self.assertEqual(increment, 4096)
        finally:
            parser.clear(force=True)

    def test_encoder(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")
        self.settings_r[netius.common.http2.SETTINGS_HEADER_TABLE_SIZE] = 8192
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            self.assertEqual(parser.encoder.header_table_size, 8192)
        finally:
            parser.clear(force=True)

    def test_decoder(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")
        self.settings[netius.common.http2.SETTINGS_HEADER_TABLE_SIZE] = 16384
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            self.assertEqual(parser.decoder.max_allowed_table_size, 16384)
        finally:
            parser.clear(force=True)


class HTTP2StreamTest(unittest.TestCase):

    def test_resolve_encoding(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        parser = connection.parser
        try:
            stream_1 = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)
            stream_3 = netius.common.http2.HTTP2Stream(identifier=3, owner=parser)
            stream_1.headers = {"accept-encoding": "gzip"}
            stream_3.headers = {}

            stream_1.resolve_encoding(stream_1)
            stream_3.resolve_encoding(stream_3)

            # each of the multiplexed streams must reach its own decision,
            # the negotiation of one of them must never revoke the one that
            # has already been reached by the other
            self.assertEqual(stream_1.current, netius.common.GZIP_ENCODING)
            self.assertEqual(stream_1.is_compressed(), True)
            self.assertEqual(stream_3.current, netius.common.CHUNKED_ENCODING)
            self.assertEqual(stream_3.is_compressed(), False)

            # the encoding state must live in the stream itself instead of
            # being delegated to the connection through the attribute lookup
            self.assertIn("current", stream_1.__dict__)
            self.assertEqual(connection.current, netius.common.GZIP_ENCODING)
        finally:
            parser.clear(force=True)

    def test_get_encodings(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)
            stream.headers = {"accept-encoding": "deflate;q=0.5, gzip"}

            # the codings must be resolved with the same quality value rules
            # used in the HTTP/1 parser, being cached in the stream afterwards
            self.assertEqual(stream.get_encodings(), ["gzip", "deflate"])
            self.assertEqual(stream.encodings, ["gzip", "deflate"])
        finally:
            parser.clear(force=True)

    def test_ctx_request(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)
            stream.set_gzip()

            # under the request context the encoding state of the stream is
            # the one visible in the connection, being restored on exit
            with stream.ctx_request():
                self.assertEqual(connection.current, netius.common.GZIP_ENCODING)
                connection.set_deflate()
                connection.encoding_c = "deflate"
            self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)
            self.assertEqual(connection.encoding_c, None)

            # the changes performed under the context must have been stored
            # back into the stream instead of being lost on the restore
            self.assertEqual(stream.current, netius.common.DEFLATE_ENCODING)
            self.assertEqual(stream.encoding_c, "deflate")
        finally:
            parser.clear(force=True)

    def _make_connection(self, encoding=netius.common.PLAIN_ENCODING):
        # builds a minimal HTTP/2 connection (and parser) that satisfies the
        # encoding and window probes performed on the creation of a stream
        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.window_o = netius.common.HTTP2_WINDOW
        connection.parser = netius.common.HTTP2Parser(connection, store=True)
        return connection
