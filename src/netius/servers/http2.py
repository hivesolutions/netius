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

    def __init__(self, legacy = True, *args, **kwargs):
        http.HTTPConnection.__init__(self, *args, **kwargs)
        self.legacy = legacy
        self.preface = False
        self.preface_b = b""

    def open(self, *args, **kwargs):
        http.HTTPConnection.open(self, *args, **kwargs)
        if not self.legacy: self.set_h2()

    def set_h2(self):
        self.legacy = False
        if self.parser: self.parser.destroy()
        self.parser = netius.common.HTTP2Parser(self)
        self.parser.bind("on_frame", self.on_frame)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_settings", self.on_settings)
        self.parser.bind("on_ping", self.on_ping)

    def parse(self, data):
        if not self.legacy and not self.preface:
            data = self.parse_preface(data)
            if not data: return
        return self.parser.parse(data)

    def parse_preface(self, data):
        """
        Tries to run the parsing on the preface part of the
        connection establishment using the provided data
        note that the data is buffered in case the proper size
        has not been reached for proper validation.

        This should be the first step when trying to establish
        a proper HTTP 2 connection.

        :type data: String
        :param data: The data buffer that is going to be used to
        try to parse the connection preface.
        :rtype: String
        :return: The resulting data after the preface has been
        parsed, this should be empty or invalid in case no data
        is pending to be parsed.
        """

        # adds the current data to the buffer of bytes pending
        # in the preface parsing and then verified that the proper
        # preface size has been reached, in case it has not returned
        # an invalid value immediately (no further parsing)
        self.preface_b += data
        preface_l = len(netius.common.HTTP2_PREFACE)
        is_size = len(self.preface_b) >= preface_l
        if not is_size: return None

        # retrieves the preface string from the buffer (according to size)
        # and runs the string based verification, raising an exception in
        # case there's a mismatch in the string validation
        preface = self.preface_b[:preface_l]
        if not preface == netius.common.HTTP2_PREFACE:
            raise netius.ParserError("Invalid preface")

        # sets the preface (parsed) flag indicating that the preface has
        # been parsed for the current connection
        self.preface = True

        # retrieves the extra data added to the preface buffer and then
        # unsets the same buffer (no more preface parsing)
        data = self.preface_b[preface_l:]
        self.preface_b = b""

        # calls the proper callback for the preface sending both the current
        # instance and the associated parser for handling
        self.owner.on_preface_http2(self, self.parser)

        # returns the remaining data pending to be parsed so that it may be
        # parsed by any extra operation
        return data

    def send_response(
        self,
        data = None,
        headers = None,
        version = "HTTP/2.0",
        code = 200,
        code_s = None,
        apply = False,
        final = True,
        flush = True,
        delay = False,
        callback = None
    ):
        # in case the legacy mode is enabled the send response call is
        # forwarded to the upper layers so that it's handled properly
        if self.legacy: return http.HTTPConnection.send_response(
            self,
            data = data,
            headers = headers,
            code = code,
            code_s = code_s,
            apply = apply,
            flush = flush,
            delay = delay,
            callback = callback
        )

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

        # sends the part/payload information (data) to the client and optionally
        # flushes the current internal buffers to enforce sending of the value
        count += self.send_part(
            data,
            final = final,
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
        # in case the legacy mode is enabled the send header call is
        # forwarded to the upper layers so that it's handled properly
        if self.legacy: return http.HTTPConnection.send_header(
            self,
            headers = headers,
            code = code,
            code_s = code_s,
            delay = delay,
            callback = callback
        )

        # verifies if the headers value has been provided and in case it
        # has not creates a new empty dictionary (runtime compatibility)
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

    def send_part(
        self,
        data,
        final = True,
        flush = False,
        delay = False,
        callback = None
    ):
        if self.legacy: return http.HTTPConnection.send_part(
            self,
            data,
            final = final,
            flush = flush,
            delay = delay,
            callback = callback
        )
        if flush: count = self.send_data(data, end_stream = final); self.flush(callback = callback)
        else: count = self.send_data(data, end_stream = final, delay = delay, callback = callback)
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
        stream = None,
        delay = False,
        callback = None
    ):
        flags = 0x00
        if end_stream: flags |= 0x01
        return self.send_frame(
            type = netius.common.DATA,
            flags = flags,
            payload = data,
            stream = stream or self.parser.stream,
            delay = delay,
            callback = callback
        )

    def send_headers(
        self,
        headers = [],
        end_stream = False,
        end_headers = True,
        stream = None,
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
            stream = stream or self.parser.stream,
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

    def send_ping(
        self,
        ack = False,
        delay = False,
        callback = None
    ):
        flags = 0x00
        if ack: flags |= 0x01
        payload = b"\0\0\0\0\0\0\0\0"
        return self.send_frame(
            type = netius.common.PING,
            flags = flags,
            payload = payload,
            delay = delay,
            callback = callback
        )

    def on_frame(self):
        self.owner.on_frame_http2(self, self.parser)

    def on_headers(self, headers, dependency, weight, end_stream):
        self.owner.on_headers_http2(self, self.parser, headers)

    def on_settings(self, settings, ack):
        self.owner.on_settings_http2(self, self.parser, settings, ack)

    def on_ping(self, ack):
        self.owner.on_ping_http2(self, self.parser, ack)

class HTTP2Server(http.HTTPServer):

    def __init__(self, legacy = True, safe = True, *args, **kwargs):
        self._protocols = []
        self.legacy, self.safe = legacy, safe
        http.HTTPServer.__init__(self, *args, **kwargs)

    def get_protocols(self):
        if self._protocols: return self._protocols
        if not self.safe: self._protocols.extend(["h2"])
        if self.legacy: self._protocols.extend(["http/1.1", "http/1.0"])
        return self._protocols

    def new_connection(self, socket, address, ssl = False):
        return HTTP2Connection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding,
            legacy = self.legacy
        )

    def on_ssl(self, connection):
        http.HTTPServer.on_ssl(self, connection)
        if self.safe: return
        protocol = connection.ssl_protocol()
        if not protocol == "h2": return
        connection.set_h2()

    def on_preface_http2(self, connection, parser):
        pass

    def on_frame_http2(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_frame(connection, parser)

    def on_headers_http2(self, connection, parser, headers):
        self.on_data_http(connection, parser) #@todo this is forced as the request may not be complete (NOT VALID FOR POST)

    def on_settings_http2(self, connection, parser, settings, ack):
        if ack: return
        connection.send_settings(ack = True)

    def on_ping_http2(self, connection, parser, ack):
        if ack: return
        connection.send_ping(ack = True)

    def _log_frame(self, connection, parser):
        self.debug("Received frame 0x%02x with length %d bytes" % (parser.type, parser.length))
