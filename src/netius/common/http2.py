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

import netius

from . import parser

HEADER_SIZE = 9

SETTING_SIZE = 6

DATA = 0x00
HEADERS = 0x01
PRIORITY = 0x02
RST_STREAM = 0x03
SETTINGS = 0x04
PUSH_PROMISE = 0x05
PING = 0x06
GOAWAY = 0x07
WINDOW_UPDATE = 0x08
CONTINUATION = 0x09

HEADER_STATE = 1
""" The initial header state for which the header
of the frame is going to be parsed and loaded """

PAYLOAD_STATE = 2
""" The second state of the frame parsing where the
payload of the frame is going to be loaded """

FINISH_STATE = 3
""" The final finish state to be used when the parsing
of the frame has been finished """

class HTTP2Parser(parser.Parser):

    def __init__(self, owner):
        parser.Parser.__init__(self, owner)

        self.keep_alive = True
        self.version_s = "HTTP/2.0"

        self.build()
        self.reset()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        self.states = (
            self._parse_header,
            self._parse_payload
        )
        self.state_l = len(self.states)

        self.parsers = (
            self._parse_data,
            self._parse_headers,
            self._parse_priority,
            self._parse_rst_stream,
            self._parse_settings,
            self._parse_push_promise,
            self._parse_ping,
            self._parse_goaway,
            self._parse_window_update,
            self._parse_continuation
        )

        self._encoder = None
        self._decoder = None

    def destroy(self):
        """
        Destroys the current structure for the parser meaning that
        it's restored to the original values, this method should only
        be called on situation where no more parser usage is required.
        """

        parser.Parser.destroy(self)

        self.states = ()
        self.state_l = 0
        self.parsers = ()
        self._encoder = None
        self._decoder = None

    def reset(self):
        self.state = HEADER_STATE
        self.buffer = []
        self.length = 0
        self.type = 0
        self.flags = 0
        self.stream = 0

    def clear(self, force = False):
        if not force and self.state == HEADER_STATE: return
        self.reset()

    def get_path(self):
        split = self.path_s.split("?", 1)
        return split[0]

    def get_query(self):
        split = self.path_s.split("?", 1)
        if len(split) == 1: return ""
        else: return split[1]

    def parse(self, data):
        """
        Parses the provided data chunk, changing the current
        state of the parser accordingly and returning the
        number of processed bytes from it.

        :type data: String
        :param data: The string containing the data to be parsed
        in the current parse operation.
        :rtype: int
        :return: The amount of bytes of the data string that have
        been "parsed" in the current parse operation.
        """

        parser.Parser.parse(self, data)

        # in case the current state of the parser is finished, must
        # reset the state to the start position as the parser is
        # re-starting (probably a new data sequence)
        if self.state == FINISH_STATE: self.clear()

        # retrieves the size of the data that has been sent for parsing
        # and saves it under the size original variable
        size = len(data)
        size_o = size

        # iterates continuously to try to process all that
        # data that has been sent for processing
        while size > 0:

            if self.state <= self.state_l:
                method = self.states[self.state - 1]
                count = method(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == FINISH_STATE:
                break

            else:
                raise netius.ParserError("Invalid state '%d'" % self.state)

        # in case not all of the data has been processed
        # must add it to the buffer so that it may be used
        # latter in the next parsing of the message
        if size > 0: self.buffer.append(data)

        # returns the number of read (processed) bytes of the
        # data that has been sent to the parser
        return size_o - size

    def _parse_header(self, data):
        if len(data) + self.buffer_size < HEADER_SIZE: return 0

        size = HEADER_SIZE - self.buffer_size
        data = self.buffer_data + data[:size]

        header = struct.unpack("!BHBBI", data)
        extra, self.length, self.type, self.flags, self.stream = header
        self.length += extra << 16

        self.state = PAYLOAD_STATE
        self.trigger("on_header", header)

        return size

    def _parse_payload(self, data):
        if len(data) + self.buffer_size < self.length: return 0

        size = self.length - self.buffer_size
        data = self.buffer_data + data[:size]

        parse_method = self.parsers[self.type]
        parse_method(data)

        self.state = FINISH_STATE
        self.trigger("on_frame")

        return size

    def _parse_data(self, data):
        data_l = len(data)

        padded = self.flags & 0x08

        index = 0
        padded_l = 0

        if padded:
            padded_l = struct.unpack("!B", data[index:index + 1])
            index += 1

        contents = data[index:data_l - padded_l]

        self.trigger("on_data", contents)

    def _parse_headers(self, data):
        data_l = len(data)

        padded = self.flags & 0x08
        priority = self.flags & 0x20

        index = 0
        padded_l = 0
        dependency = 0
        weight = 0

        if padded:
            padded_l = struct.unpack("!B", data[index:index + 1])
            index += 1

        if priority:
            dependency = struct.unpack("!I", data[index:index + 4])
            index += 4
            weight = struct.unpack("!B", data[index:index + 1])
            index += 1

        fragment = data[index:data_l - padded_l]
        headers = self.decoder.decode(fragment)

        self._set_legacy(headers)

        self.trigger("on_headers", headers, dependency, weight)

    def _parse_priority(self, data):
        pass

    def _parse_rst_stream(self, data):
        pass

    def _parse_settings(self, data):
        settings = []
        count = self.length // SETTING_SIZE

        ack = self.flags & 0x01

        for index in netius.legacy.xrange(count):
            base = index * SETTING_SIZE
            part = data[base:base + SETTING_SIZE]
            setting = struct.unpack("!HI", part)
            settings.append(setting)

        self.trigger("on_settings", settings, ack)

    def _parse_push_promise(self, data):
        pass

    def _parse_ping(self, data):
        pass

    def _parse_goaway(self, data):
        pass

    def _parse_window_update(self, data):
        pass

    def _parse_continuation(self, data):
        pass

    def _set_legacy(self, headers):
        headers_m = dict()
        headers_s = dict()

        for header in headers:
            key, value = header
            is_special = key.startswith(":")
            if is_special: headers_s[key] = value
            else: headers_m[key] = value #@todo in case there's an overlap a list must be created

        host = headers_s.get(":authority", None)
        if host: headers_m["host"] = host

        self.method = headers_s.get(":method", None)
        self.path_s = headers_s.get(":path", None)
        self.headers = headers_m

    @property
    def buffer_size(self):
        return sum(len(data) for data in self.buffer)

    @property
    def buffer_data(self, empty = True):
        data = b"".join(self.buffer)
        if empty: del self.buffer[:]
        return data

    @property
    def encoder(self):
        if self._encoder: return self._encoder
        import hpack
        self._encoder = hpack.hpack.Encoder()
        return self._encoder

    @property
    def decoder(self):
        if self._decoder: return self._decoder
        import hpack
        self._decoder = hpack.hpack.Decoder()
        return self._decoder
