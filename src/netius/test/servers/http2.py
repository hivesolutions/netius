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
import netius.servers.http2

try:
    import hpack
except ImportError:
    hpack = None


class HTTP2ServerTest(unittest.TestCase):

    def test__has_hpack(self):
        result = netius.servers.HTTP2Server._has_hpack()
        self.assertEqual(result in (True, False), True)

    def test__has_alpn(self):
        result = netius.servers.HTTP2Server._has_alpn()
        self.assertEqual(result in (True, False), True)

    def test__has_npn(self):
        result = netius.servers.HTTP2Server._has_npn()
        self.assertEqual(result in (True, False), True)

    def test_info_dict(self):
        http2_server = netius.servers.HTTP2Server()
        info = http2_server.info_dict()

        self.assertEqual(info["legacy"], True)
        self.assertEqual(info["safe"], False)
        self.assertEqual(info["has_h2"], http2_server._has_h2())
        self.assertEqual(info["has_all_h2"], http2_server._has_all_h2())

    def test_get_protocols(self):
        http2_server = netius.servers.HTTP2Server(legacy=True, safe=True)
        protocols = http2_server.get_protocols()

        self.assertEqual(protocols, ["http/1.1", "http/1.0"])

        http2_server = netius.servers.HTTP2Server(legacy=False, safe=True)
        protocols = http2_server.get_protocols()

        self.assertEqual(protocols, [])

        http2_server = netius.servers.HTTP2Server(legacy=True, safe=False)
        protocols = http2_server.get_protocols()

        if http2_server.has_h2:
            self.assertEqual(protocols, ["h2", "http/1.1", "http/1.0"])
        else:
            self.assertEqual(protocols, ["http/1.1", "http/1.0"])


class HTTP2ConnectionTest(unittest.TestCase):

    def setUp(self):
        self.settings = dict(netius.common.HTTP2_SETTINGS_OPTIMAL)
        self.settings_r = dict(netius.common.HTTP2_SETTINGS)
        self.window = netius.common.HTTP2_WINDOW

    def test_split_frame(self):
        connection = self._make_connection()
        try:
            stream = self._make_stream(connection, window=1)

            # the payload is larger than the window of the stream so the
            # frame must be delayed instead of being sent immediately
            connection.send_data(b"hello", stream=stream.identifier)

            self.assertEqual(len(connection.sent), 0)
            self.assertEqual(len(connection.frames), 1)
            self.assertEqual(connection.frames[0][1]["payload"], b"hello")

            connection.split_frame(connection.frames[0], 1)

            # only the first byte of the payload should have been sent, with
            # the end stream flag unset, as the frame is not yet complete
            self.assertEqual(len(connection.sent), 1)
            self.assertEqual(connection.sent[0][4:5], b"\x00")
            self.assertEqual(connection.sent[0][9:], b"h")

            # the remaining payload must be kept in the delayed frame and
            # both of the windows decremented by the amount that was sent
            self.assertEqual(connection.frames[0][1]["payload"], b"ello")
            self.assertEqual(stream.window, 0)
            self.assertEqual(connection.window, self.window - 1)
        finally:
            connection.parser.clear(force=True)

    def test_flush_frames(self):
        connection = self._make_connection()
        try:
            stream = self._make_stream(connection, window=0)

            connection.send_data(b"hello", stream=stream.identifier)

            self.assertEqual(len(connection.sent), 0)
            self.assertEqual(len(connection.frames), 1)
            self.assertEqual(connection.unavailable, {stream.identifier: True})

            # a window that only accommodates part of the payload must still
            # make progress, sending such part and delaying the remaining one
            stream.remote_update(2)
            connection.flush_frames()

            self.assertEqual(len(connection.sent), 1)
            self.assertEqual(connection.sent[0][4:5], b"\x00")
            self.assertEqual(connection.sent[0][9:], b"he")
            self.assertEqual(connection.frames[0][1]["payload"], b"llo")
            self.assertEqual(stream.window, 0)

            # as soon as the window becomes large enough the remaining payload
            # is sent as a whole, this time carrying the end stream flag
            stream.remote_update(3)
            connection.flush_frames()

            self.assertEqual(len(connection.sent), 2)
            self.assertEqual(connection.sent[1][4:5], b"\x01")
            self.assertEqual(connection.sent[1][9:], b"llo")
            self.assertEqual(len(connection.frames), 0)
            self.assertEqual(stream.frames, 0)
        finally:
            connection.parser.clear(force=True)

    def test_set_settings(self):
        if hpack == None:
            self.skipTest("Skipping test: hpack unavailable")

        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.settings_r = self.settings_r
        connection.parser = netius.common.HTTP2Parser(self, store=True)

        try:
            self.assertEqual(connection.parser._encoder, None)

            connection.set_settings(
                {netius.common.http2.SETTINGS_HEADER_TABLE_SIZE: 8192}
            )
            self.assertEqual(connection.parser._encoder, None)
            self.assertEqual(
                connection.settings_r[netius.common.http2.SETTINGS_HEADER_TABLE_SIZE],
                8192,
            )

            self.assertEqual(connection.parser.encoder.header_table_size, 8192)

            connection.set_settings(
                {netius.common.http2.SETTINGS_HEADER_TABLE_SIZE: 16384}
            )
            self.assertEqual(connection.parser._encoder.header_table_size, 16384)
        finally:
            connection.parser.clear(force=True)

    def test_set_settings_window(self):
        connection = self._make_connection()
        connection.settings_r[netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE] = 3
        try:
            stream = self._make_stream(connection, window=3)

            connection.send_data(b"hello", stream=stream.identifier)

            self.assertEqual(len(connection.sent), 0)
            self.assertEqual(len(connection.frames), 1)

            # a change to the initial window size must be applied to the
            # streams that are already open, unblocking the delayed frame
            connection.set_settings(
                {netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE: 4}
            )

            self.assertEqual(stream.window, 0)
            self.assertEqual(len(connection.sent), 1)
            self.assertEqual(connection.sent[0][9:], b"hell")
            self.assertEqual(connection.frames[0][1]["payload"], b"o")

            # a reduction of the initial window size must be applied as well,
            # even if that makes the window of the stream a negative value
            connection.set_settings(
                {netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE: 3}
            )

            self.assertEqual(stream.window, -1)
            self.assertEqual(len(connection.sent), 1)
        finally:
            connection.parser.clear(force=True)

    def test_available_stream(self):
        connection = self._make_connection()
        try:
            stream = self._make_stream(connection, window=4)

            self.assertEqual(connection.available_stream(stream.identifier, 4), True)
            self.assertEqual(connection.available_stream(stream.identifier, 5), False)

            # a zero length payload does not consume any of the windows so
            # it remains available even for an exhausted stream window
            stream.remote_update(-4)

            self.assertEqual(connection.available_stream(stream.identifier, 1), False)
            self.assertEqual(connection.available_stream(stream.identifier, 0), True)

            # the ordering constraint must still be verified, so that a frame
            # is never sent ahead of the ones that are already delayed
            stream.frames += 1

            self.assertEqual(connection.available_stream(stream.identifier, 0), False)
            self.assertEqual(
                connection.available_stream(stream.identifier, 0, strict=False), True
            )
        finally:
            connection.parser.clear(force=True)

    def test_partial_stream(self):
        connection = self._make_connection()
        try:
            stream = self._make_stream(connection, window=2)

            self.assertEqual(connection.partial_stream(stream.identifier, 5), 2)
            self.assertEqual(connection.partial_stream(stream.identifier, 1), 1)

            # a negative window (eg: a reduction of the initial window size)
            # must never produce a negative amount of bytes to be sent
            stream.remote_update(-3)

            self.assertEqual(connection.partial_stream(stream.identifier, 5), 0)

            # the window of the connection is an upper bound for the value,
            # even when the window of the stream is larger than it
            stream.remote_update(1024)
            connection.window = 4

            self.assertEqual(connection.partial_stream(stream.identifier, 5), 4)
        finally:
            connection.parser.clear(force=True)

    def _make_connection(self):
        # builds a minimal HTTP/2 connection (and parser) that satisfies the
        # window probes performed by the flow control operations, replacing
        # the send operation by a simple collector of the sent messages
        connection = netius.servers.http2.HTTP2Connection.__new__(
            netius.servers.http2.HTTP2Connection
        )
        connection.legacy = False
        connection.owner = netius.servers.HTTP2Server()
        connection.encoding = netius.common.PLAIN_ENCODING
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.settings = dict(self.settings)
        connection.settings_r = dict(self.settings_r)
        connection.window = self.window
        connection.window_o = self.settings[
            netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE
        ]
        connection.frames = []
        connection.unavailable = {}
        connection.sent = []
        connection.send = lambda data, **kwargs: connection.sent.append(data)
        connection.parser = netius.common.HTTP2Parser(connection, store=True)
        return connection

    def _make_stream(self, connection, window=netius.common.HTTP2_WINDOW):
        # builds an open stream with the requested (remote) window, registering
        # it in the parser so that the flow control operations may reach it
        stream = netius.common.http2.HTTP2Stream(
            identifier=1, owner=connection.parser, window=window
        )
        stream.open()
        connection.parser._set_stream(stream)
        return stream
