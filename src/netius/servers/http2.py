#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct

import netius.common

from . import http

class HTTP2Stream(netius.Stream):
    pass

class HTTP2Connection(http.HTTPConnection):

    def __init__(self, *args, **kwargs):
        http.HTTPConnection.__init__(self, *args, **kwargs)
        self.preface = False #@todo this must be done via states and not like this (just like SMTP)

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.HTTP2Parser(self)
        self.parser.bind("on_frame", self.on_frame)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_settings", self.on_settings)

    def parse(self, data):
        if not self.preface:
            self.owner.on_preface_http2(self, self.parser)
            self.preface = True
            return
        return self.parser.parse(data)

    def send_response(
        self,
        data = None,
        headers = None,
        version = "HTTP/2.0",
        code = 200,
        code_s = None,
        apply = False,
        flush = True,
        delay = False,
        callback = None
    ):
        # retrieves the various parts that define the response
        # and runs a series of normalization processes to retrieve
        # the relevant information of the data to be sent to client
        data = data or ""
        data = netius.legacy.bytes(data)
        headers = headers or dict()
        data_l = len(data) if data else 0
        is_empty = code in (204, 304) and data_l == 0

        # verifies if the content length header is currently present
        # in the provided headers and in case it's not inserts it
        if not "content-length" in headers and not is_empty:
            headers["content-length"] = str(data_l)

        # in case the apply flag is set the apply all operation is performed
        # so that a series of headers are applied to the current context
        # (things like the name of the server connection, etc)
        if apply: self.owner._apply_all(self.parser, self, headers)

        # sends the initial headers data (including status line), this should
        # trigger the initial data sent to the peer/client
        count = self.send_header(
            headers = headers,
            version = version,
            code = code,
            code_s = code_s
        )

        # sends the payload information (data) to the client and optionally flushes
        # the current internal buffers to enforce sending of the value
        count += self.send_payload(
            data,
            flush = flush,
            delay = delay,
            callback = callback
        )
        return count

    def send_header(
        self,
        headers = None,
        version = "HTTP/2.0",
        code = 200,
        code_s = None,
        delay = False,
        callback = None
    ):
        headers = headers or dict()

        # creates the headers base list that is going to store the various
        # header tuples representing the headers in canonical http2 form
        headers_b = []
        headers_b.append((":status", str(code)))

        # iterates over the complete set of raw header values to normalize
        # them and add them to the currently defined base list
        for key, value in headers.items():
            key = netius.common.header_down(key)
            if not type(value) == list: value = (value,)
            for _value in value: headers_b.append((key, _value))

        return self.send_headers(headers_b, delay = delay, callback = callback)

    def send_part(self, data, flush = False, delay = False, callback = None):
        if flush: count = self.send_data(data); self.flush(callback = callback)
        else: count = self.send_data(data, delay = delay, callback = callback)
        return count

    def send_frame(
        self,
        type = 0x01,
        flags = 0x00,
        payload = b"",
        stream = 0x00,
        delay = False,
        callback = None
    ):
        size = len(payload)
        header = struct.pack("!BHBBI", 0x00, size, type, flags, stream)
        message = header + payload
        return self.send(message, delay = delay, callback = callback)

    def send_data(
        self,
        data = b"",
        end_stream = True,
        delay = False,
        callback = None
    ):
        flags = 0x00
        if end_stream: flags |= 0x01
        return self.send_frame(
            type = netius.common.DATA,
            flags = flags,
            payload = data,
            stream = self.parser.stream, #@todo: this is not correct (must retrieve it from stream)
            delay = delay,
            callback = callback
        )

    def send_headers(
        self,
        headers = [],
        end_stream = False,
        end_headers = True,
        delay = False,
        callback = None
    ):
        flags = 0x00
        if end_stream: flags |= 0x01
        if end_headers: flags |= 0x04
        payload = self.parser.encoder.encode(headers)
        return self.send_frame(
            type = netius.common.HEADERS,
            flags = flags,
            payload = payload,
            stream = self.parser.stream, #@todo: this is not correct (must retrieve it from stream)
            delay = delay,
            callback = callback
        )

    def send_settings(
        self,
        settings = (),
        ack = False,
        delay = False,
        callback = None
    ):
        flags = 0x00
        if ack: flags |= 0x01
        buffer = []
        for ident, value in settings:
            setting_s = struct.pack("!HI", ident, value)
            buffer.append(setting_s)
        payload = b"".join(buffer)
        return self.send_frame(
            type = netius.common.SETTINGS,
            flags = flags,
            payload = payload,
            delay = delay,
            callback = callback
        )

    def on_frame(self):
        self.owner.on_frame_http2(self, self.parser)

    def on_headers(self, headers, dependency, weight):
        self.owner.on_headers_http2(self, self.parser, headers)

    def on_settings(self, settings, ack):
        self.owner.on_settings_http2(self, self.parser, settings, ack)

class HTTP2Server(http.HTTPServer):

    def get_protocols(self):
        return ["h2", "http/1.1", "http/1.0"]

    def new_connection(self, socket, address, ssl = False):
        return HTTP2Connection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding
        )

    def on_preface_http2(self, connection, parser):
        pass

    def on_frame_http2(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_frame(connection, parser)

    def on_settings_http2(self, connection, parser, settings, ack):
        if ack: return
        connection.send_settings(ack = True)

    def on_headers_http2(self, connection, parser, headers):
        self.on_data_http(connection, parser) #@todo this is forced as the request may not be complete (NOT VALID FOR POST)

    def _log_frame(self, connection, parser):
        self.debug("Received frame 0x%02x with length %d bytes" % (parser.type, parser.length))
