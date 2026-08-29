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
import netius.servers

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

RESERVED_PING_FRAME = _pack_frame(
    netius.common.PING,
    stream=0x80000000,
    payload=b"\x01\x02\x03\x04\x05\x06\x07\x08",
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
        self.window_o = netius.common.HTTP2_WINDOW

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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE",
                    parser.assert_header,
                )
        finally:
            parser.clear(force=True)

    def test_assert_stream(self):
        parser = self._make_connection().parser
        try:
            # a stream that has been opened by the client carries an odd
            # identifier, an even one belongs to the server
            parser.assert_stream(self._make_stream(parser, identifier=1))
            self.assertRaises(
                netius.ParserError,
                parser.assert_stream,
                self._make_stream(parser, identifier=2),
            )

            # a stream that depends on itself would form a cycle in the
            # tree of priorities, so it may never be accepted
            self.assertRaises(
                netius.ParserError,
                parser.assert_stream,
                self._make_stream(parser, identifier=1, dependency=1),
            )
        finally:
            parser.clear(force=True)

    def test_assert_stream_concurrent(self):
        parser = self._make_connection().parser
        try:
            # the number of streams that may be open at the same time is
            # bounded by the setting that has been announced to the client
            maximum = self.settings[netius.common.http2.SETTINGS_MAX_CONCURRENT_STREAMS]
            for identifier in range(maximum):
                parser.streams[identifier] = self._make_stream(
                    parser, identifier=identifier
                )

            self.assertRaises(
                netius.ParserError,
                parser.assert_stream,
                self._make_stream(parser, identifier=1),
            )
        finally:
            parser.clear(force=True)

    def test_assert_data(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01

            # a data frame may only be received once the headers of the
            # stream are complete, as the message is not yet framed
            self.assertRaises(
                netius.ParserError,
                parser.assert_data,
                self._make_stream(parser, end_headers=False),
                False,
            )

            parser.assert_data(self._make_stream(parser, end_headers=True), False)

            # a stream that the client has already half closed may no
            # longer carry any data towards the server
            self.assertRaises(
                netius.ParserError,
                parser.assert_data,
                self._make_stream(parser, end_headers=True, end_stream=True),
                False,
            )
        finally:
            parser.clear(force=True)

    def test_assert_data_stream(self):
        parser = self._make_connection().parser
        try:
            # the connection level stream never carries data, as a data
            # frame is always bound to a request
            parser.stream = 0x00

            self.assertRaises(
                netius.ParserError,
                parser.assert_data,
                self._make_stream(parser, end_headers=True),
                False,
            )
        finally:
            parser.clear(force=True)

    def test_assert_headers(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01

            # a second headers frame is only allowed as the trailers of a
            # message, so it has to carry the end of the stream
            parser.assert_headers(self._make_stream(parser), True)
            self.assertRaises(
                netius.ParserError,
                parser.assert_headers,
                self._make_stream(parser),
                False,
            )

            # a stream that the client has already half closed may not be
            # extended with any further headers
            self.assertRaises(
                netius.ParserError,
                parser.assert_headers,
                self._make_stream(parser, end_headers=True, end_stream=True),
                True,
            )
        finally:
            parser.clear(force=True)

    def test_assert_priority(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01

            parser.assert_priority(self._make_stream(parser, identifier=1), 3)

            # a stream that depends on itself would form a cycle, the
            # dependency of the frame naming the very stream that it reorders
            self.assertRaises(
                netius.ParserError,
                parser.assert_priority,
                self._make_stream(parser, identifier=1),
                1,
            )
        finally:
            parser.clear(force=True)

    def test_assert_priority_stream(self):
        parser = self._make_connection().parser
        try:
            # a priority frame always names the stream it reorders, so it
            # is never bound to the connection level one
            parser.stream = 0x00

            self.assertRaises(netius.ParserError, parser.assert_priority, None, 3)
        finally:
            parser.clear(force=True)

    def test_assert_rst_stream(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01
            parser._max_stream = 0x01

            parser.assert_rst_stream(self._make_stream(parser, identifier=1))

            # a stream that was never opened may not be reset, as there is
            # nothing on the server to be torn down
            parser.stream = 0x03

            self.assertRaises(
                netius.ParserError,
                parser.assert_rst_stream,
                self._make_stream(parser, identifier=3),
            )
        finally:
            parser.clear(force=True)

    def test_assert_rst_stream_connection(self):
        parser = self._make_connection().parser
        try:
            # the connection level stream is not a stream that may be
            # reset, so the frame is rejected outright
            parser.stream = 0x00

            self.assertRaises(netius.ParserError, parser.assert_rst_stream, None)
        finally:
            parser.clear(force=True)

    def test_assert_continuation(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01
            parser.last_type = netius.common.HEADERS

            parser.assert_continuation(self._make_stream(parser))

            # a continuation only ever follows a frame that opened a block
            # of headers, so anything else before it is a protocol error
            parser.last_type = netius.common.DATA

            self.assertRaises(
                netius.ParserError,
                parser.assert_continuation,
                self._make_stream(parser),
            )
        finally:
            parser.clear(force=True)

    def test_assert_continuation_closed(self):
        parser = self._make_connection().parser
        try:
            parser.stream = 0x01
            parser.last_type = netius.common.HEADERS

            # a stream that the client has already half closed may not be
            # extended with any further block of headers
            self.assertRaises(
                netius.ParserError,
                parser.assert_continuation,
                self._make_stream(parser, end_headers=True, end_stream=True),
            )
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Stream must be set to 0x00 for SETTINGS",
                    lambda: parser.assert_settings([], False),
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS with ACK must be zero length",
                    lambda: parser.assert_settings([], True),
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Size of SETTINGS frame must be a multiple of 6",
                    lambda: parser.assert_settings([], False),
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS_ENABLE_PUSH different from 0 or 1",
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE too small",
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS_MAX_FRAME_SIZE too large",
                    lambda: parser.assert_settings(settings, False),
                )

            parser.stream = 0x00
            parser.length = 6
            settings = [(netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE, 2147483648)]
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "SETTINGS_INITIAL_WINDOW_SIZE too large",
                    lambda: parser.assert_settings(settings, False),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "SETTINGS_INITIAL_WINDOW_SIZE too large",
                    lambda: parser.assert_settings(settings, False),
                )

            # only the values of the settings are verified by the extended
            # mode, so that the framing of the frame may be verified alone
            parser.stream = 0x00
            parser.length = 6
            settings = [(netius.common.http2.SETTINGS_ENABLE_PUSH, 2)]
            parser.assert_settings(settings, False, extended=False)
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "PUSH_PROMISE not allowed for server",
                    lambda: parser.assert_push_promise(0x02),
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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Stream must be set to 0x00 for PING",
                    parser.assert_ping,
                )

            parser.stream = 0x00
            parser.length = 4
            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Size of PING frame must be 8",
                    parser.assert_ping,
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Size of PING frame must be 8",
                    parser.assert_ping,
                )

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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Stream must be set to 0x00 for GOAWAY",
                    parser.assert_goaway,
                )

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
                self.assertRaisesRegex(
                    netius.ParserError,
                    "WINDOW_UPDATE increment must not be zero",
                    lambda: parser.assert_window_update(None, 0),
                )

            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Window value for the connection too large",
                    lambda: parser.assert_window_update(None, 2147483647),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Window value for the connection too large",
                    lambda: parser.assert_window_update(None, 2147483647),
                )

            parser.assert_window_update(None, 4096)

            # the connection window may only be changed by an update sent
            # for the zero stream, so an update sent for a "normal" stream
            # must not be verified against the value of such window
            parser.stream = 0x01
            parser.assert_window_update(None, 2147483647)

            # an update that overflows the window of the stream is a stream
            # level error, meaning that only such stream is reset by it
            stream = netius.common.http2.HTTP2Stream.__new__(
                netius.common.http2.HTTP2Stream
            )
            stream.window = 1

            if hasattr(self, "assertRaisesRegexp"):
                self.assertRaisesRegexp(
                    netius.ParserError,
                    "Window value for the stream too large",
                    lambda: parser.assert_window_update(stream, 2147483647),
                )
            else:
                self.assertRaisesRegex(
                    netius.ParserError,
                    "Window value for the stream too large",
                    lambda: parser.assert_window_update(stream, 2147483647),
                )

            try:
                parser.assert_window_update(stream, 2147483647)
            except netius.ParserError as error:
                self.assertEqual(error.get_kwarg("stream"), 0x01)
                self.assertEqual(
                    error.get_kwarg("error_code"),
                    netius.common.http2.FLOW_CONTROL_ERROR,
                )
        finally:
            parser.clear(force=True)

    def test_parse_header(self):
        parser = netius.common.HTTP2Parser(self, store=True)
        try:
            # the reserved bit of the frame header must be ignored, so that
            # only the remaining bits are taken as the stream identifier,
            # note that a ping is only valid for the zero stream
            count = parser.parse(RESERVED_PING_FRAME)
            self.assertEqual(count, len(RESERVED_PING_FRAME))
            self.assertEqual(parser.type, netius.common.PING)
            self.assertEqual(parser.stream, 0x00)
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

    def test_parse_data(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(parser, identifier=1, end_headers=True)
            parser.streams[1] = stream

            events = []
            parser.bind("on_data_h2", lambda stream, contents: events.append(contents))

            frame = _pack_frame(
                netius.common.DATA, flags=0x01, stream=0x01, payload=b"Hello World"
            )
            parser.parse(frame)

            # the payload of the frame reaches the stream untouched and the
            # end of stream flag closes the remote side of it
            self.assertEqual(events, [b"Hello World"])
            self.assertEqual(stream.end_stream, True)
        finally:
            parser.clear(force=True)

    def test_parse_data_padded(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(parser, identifier=1, end_headers=True)
            parser.streams[1] = stream

            events = []
            parser.bind("on_data_h2", lambda stream, contents: events.append(contents))

            # the padding is announced by a leading byte and is removed from
            # the tail, so that neither of them reaches the stream
            payload = struct.pack("!B", 4) + b"Hello World" + b"\0" * 4
            frame = _pack_frame(
                netius.common.DATA, flags=0x08, stream=0x01, payload=payload
            )
            parser.parse(frame)

            self.assertEqual(events, [b"Hello World"])
            self.assertEqual(stream.end_stream, False)
        finally:
            parser.clear(force=True)

    def test_parse_data_ready(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = self._make_connection()
        parser = connection.parser
        try:
            events = []
            parser.bind("on_data", lambda: events.append("data"))

            block = hpack.Encoder().encode(
                [
                    (":method", "POST"),
                    (":scheme", "https"),
                    (":path", "/"),
                    ("content-length", "11"),
                ]
            )
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x04, stream=0x01, payload=block
            )
            parser.parse(frame)

            # the end of the header block alone is not enough to make the
            # stream ready, as the payload of the request is still pending
            self.assertEqual(events, [])

            frame = _pack_frame(
                netius.common.DATA, flags=0x01, stream=0x01, payload=b"Hello World"
            )
            parser.parse(frame)

            # the end of stream completes the request and so the message is
            # handed over to the upper layers as a complete one
            stream = parser.streams[1]
            self.assertEqual(events, ["data"])
            self.assertEqual(stream.method, "POST")
            self.assertEqual(stream.content_l, 11)
            self.assertEqual(stream.get_message_b().read(), b"Hello World")
        finally:
            parser.clear(force=True)

    def test_parse_headers(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = self._make_connection()
        parser = connection.parser
        try:
            events = []
            parser.bind("on_headers", lambda: events.append("headers"))
            parser.bind("on_data", lambda: events.append("data"))

            block = hpack.Encoder().encode(
                [(":method", "GET"), (":scheme", "https"), (":path", "/hello?name=joe")]
            )
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x05, stream=0x01, payload=block
            )
            parser.parse(frame)

            # a request that carries no payload is complete as soon as the
            # single frame that opened the stream has been parsed
            stream = parser.streams[1]
            self.assertEqual(events, ["headers", "data"])
            self.assertEqual(stream.method, "GET")
            self.assertEqual(stream.get_path(), "/hello")
            self.assertEqual(stream.get_query(), "name=joe")
        finally:
            parser.clear(force=True)

    def test_parse_headers_padded(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            # the padding is announced by a leading byte and is removed from
            # the tail, so that neither of them reaches the block of headers
            payload = struct.pack("!B", 3) + b"fragment" + b"\0" * 3
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x08, stream=0x01, payload=payload
            )
            parser.parse(frame)

            stream = parser.streams[1]
            self.assertEqual(stream.header_b, [b"fragment"])
            self.assertEqual(stream.end_headers, False)
        finally:
            parser.clear(force=True)

    def test_parse_headers_priority(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            # the priority is announced by a leading dependency and weight,
            # the highest bit of the dependency being the exclusive flag and
            # the weight of the wire being one below the effective one
            payload = struct.pack("!IB", 0x80000003, 42) + b"fragment"
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x20, stream=0x01, payload=payload
            )
            parser.parse(frame)

            stream = parser.streams[1]
            self.assertEqual(stream.dependency, 3)
            self.assertEqual(stream.weight, 43)
            self.assertEqual(stream.exclusive, True)
            self.assertEqual(stream.header_b, [b"fragment"])
        finally:
            parser.clear(force=True)

    def test_parse_headers_priority_lowest(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(
                owner=parser, identifier=1, weight=16
            )
            parser.streams[1] = stream

            payload = struct.pack("!IB", 3, 0) + b"fragment"
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x21, stream=0x01, payload=payload
            )
            parser.parse(frame)

            # the lowest weight of the wire names the effective weight of
            # one, a value of its own that is no longer confused with the
            # absence of a priority in the frame
            self.assertEqual(stream.weight, 1)
        finally:
            parser.clear(force=True)

    def test_parse_headers_priority_absent(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x00, stream=0x01, payload=b"fragment"
            )
            parser.parse(frame)

            # a frame that announces no priority opens the stream with the
            # default weight that the RFC names for it, and not with a value
            # that falls outside of the range of an effective weight
            stream = parser.streams[1]
            self.assertEqual(stream.weight, 16)
        finally:
            parser.clear(force=True)

    def test_parse_headers_priority_kept(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(
                owner=parser, identifier=1, weight=42
            )
            parser.streams[1] = stream

            frame = _pack_frame(
                netius.common.HEADERS, flags=0x01, stream=0x01, payload=b"fragment"
            )
            parser.parse(frame)

            # a frame that announces no priority leaves the weight of a
            # stream that is already open untouched, rather than resetting
            # it to the default of a new one
            self.assertEqual(stream.weight, 42)
        finally:
            parser.clear(force=True)

    def test_parse_headers_trailers(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = self._make_connection()
        parser = connection.parser
        try:
            encoder = hpack.Encoder()
            block = encoder.encode(
                [(":method", "GET"), (":scheme", "https"), (":path", "/")]
            )
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x04, stream=0x01, payload=block
            )
            parser.parse(frame)

            # the trailers of a message reopen the block of headers of a
            # stream that is already open, updating its priority in place
            payload = struct.pack("!IB", 0x80000005, 7) + encoder.encode(
                [("x-checksum", "1")]
            )
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x25, stream=0x01, payload=payload
            )
            parser.parse(frame)

            stream = parser.streams[1]
            self.assertEqual(stream.dependency, 5)
            self.assertEqual(stream.weight, 8)
            self.assertEqual(stream.exclusive, True)
            self.assertEqual(stream.end_stream, True)
            self.assertEqual(stream.end_headers, True)
        finally:
            parser.clear(force=True)

    def test_parse_priority(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(parser, identifier=1)
            parser.streams[1] = stream

            events = []
            parser.bind(
                "on_priority",
                lambda stream, dependency, weight: events.append((dependency, weight)),
            )

            frame = _pack_frame(
                netius.common.PRIORITY,
                stream=0x01,
                payload=struct.pack("!IB", 3, 16),
            )
            parser.parse(frame)

            # the dependency and the weight are recorded in the stream so
            # that the tree of priorities may be rebuilt from them, the
            # weight being the effective one, which the RFC defines as the
            # value that travels in the wire plus one
            self.assertEqual(events, [(3, 17)])
            self.assertEqual(stream.dependency, 3)
            self.assertEqual(stream.weight, 17)
        finally:
            parser.clear(force=True)

    def test_parse_priority_lowest(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(parser, identifier=1)
            parser.streams[1] = stream

            frame = _pack_frame(
                netius.common.PRIORITY,
                stream=0x01,
                payload=struct.pack("!IB", 3, 0),
            )
            parser.parse(frame)

            # the lowest weight of the wire names the effective weight of
            # one, which is the smallest that the RFC allows for a stream
            self.assertEqual(stream.weight, 1)
        finally:
            parser.clear(force=True)

    def test_parse_rst_stream(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(parser, identifier=1)
            parser.streams[1] = stream
            parser._max_stream = 0x01

            events = []
            parser.bind(
                "on_rst_stream",
                lambda stream, error_code: events.append(error_code),
            )

            frame = _pack_frame(
                netius.common.RST_STREAM,
                stream=0x01,
                payload=struct.pack("!I", netius.common.http2.CANCEL),
            )
            parser.parse(frame)

            self.assertEqual(events, [netius.common.http2.CANCEL])
        finally:
            parser.clear(force=True)

    def test_parse_push_promise(self):
        connection = self._make_connection()
        parser = connection.parser
        seen = []
        parser.bind("on_push_promise", lambda *args: seen.append(args))
        try:
            # a promise may only travel from a server towards a client, so
            # one that arrives at the server is always a protocol error
            frame = _pack_frame(
                netius.common.PUSH_PROMISE,
                flags=0x04,
                stream=0x01,
                payload=struct.pack("!I", 2) + b"fragment",
            )

            self.assertRaises(netius.ParserError, parser.parse, frame)

            # the refusal happens before any event, so a promise never
            # reaches a listener that is bound to the parser
            self.assertEqual(seen, [])
        finally:
            parser.clear(force=True)

    def test_parse_push_promise_padded(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            # the padding of the promise is stripped before the direction of
            # it is verified, so that a padded one is refused just the same
            payload = (
                struct.pack("!B", 4) + struct.pack("!I", 2) + b"fragment" + b"\0" * 4
            )
            frame = _pack_frame(
                netius.common.PUSH_PROMISE,
                flags=0x0C,
                stream=0x01,
                payload=payload,
            )

            self.assertRaises(netius.ParserError, parser.parse, frame)
        finally:
            parser.clear(force=True)

    def test_parse_continuation(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            events = []
            parser.bind("on_continuation", lambda stream: events.append(stream))

            # a continuation only ever follows a block of headers that was
            # left open on the very same stream
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x01, stream=0x01, payload=b"frag"
            )
            parser.parse(frame)

            # without the end of headers flag the fragment is only buffered,
            # as the block of headers is not yet complete to be decoded
            frame = _pack_frame(
                netius.common.CONTINUATION, stream=0x01, payload=b"ment"
            )
            parser.parse(frame)

            stream = parser.streams[1]
            self.assertEqual(events, [stream])
            self.assertEqual(stream.end_headers, False)
            self.assertEqual(stream.header_b, [b"frag", b"ment"])
            self.assertEqual(stream.headers_l, None)
        finally:
            parser.clear(force=True)

    def test_parse_continuation_end_headers(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = self._make_connection()
        parser = connection.parser
        try:
            events = []
            parser.bind("on_headers", lambda: events.append("headers"))
            parser.bind("on_data", lambda: events.append("data"))

            # the block of headers is split around the two frames, so that
            # only the joining of both of them may be decoded
            block = hpack.Encoder().encode(
                [(":method", "GET"), (":scheme", "https"), (":path", "/")]
            )
            frame = _pack_frame(
                netius.common.HEADERS, flags=0x01, stream=0x01, payload=block[:1]
            )
            parser.parse(frame)

            self.assertEqual(events, [])

            frame = _pack_frame(
                netius.common.CONTINUATION,
                flags=0x04,
                stream=0x01,
                payload=block[1:],
            )
            parser.parse(frame)

            # the end of the header block completes a request that carried
            # the end of stream flag and so no payload is expected for it
            stream = parser.streams[1]
            self.assertEqual(events, ["headers", "data"])
            self.assertEqual(stream.method, "GET")
            self.assertEqual(stream.path_s, "/")
            self.assertEqual(stream.is_ready, True)
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

    def _make_connection(self, encoding=netius.common.PLAIN_ENCODING):
        # builds a minimal HTTP/2 connection (and parser) that satisfies the
        # encoding, settings and window probes performed by the assertions
        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.owner = netius.servers.HTTPServer()
        connection.settings = dict(netius.common.HTTP2_SETTINGS_OPTIMAL)
        connection.settings_r = dict(netius.common.HTTP2_SETTINGS)
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.window = netius.common.HTTP2_WINDOW
        connection.window_o = netius.common.HTTP2_WINDOW
        connection.parser = netius.common.HTTP2Parser(connection, store=True)
        return connection

    def _make_stream(
        self, parser, identifier=1, dependency=0x00, end_headers=False, end_stream=False
    ):
        # builds a stream bound to the provided parser, carrying only the state
        # that the assertions of the parser are going to look at
        return netius.common.http2.HTTP2Stream(
            owner=parser,
            identifier=identifier,
            dependency=dependency,
            end_headers=end_headers,
            end_stream=end_stream,
        )


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

    def test_encoding_w(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)

            # the encoding of the stream must be the one resolved from its
            # own state and never the one of the shared connection
            connection.set_plain()
            self.assertEqual(stream.encoding_w(), netius.common.GZIP_ENCODING)
            self.assertEqual(stream.encoding_name(), "gzip")

            # the per response dynamic state of the stream must clamp the
            # encoding so that no re-encoding of the payload is performed
            stream.dynamic = True
            self.assertEqual(stream.encoding_w(), netius.common.CHUNKED_ENCODING)
            self.assertEqual(stream.encoding_name(), None)
        finally:
            parser.clear(force=True)

    def test_set_base(self):
        connection = self._make_connection(encoding=netius.common.GZIP_ENCODING)
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)
            stream.set_deflate()
            stream.encoding_c = "deflate"
            stream.encodings_a = ["deflate"]
            stream.dynamic = True

            stream.set_base()

            # the base encoding is the one that the connection negotiated,
            # the state that is specific to a response being discarded
            self.assertEqual(stream.current, netius.common.GZIP_ENCODING)
            self.assertEqual(stream.encoding_c, None)
            self.assertEqual(stream.encodings_a, None)
            self.assertEqual(stream.dynamic, None)
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

    def test_decode_headers(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = self._make_connection()
        parser = connection.parser
        try:
            # a dynamic table size update beyond the negotiated maximum must
            # be refused, as the peer would otherwise be able to grow the
            # table of the decoder without any bound
            stream = self._make_stream(parser, [])
            stream.end_headers = True
            stream.header_b = [b"\x3f\xe1\xff\x03\x82"]

            self.assertRaises(netius.ParserError, stream.decode_headers)

            # the failure in the decoding of a field block is a connection
            # level error, as the dynamic table becomes unsynchronized
            stream = self._make_stream(parser, [])
            stream.end_headers = True
            stream.header_b = [b"\x3f\xe1\xff\x03\x82"]
            try:
                stream.decode_headers()
            except netius.ParserError as error:
                self.assertEqual(
                    error.get_kwarg("error_code"),
                    netius.common.http2.COMPRESSION_ERROR,
                )
                self.assertEqual(error.get_kwarg("stream"), None)
        finally:
            parser.clear(force=True)

    def test_get_path(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)

            # the path is the part of the target that comes before the
            # query, which is left out of it
            stream.path_s = "/hello?name=joe"
            self.assertEqual(stream.get_path(), "/hello")

            # an absolute target is only reduced to its path when the
            # normalization is requested, as a proxy may hand one out
            stream.path_s = "https://example.com/proxied?name=joe"
            self.assertEqual(stream.get_path(), "https://example.com/proxied")
            self.assertEqual(stream.get_path(normalize=True), "/proxied")

            # a relative target is untouched by the normalization, as there
            # is no absolute prefix to be removed from it
            stream.path_s = "/hello"
            self.assertEqual(stream.get_path(normalize=True), "/hello")
        finally:
            parser.clear(force=True)

    def test_get_query(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)

            stream.path_s = "/hello?name=joe&flag"
            self.assertEqual(stream.get_query(), "name=joe&flag")

            # a target without a query yields an empty one, so that the
            # parsing of the arguments may be run over it unconditionally
            stream.path_s = "/hello"
            self.assertEqual(stream.get_query(), "")
        finally:
            parser.clear(force=True)

    def test_get_message_b(self):
        connection = self._make_connection()
        parser = connection.parser
        headers = [
            (":method", "POST"),
            (":scheme", "https"),
            (":path", "/"),
            ("content-length", "11"),
        ]
        try:
            stream = netius.common.http2.HTTP2Stream(
                identifier=1, owner=parser, store=True
            )
            stream.headers_l = headers
            stream.end_headers = True
            stream._calculate()
            stream.extend_data(b"Hello World")

            # the shallow buffer is the one of the stream itself, handed
            # out rewound so that it may be read from its beginning
            shallow = stream.get_message_b()
            self.assertEqual(shallow.read(), b"Hello World")
            self.assertEqual(stream.get_message_b().read(), b"Hello World")

            # a copy is a buffer of its own, the one of the stream being
            # left rewound so that it may still be read afterwards
            copy = stream.get_message_b(copy=True)
            self.assertEqual(copy.read(), b"Hello World")
            self.assertEqual(copy is shallow, False)
            self.assertEqual(shallow.read(), b"Hello World")

            # a payload that goes over the file limit is kept in a file
            # system based buffer instead of an in memory one
            stream = netius.common.http2.HTTP2Stream(
                identifier=3, owner=parser, store=True, file_limit=4
            )
            stream.headers_l = headers
            stream.end_headers = True
            stream._calculate()
            stream.extend_data(b"Hello World")

            copy = stream.get_message_b(copy=True)
            try:
                self.assertEqual(copy.read(), b"Hello World")
                self.assertEqual(hasattr(copy, "name"), True)
            finally:
                copy.close()
        finally:
            parser.clear(force=True)

    def test_fragment(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            # the maximum payload of a frame is bound by the maximum frame size
            # of the peer and not by the window, so that a stream opened under
            # an exhausted window is still able to fragment its payload
            stream = netius.common.http2.HTTP2Stream(
                identifier=1, owner=parser, window=0, frame_size=16384
            )

            self.assertEqual(stream.window_m, 16384 - netius.common.http2.HEADER_SIZE)
            self.assertEqual(stream.fragmentable(b"x" * 20000), True)

            # with an exhausted window no initial fragment is produced, as an
            # empty data frame would otherwise be sent for it
            fragments = list(stream.fragment(b"x" * 20000))
            self.assertEqual([len(fragment) for fragment in fragments], [16375, 3625])

            # the initial fragment is the one that fits the current window while
            # the remaining ones are bound by the maximum payload of a frame
            stream.remote_update(1000)
            fragments = list(stream.fragment(b"x" * 20000))
            self.assertEqual(
                [len(fragment) for fragment in fragments], [1000, 16375, 2625]
            )

            # a negative window (eg: a reduction of the initial window size)
            # must not produce an initial fragment either
            stream.remote_update(-1001)
            fragments = list(stream.fragment(b"x" * 20000))
            self.assertEqual([len(fragment) for fragment in fragments], [16375, 3625])
        finally:
            parser.clear(force=True)

    def test_assert_headers(self):
        connection = self._make_connection()
        parser = connection.parser
        base = [(":method", "GET"), (":scheme", "https"), (":path", "/")]
        try:
            # a valid set of headers carries every mandatory pseudo-header
            # with all of them positioned before the normal ones
            stream = self._make_stream(parser, base + [("accept", "*/*")])
            stream.assert_headers()

            # the headers that are specific to a single transport level
            # connection must never be present in an HTTP 2 message
            for name in netius.common.http2.HTTP2_CONNECTION:
                stream = self._make_stream(parser, base + [(name, "value")])
                self.assertRaises(netius.ParserError, stream.assert_headers)

            # the TE header is the only exception to the previous rule and
            # it's only allowed while its value is the trailers one
            stream = self._make_stream(parser, base + [("te", "trailers")])
            stream.assert_headers()
            stream = self._make_stream(parser, base + [("te", "gzip")])
            self.assertRaises(netius.ParserError, stream.assert_headers)

            # the name of a header must be a lower cased one, as the casing
            # of it is not preserved by the HTTP 2 specification
            stream = self._make_stream(parser, base + [("Accept", "*/*")])
            self.assertRaises(netius.ParserError, stream.assert_headers)

            # an unknown pseudo-header, a duplicated one and a response only
            # one are all invalid under a request message
            stream = self._make_stream(parser, base + [(":bogus", "value")])
            self.assertRaises(netius.ParserError, stream.assert_headers)
            stream = self._make_stream(parser, base + [(":path", "/other")])
            self.assertRaises(netius.ParserError, stream.assert_headers)
            stream = self._make_stream(parser, base + [(":status", "200")])
            self.assertRaises(netius.ParserError, stream.assert_headers)

            # a pseudo-header must never be positioned after a normal one so
            # that the message may be processed in a single pass
            stream = self._make_stream(
                parser, base[:2] + [("accept", "*/*")] + base[2:]
            )
            self.assertRaises(netius.ParserError, stream.assert_headers)

            # every mandatory pseudo-header must be present, otherwise the
            # target of the request may not be determined
            for index in range(len(base)):
                headers = base[:index] + base[index + 1 :]
                stream = self._make_stream(parser, headers)
                self.assertRaises(netius.ParserError, stream.assert_headers)

            # the target of the request may never be an empty one, as the
            # resource being requested would then be an unknown one
            stream = self._make_stream(
                parser, [(":method", "GET"), (":scheme", "https"), (":path", "")]
            )
            self.assertRaises(netius.ParserError, stream.assert_headers)
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

    def test_calculate_headers(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = self._make_stream(
                parser,
                [
                    (":method", "GET"),
                    (":scheme", "https"),
                    (":path", "/"),
                    (":authority", "example.com"),
                    ("accept", "text/html"),
                    ("accept", "text/plain"),
                    ("accept", "*/*"),
                ],
            )
            stream.end_headers = True

            stream._calculate_headers()

            # a header that is repeated is collapsed into a sequence, so
            # that no value of it is lost on the way in
            self.assertEqual(
                stream.headers["accept"], ["text/html", "text/plain", "*/*"]
            )

            # the authority is the HTTP 2 counterpart of the host header
            # and so it is exposed under that name as well
            self.assertEqual(stream.headers["host"], "example.com")

            # the pseudo-headers are never part of the mapping, being read
            # into the fields of the stream instead
            self.assertEqual(stream.method, "GET")
            self.assertEqual(stream.path_s, "/")
            self.assertEqual(":method" in stream.headers, False)

            # the pairs of the block are normalized into strings, so that
            # the mapping is always a textual one
            stream = self._make_stream(parser, [("content-length", 11)])
            stream.end_headers = True
            stream._calculate_headers()
            self.assertEqual(stream.headers["content-length"], "11")
        finally:
            parser.clear(force=True)

    def test_parse_query(self):
        connection = self._make_connection()
        parser = connection.parser
        try:
            stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)

            # a repeated argument is gathered under a single key and a
            # blank one is kept, as it may still be meaningful
            self.assertEqual(
                stream._parse_query("name=joe&name=mary&flag="),
                dict(name=["joe", "mary"], flag=[""]),
            )

            # a byte based mapping is decoded into a textual one, as the
            # runtime may hand the arguments out either way
            self.assertEqual(
                stream._decode_params({b"name": [b"joe", b"mary"]}),
                dict(name=["joe", "mary"]),
            )
        finally:
            parser.clear(force=True)

    def _make_stream(self, parser, headers):
        # builds a stream carrying the provided sequence of headers so that
        # the assertion of them may be run over it
        stream = netius.common.http2.HTTP2Stream(identifier=1, owner=parser)
        stream.headers_l = headers
        return stream

    def _make_connection(self, encoding=netius.common.PLAIN_ENCODING):
        # builds a minimal HTTP/2 connection (and parser) that satisfies the
        # encoding and window probes performed on the creation of a stream
        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.owner = netius.servers.HTTPServer()
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.window = netius.common.HTTP2_WINDOW
        connection.window_o = netius.common.HTTP2_WINDOW
        connection.parser = netius.common.HTTP2Parser(connection, store=True)
        return connection
