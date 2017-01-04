#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct
import tempfile
import contextlib

import netius

from . import http
from . import util
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

PROTOCOL_ERROR = 0x01
INTERNAL_ERROR = 0x02
FLOW_CONTROL_ERROR = 0x03
SETTINGS_TIMEOUT = 0x04
STREAM_CLOSED = 0x05
FRAME_SIZE_ERROR = 0x06
REFUSED_STREAM = 0x07
CANCEL = 0x08
COMPRESSION_ERROR = 0x09
CONNECT_ERROR = 0x0a
ENHANCE_YOUR_CALM = 0x0b
INADEQUATE_SECURITY = 0x0c
HTTP_1_1_REQUIRED = 0x0d

SETTINGS_HEADER_TABLE_SIZE = 0x01
SETTINGS_ENABLE_PUSH = 0x02
SETTINGS_MAX_CONCURRENT_STREAMS = 0x03
SETTINGS_INITIAL_WINDOW_SIZE = 0x04
SETTINGS_MAX_FRAME_SIZE = 0x05
SETTINGS_MAX_HEADER_LIST_SIZE = 0x06

HTTP_20 = 4
""" The newly created version of the protocol, note that
this constant value should be created in away that its value
is superior to the ones defined for previous versions """

HEADER_STATE = 1
""" The initial header state for which the header
of the frame is going to be parsed and loaded """

PAYLOAD_STATE = 2
""" The second state of the frame parsing where the
payload of the frame is going to be loaded """

FINISH_STATE = 3
""" The final finish state to be used when the parsing
of the frame has been finished """

HTTP2_WINDOW = 65535
""" The default/initial size of the window used for the
flow control of both connections and streams """

HTTP2_FRAME_SIZE = 16384
""" The base default value for the maximum size allowed
from the frame, this includes the header value """

HTTP2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
""" The preface string to be sent by the client upon
the establishment of the connection """

HTTP2_PSEUDO = (":method", ":scheme", ":path", ":authority", ":status")
""" The complete set of HTTP 2 based pseudo-header values
this list should be inclusive and limited """

HTTP2_TUPLES = (
    (SETTINGS_HEADER_TABLE_SIZE, "SETTINGS_HEADER_TABLE_SIZE"),
    (SETTINGS_ENABLE_PUSH, "SETTINGS_ENABLE_PUSH"),
    (SETTINGS_MAX_CONCURRENT_STREAMS, "SETTINGS_MAX_CONCURRENT_STREAMS"),
    (SETTINGS_INITIAL_WINDOW_SIZE, "SETTINGS_INITIAL_WINDOW_SIZE"),
    (SETTINGS_MAX_FRAME_SIZE, "SETTINGS_MAX_FRAME_SIZE"),
    (SETTINGS_MAX_HEADER_LIST_SIZE, "SETTINGS_MAX_HEADER_LIST_SIZE")
)
""" The sequence of tuple that associate the constant value of the
setting with the proper string representation for it """

HTTP2_NAMES = {
    DATA : "DATA",
    HEADERS : "HEADERS",
    PRIORITY : "PRIORITY",
    RST_STREAM : "RST_STREAM",
    SETTINGS : "SETTINGS",
    PUSH_PROMISE : "PUSH_PROMISE",
    PING : "PING",
    GOAWAY : "GOAWAY",
    WINDOW_UPDATE : "WINDOW_UPDATE",
    CONTINUATION : "CONTINUATION"
}
""" The association between the various types of frames
described as integers and their representation as strings """

HTTP2_SETTINGS = {
    SETTINGS_HEADER_TABLE_SIZE : 4096,
    SETTINGS_ENABLE_PUSH : 1,
    SETTINGS_MAX_CONCURRENT_STREAMS : 128,
    SETTINGS_INITIAL_WINDOW_SIZE : 65535,
    SETTINGS_MAX_FRAME_SIZE : 16384,
    SETTINGS_MAX_HEADER_LIST_SIZE : 16384
}
""" The default values to be used for settings of a newly
created connection, this should be defined according to specification """

HTTP2_SETTINGS_OPTIMAL = {
    SETTINGS_HEADER_TABLE_SIZE : 4096,
    SETTINGS_MAX_CONCURRENT_STREAMS : 512,
    SETTINGS_INITIAL_WINDOW_SIZE : 1048576,
    SETTINGS_MAX_FRAME_SIZE : 131072,
    SETTINGS_MAX_HEADER_LIST_SIZE : 16384
}
""" The optimal settings meant to be used by an infra-structure
deployed in a production environment """

HTTP2_SETTINGS_T = netius.legacy.items(HTTP2_SETTINGS)
""" The tuple sequence version of the settings defaults """

HTTP2_SETTINGS_OPTIMAL_T = netius.legacy.items(HTTP2_SETTINGS_OPTIMAL)
""" The tuple sequence version of the settings optimal """

class HTTP2Parser(parser.Parser):

    FIELDS = (
        "_pid",
        "store",
        "file_limit",
        "state",
        "keep_alive",
        "length",
        "type",
        "flags",
        "stream",
        "end_headers",
        "last_type",
        "last_stream",
        "last_end_headers"
    )

    def __init__(
        self,
        owner,
        store = False,
        file_limit = http.FILE_LIMIT
    ):
        parser.Parser.__init__(self, owner)

        self.build()
        self.reset(
            store = store,
            file_limit = file_limit
        )

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        self.connection = self.owner

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

        self.streams = {}
        self._max_stream = 0
        self._encoder = None
        self._decoder = None

    def destroy(self):
        """
        Destroys the current structure for the parser meaning that
        it's restored to the original values, this method should only
        be called on situation where no more parser usage is required.
        """

        parser.Parser.destroy(self)

        # iterates over the complete set of associated streams to close
        # them as the parser is now going to be destroyed and they cannot
        # be reached any longer (invalidated state)
        streams = netius.legacy.values(self.streams)
        for stream in streams: stream.close()

        self.connection = None
        self.states = ()
        self.state_l = 0
        self.parsers = ()
        self.streams = {}
        self._max_stream = 0
        self._encoder = None
        self._decoder = None

    def info_dict(self):
        info = parser.Parser.info_dict(self)
        info.update(
            streams = self.info_streams()
        )
        return info

    def info_streams(self):
        info = []
        keys = netius.legacy.keys(self.streams)
        keys.sort()
        for stream in keys:
            stream = self.streams[stream]
            item = stream.info_dict()
            info.append(item)
        return info

    def reset(
        self,
        store = False,
        file_limit = http.FILE_LIMIT
    ):
        self.store = store
        self.file_limit = file_limit
        self.state = HEADER_STATE
        self.buffer = []
        self.keep_alive = True
        self.payload = None
        self.length = 0
        self.type = 0
        self.flags = 0
        self.stream = 0
        self.stream_o = None
        self.end_headers = False
        self.last_type = 0
        self.last_stream = 0
        self.last_end_headers = False

    def clear(self, force = False, save = True):
        if not force and self.state == HEADER_STATE: return
        type = self.type
        stream = self.stream
        end_headers = self.end_headers
        self.reset(
            store = self.store,
            file_limit = self.file_limit
        )
        if not save: return
        self.last_type = type
        self.last_stream = stream
        self.last_end_headers = end_headers

    def close(self):
        pass

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
                if count == -1: break
                if count == 0: continue

                size -= count
                data = data[count:]

                continue

            elif self.state == FINISH_STATE:
                self.clear()

                continue

            else:
                raise netius.ParserError("Invalid state '%d'" % self.state)

        # in case not all of the data has been processed
        # must add it to the buffer so that it may be used
        # latter in the next parsing of the message
        if size > 0: self.buffer.append(data)

        # returns the number of read (processed) bytes of the
        # data that has been sent to the parser
        return size_o - size

    def get_type_s(self, type):
        """
        Retrieves the string based representation of the frame
        type according to the HTTP2 specification.

        :type type: int
        :param type: The frame type as an integer that is going
        to be converted to the string representation.
        :rtype: String
        :return: The string based representation of the frame type.
        """

        return HTTP2_NAMES.get(type, None)

    def assert_header(self):
        """
        Runs a series of assertion operations related with the
        header of the frame, making sure it remains compliant
        with the HTTP 2 specification.
        """

        if self.length > self.owner.settings[SETTINGS_MAX_FRAME_SIZE]:
            raise netius.ParserError(
                "Headers are greater than SETTINGS_MAX_FRAME_SIZE",
                stream = self.stream,
                error_code = FRAME_SIZE_ERROR
            )
        if self.last_type in (HEADERS, CONTINUATION) and not\
            self.last_end_headers and not self.last_stream == self.stream:
            raise netius.ParserError(
                "Cannot send frame from a different stream in middle of headers",
                error_code = PROTOCOL_ERROR
            )

    def assert_stream(self, stream):
        if not stream.identifier % 2 == 1:
            raise netius.ParserError(
                "Stream identifiers must be odd",
                error_code = PROTOCOL_ERROR
            )
        if stream.dependency == stream.identifier:
            raise netius.ParserError(
                "Stream cannot depend on itself",
                error_code = PROTOCOL_ERROR
            )
        if len(self.streams) >= self.owner.settings[SETTINGS_MAX_CONCURRENT_STREAMS]:
            raise netius.ParserError(
                "Too many streams (greater than SETTINGS_MAX_CONCURRENT_STREAMS)",
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )

    def assert_data(self, stream, end_stream):
        if self.stream == 0x00:
            raise netius.ParserError(
                "Stream cannot be set to 0x00 for DATA",
                error_code = PROTOCOL_ERROR
            )
        if not stream.end_headers:
            raise netius.ParserError(
                "Not ready to receive DATA open",
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )
        if stream.end_stream and stream.end_headers:
            raise netius.ParserError(
                "Not ready to receive DATA half closed (remote)",
                stream = self.stream,
                error_code = STREAM_CLOSED
            )

    def assert_headers(self, stream, end_stream):
        if stream.end_stream and stream.end_headers:
            raise netius.ParserError(
                "Not ready to receive HEADERS half closed (remote)",
                stream = self.stream,
                error_code = STREAM_CLOSED
            )
        if not end_stream:
            raise netius.ParserError(
                "Second HEADERS without END_STREAM flag",
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )

    def assert_priority(self, stream, dependency):
        if self.stream == 0x00:
            raise netius.ParserError(
                "Stream cannot be set to 0x00 for PRIORITY",
                error_code = PROTOCOL_ERROR
            )
        if dependency == self.stream:
            raise netius.ParserError(
                "Stream cannot depend on current stream",
                error_code = PROTOCOL_ERROR
            )
        if stream and dependency == stream.identifier:
            raise netius.ParserError(
                "Stream cannot depend on itself",
                error_code = PROTOCOL_ERROR
            )

    def assert_rst_stream(self, stream):
        if self.stream == 0x00:
            raise netius.ParserError(
                "Stream cannot be set to 0x00 for RST_STREAM",
                error_code = PROTOCOL_ERROR
            )
        if self.stream > self._max_stream:
            raise netius.ParserError(
                "Stream has not been created for RST_STREAM",
                error_code = PROTOCOL_ERROR
            )

    def assert_settings(self, settings, ack, extended = True):
        if not self.stream == 0x00:
            raise netius.ParserError(
                "Stream must be set to 0x00 for SETTINGS",
                error_code = PROTOCOL_ERROR
            )
        if ack and not self.length == 0:
            raise netius.ParserError(
                "SETTINGS with ACK must be zero length",
                error_code = FRAME_SIZE_ERROR
            )
        if not self.length % 6 == 0:
            raise netius.ParserError(
                "Size of SETTINGS frame must be a multiple of 6",
                error_code = FRAME_SIZE_ERROR
            )
        if not extended: return
        settings = dict(settings)
        if not settings.get(SETTINGS_ENABLE_PUSH, 0) in (0, 1):
            raise netius.ParserError(
                "Value of SETTINGS_ENABLE_PUSH different from 0 or 1",
                error_code = PROTOCOL_ERROR
            )
        if settings.get(SETTINGS_INITIAL_WINDOW_SIZE, 0) > 2147483647:
            raise netius.ParserError(
                "Value of SETTINGS_INITIAL_WINDOW_SIZE too large",
                error_code = FLOW_CONTROL_ERROR
            )
        if settings.get(SETTINGS_MAX_FRAME_SIZE, 16384) < 16384:
            raise netius.ParserError(
                "Value of SETTINGS_MAX_FRAME_SIZE too small",
                error_code = PROTOCOL_ERROR
            )
        if settings.get(SETTINGS_MAX_FRAME_SIZE, 16384) > 16777215:
            raise netius.ParserError(
                "Value of SETTINGS_MAX_FRAME_SIZE too large",
                error_code = PROTOCOL_ERROR
            )

    def assert_push_promise(self, promised_stream):
        raise netius.ParserError(
            "PUSH_PROMISE not allowed for server",
            error_code = PROTOCOL_ERROR
        )

    def assert_ping(self):
        if not self.stream == 0x00:
            raise netius.ParserError(
                "Stream must be set to 0x00 for PING",
                error_code = PROTOCOL_ERROR
            )
        if not self.length == 8:
            raise netius.ParserError(
                "Size of PING frame must be 8",
                error_code = FRAME_SIZE_ERROR
            )

    def assert_goaway(self):
        if not self.stream == 0x00:
            raise netius.ParserError(
                "Stream must be set to 0x00 for GOAWAY",
                error_code = PROTOCOL_ERROR
            )

    def assert_window_update(self, stream, increment):
        if increment == 0:
            raise netius.ParserError(
                "WINDOW_UPDATE increment must not be zero",
                error_code = PROTOCOL_ERROR
            )
        if self.owner.window + increment > 2147483647:
            raise netius.ParserError(
                "Window value for the connection too large",
                error_code = FLOW_CONTROL_ERROR
            )
        if stream and stream.window + increment > 2147483647:
            raise netius.ParserError(
                "Window value for the stream too large",
                error_code = FLOW_CONTROL_ERROR
            )

    def assert_continuation(self, stream):
        if stream.end_stream and stream.end_headers:
            raise netius.ParserError(
                "Not ready to receive CONTINUATION half closed (remote)",
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )
        if not self.last_type in (HEADERS, PUSH_PROMISE, CONTINUATION):
            raise netius.ParserError(
                "CONTINUATION without HEADERS, PUSH_PROMISE or CONTINUATION before",
                error_code = PROTOCOL_ERROR
            )

    @property
    def type_s(self):
        return self.get_type_s(self.type)

    def _parse_header(self, data):
        if len(data) + self.buffer_size < HEADER_SIZE: return -1

        size = HEADER_SIZE - self.buffer_size
        data = self.buffer_data + data[:size]

        header = struct.unpack("!BHBBI", data)
        extra, self.length, self.type, self.flags, self.stream = header
        self.length += extra << 16

        self.assert_header()

        self.state = PAYLOAD_STATE
        self.trigger("on_header", header)

        return size

    def _parse_payload(self, data):
        if len(data) + self.buffer_size < self.length: return -1

        size = self.length - self.buffer_size
        data = self.buffer_data + data[:size]

        valid_type = self.type < len(self.parsers)
        if not valid_type: self._invalid_type()

        self.payload = data
        self.trigger("on_payload")

        parse_method = self.parsers[self.type]
        parse_method(data)

        self.state = FINISH_STATE
        self.trigger("on_frame")

        return size

    def _parse_data(self, data):
        data_l = len(data)

        end_stream = True if self.flags & 0x01 else False
        padded = self.flags & 0x08

        index = 0
        padded_l = 0

        if padded:
            padded_l, = struct.unpack("!B", data[index:index + 1])
            index += 1

        contents = data[index:data_l - padded_l]

        stream = self._get_stream(self.stream)
        self.assert_data(stream, end_stream)

        stream.extend_data(contents)
        stream.end_stream = end_stream

        self.trigger("on_data_h2", stream, contents)

        self.trigger("on_partial", contents)
        if stream.is_ready: self.trigger("on_data")

    def _parse_headers(self, data):
        data_l = len(data)

        end_stream = True if self.flags & 0x01 else False
        end_headers = True if self.flags & 0x04 else False
        padded = self.flags & 0x08
        priority = self.flags & 0x20

        index = 0
        padded_l = 0
        dependency = 0
        weight = 0
        exclusive = 0

        if padded:
            padded_l, = struct.unpack("!B", data[index:index + 1])
            index += 1

        if priority:
            dependency, weight = struct.unpack("!IB", data[index:index + 5])
            exclusive = True if dependency & 0x80000000 else False
            dependency = dependency & 0x7fffffff
            index += 5

        # retrieves the (headers) fragment part of the payload, this is
        # going to be used as the basis for the header decoding
        fragment = data[index:data_l - padded_l]

        # retrieves the value of the window initial size from the owner
        # connection this is the value to be set in the new stream and
        # then retrieves the (maximum) frame size allowed to be passed
        # to the new stream instance for proper data frame fragmentation
        # these values are associated with the remote peer settings
        window = self.owner.settings_r[SETTINGS_INITIAL_WINDOW_SIZE]
        frame_size = self.owner.settings_r[SETTINGS_MAX_FRAME_SIZE]

        # tries to retrieve a previously opened stream and, this may be
        # the case it has been opened by a previous frame operation
        stream = self._get_stream(self.stream, strict = False, closed_s = True)

        if stream:
            # runs the headers assertion operation and then updated the
            # various elements in the currently opened stream accordingly
            self.assert_headers(stream, end_stream)
            stream.extend_headers(fragment)
            if dependency: stream.dependency = dependency
            if weight: stream.weight = weight
            if exclusive: stream.exclusive = exclusive
            if end_headers: stream.end_headers = end_headers
            if end_stream: stream.end_stream = end_stream
        else:
            # constructs the stream structure for the current stream that
            # is being open/created using the current owner, headers and
            # other information as the basis for such construction
            stream = HTTP2Stream(
                owner = self,
                identifier = self.stream,
                header_b = fragment,
                dependency = dependency,
                weight = weight,
                exclusive = exclusive,
                end_headers = end_headers,
                end_stream = end_stream,
                store = self.store,
                file_limit = self.file_limit,
                window = window,
                frame_size = frame_size
            )

            # ensures that the stream object is properly open, this should
            # enable to stream to start performing operations
            stream.open()

        # updates the current parser value for the end headers flag
        # this is going to be used to determine if the current state
        # of the connection is (loading/parsing) headers
        self.end_headers = end_headers

        # runs the assertion for the new stream that has been created
        # it must be correctly validation for some of its values
        self.assert_stream(stream)

        # sets the stream under the current parser meaning that it can
        # be latter retrieved for proper event propagation
        self._set_stream(stream)

        self.trigger("on_headers_h2", stream)

        if stream.end_headers: stream._calculate()
        if stream.end_headers: self.trigger("on_headers")
        if stream.is_ready: self.trigger("on_data")

    def _parse_priority(self, data):
        dependency, weight = struct.unpack("!IB", data)
        stream = self._get_stream(self.stream, strict = False)
        if stream:
            stream.dependency = dependency
            stream.weight = weight
        self.assert_priority(stream, dependency)
        self.trigger("on_priority", stream, dependency, weight)

    def _parse_rst_stream(self, data):
        error_code, = struct.unpack("!I", data)
        stream = self._get_stream(self.stream, strict = False)
        self.assert_rst_stream(stream)
        self.trigger("on_rst_stream", stream, error_code)

    def _parse_settings(self, data):
        settings = []
        count = self.length // SETTING_SIZE

        ack = self.flags & 0x01

        for index in netius.legacy.xrange(count):
            base = index * SETTING_SIZE
            part = data[base:base + SETTING_SIZE]
            setting = struct.unpack("!HI", part)
            settings.append(setting)

        self.assert_settings(settings, ack)

        self.trigger("on_settings", settings, ack)

    def _parse_push_promise(self, data):
        data_l = len(data)

        end_headers = True if self.flags & 0x04 else False
        padded = self.flags & 0x08

        index = 0
        padded_l = 0

        if padded:
            padded_l, = struct.unpack("!B", data[index:index + 1])
            index += 1

        promised_stream, = struct.unpack("!I", data[index:index + 4])

        fragment = data[index:data_l - padded_l]

        self.assert_push_promise(promised_stream)

        self.trigger("on_push_promise", promised_stream, fragment, end_headers)

    def _parse_ping(self, data):
        ack = self.flags & 0x01
        self.assert_ping()
        self.trigger("on_ping", data, ack)

    def _parse_goaway(self, data):
        last_stream, error_code = struct.unpack("!II", data[:8])
        extra = data[8:]
        self.assert_goaway()
        self.trigger("on_goaway", last_stream, error_code, extra)

    def _parse_window_update(self, data):
        increment, = struct.unpack("!I", data)
        stream = self._get_stream(
            self.stream,
            strict = False,
            unopened_s = True
        )
        self.assert_window_update(stream, increment)
        if self.stream and not stream: return
        self.trigger("on_window_update", stream, increment)

    def _parse_continuation(self, data):
        end_headers = True if self.flags & 0x04 else False

        stream = self._get_stream(self.stream)
        self.assert_continuation(stream)

        stream.extend_headers(data)
        stream.end_headers = end_headers
        self.end_headers = end_headers

        stream.decode_headers()

        self.trigger("on_continuation", stream)

        if stream.end_headers: stream._calculate()
        if stream.end_headers: self.trigger("on_headers")
        if stream.end_headers and stream.end_stream:
            self.trigger("on_data")

    def _has_stream(self, stream):
        return stream in self.streams

    def _get_stream(
        self,
        stream = None,
        default = None,
        strict = True,
        closed_s = False,
        unopened_s = False,
        exists_s = False
    ):
        if stream == None: stream = self.stream
        if stream == 0: return default
        if strict: closed_s = True; unopened_s = True; exists_s = True
        exists = stream in self.streams
        if closed_s and not exists and stream <= self._max_stream:
            raise netius.ParserError(
                "Invalid or closed stream '%d'" % stream,
                stream = self.stream,
                error_code = STREAM_CLOSED
            )
        if unopened_s and not exists and stream > self._max_stream:
            raise netius.ParserError(
                "Invalid or unopened stream '%d'" % stream,
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )
        if exists_s and not exists:
            raise netius.ParserError(
                "Invalid stream '%d'" % stream,
                stream = self.stream,
                error_code = PROTOCOL_ERROR
            )
        self.stream_o = self.streams.get(stream, default)
        return self.stream_o

    def _set_stream(self, stream):
        self.streams[stream.identifier] = stream
        self.stream_o = stream
        self._max_stream = max(self._max_stream, stream.identifier)

    def _del_stream(self, stream):
        if not stream in self.streams: return
        del self.streams[stream]
        self.stream_o = None

    def _invalid_type(self):
        ignore = False if self.last_type == HEADERS else True
        if ignore: raise netius.ParserError("Invalid frame type", ignore = True)
        raise netius.ParserError("Invalid frame type", error_code = PROTOCOL_ERROR)

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

class HTTP2Stream(netius.Stream):
    """
    Object representing a stream of data interchanged between two
    peers under the HTTP 2 protocol.

    A stream may be considered a node in a tree of dependencies,
    the children references are stored on the parent node.

    Should be compatible with both the parser and the connection
    interfaces and may be used for both types of operations.

    :see: https://tools.ietf.org/html/rfc7540
    """

    def __init__(
        self,
        identifier = None,
        header_b = None,
        dependency = 0x00,
        weight = 1,
        exclusive = False,
        end_headers = False,
        end_stream = False,
        end_stream_l = False,
        store = False,
        file_limit = http.FILE_LIMIT,
        window = HTTP2_WINDOW,
        frame_size = HTTP2_FRAME_SIZE,
        *args,
        **kwargs
    ):
        netius.Stream.__init__(self, *args, **kwargs)
        self.identifier = identifier
        self.header_b = [header_b]
        self.dependency = dependency
        self.weight = weight
        self.exclusive = exclusive
        self.end_headers = end_headers
        self.end_stream = end_stream
        self.end_stream_l = end_stream_l
        self.reset(
            store = store,
            file_limit = file_limit,
            window = window,
            frame_size = frame_size
        )

    def __getattr__(self, name):
        if hasattr(self.connection, name):
            return getattr(self.connection, name)
        raise AttributeError("'%s' not found" % name)

    def reset(
        self,
        store = False,
        file_limit = http.FILE_LIMIT,
        window = HTTP2_WINDOW,
        frame_size = HTTP2_FRAME_SIZE
    ):
        netius.Stream.reset(self)
        self.store = store
        self.file_limit = file_limit
        self.window = window
        self.window_m = min(self.window, frame_size - HEADER_SIZE)
        self.window_o = self.connection.window_o
        self.window_l = self.window_o
        self.window_t = self.window_o // 2
        self.pending_s = 0
        self.headers = None
        self.headers_l = None
        self.method = None
        self.path_s = None
        self.version = HTTP_20
        self.version_s = "HTTP/2.0"
        self.encodings = None
        self.chunked = False
        self.keep_alive = True
        self.content_l = -1
        self.frames = 0
        self._available = True
        self._data_b = None
        self._data_l = -1

    def open(self):
        # check if the current stream is currently in (already) in
        # the open state and if that's the case returns immediately
        if self.status == netius.OPEN: return

        # calls the parent open operation for upper operations, this
        # should take care of some callback calling
        netius.Stream.open(self)

        # runs the decoding of the headers, note that this is just a
        # try-out operation and may fail if the complete set of header
        # data is not currently available (continuation frames pending)
        self.decode_headers()

    def close(self, flush = False, destroy = True, reset = True):
        # verifies if the current stream is already closed and
        # if that's the case returns immediately, avoiding duplicate
        if self.status == netius.CLOSED: return

        # in case the reset flag is set sends the final, tries to determine
        # the way of reseting the stream, in case the flush flag is set
        # (meaning that a less strict closing is requested) and the current
        # stream is considered ready for request handling the stream reset
        # operation consists of a final chunk sending, otherwise (in case no
        # graceful approach is requested) the reset operation is performed
        if reset:
            graceful = flush and self.is_ready
            if graceful: self.send_part(b"")
            else: self.send_reset()

        # calls the parent close method so that the upper layer
        # instructions are correctly processed/handled
        netius.Stream.close(self)

        # verifies if a stream structure exists in the parser for
        # the provided identifier and if that's not the case returns
        # immediately otherwise removes it from the parent
        if not self.owner._has_stream(self.identifier): return
        self.owner._del_stream(self.identifier)

        # runs the reset operation in the stream clearing all of its
        # internal structures may avoid some memory leaks
        self.reset()

    def info_dict(self, full = False):
        info = netius.Stream.info_dict(self, full = full)
        info.update(
            identifier = self.identifier,
            dependency = self.dependency,
            weight = self.weight,
            exclusive = self.exclusive,
            end_headers = self.end_headers,
            end_stream = self.end_stream,
            end_stream_l = self.end_stream_l,
            store = self.store,
            file_limit = self.file_limit,
            window = self.window,
            window_m = self.window_m,
            window_o = self.window_o,
            window_l = self.window_l,
            window_t = self.window_t,
            pending_s = self.pending_s,
            headers = self.headers,
            method = self.method,
            path_s = self.path_s,
            version = self.version,
            version_s = self.version_s,
            encodings = self.encodings,
            chunked = self.chunked,
            keep_alive = self.keep_alive,
            content_l = self.content_l,
            frames = self.frames,
            available = self.connection.available_stream(self.identifier, 1),
            exhausted = self.is_exhausted(),
            restored = self.is_restored(),
            _available = self._available
        )
        return info

    def available(self):
        """
        Method called upon the become available event triggered
        when a blocked stream becomes "unblocked" again, this is a
        level operation that is only called once.
        """

        self._available = True
        self.owner.trigger("on_available")

    def unavailable(self):
        """
        Called whenever an "unblocked" stream becomes "blocked" again
        this is called only upon the "edge" (once). After this event
        the stream should no longer send frames containing data.
        """

        self._available = False
        self.owner.trigger("on_unavailable")

    def set_encoding(self, encoding):
        self.current = encoding

    def set_uncompressed(self):
        if self.current >= http.CHUNKED_ENCODING:
            self.current = http.CHUNKED_ENCODING
        else: self.current = http.PLAIN_ENCODING

    def set_plain(self):
        self.set_encoding(http.PLAIN_ENCODING)

    def set_chunked(self):
        self.set_encoding(http.CHUNKED_ENCODING)

    def set_gzip(self):
        self.set_encoding(http.GZIP_ENCODING)

    def set_deflate(self):
        self.set_encoding(http.DEFLATE_ENCODING)

    def is_plain(self):
        return self.current == http.PLAIN_ENCODING

    def is_chunked(self):
        return self.current > http.PLAIN_ENCODING

    def is_gzip(self):
        return self.current == http.GZIP_ENCODING

    def is_deflate(self):
        return self.current == http.DEFLATE_ENCODING

    def is_compressed(self):
        return self.current > http.CHUNKED_ENCODING

    def is_uncompressed(self):
        return not self.is_compressed()

    def is_flushed(self):
        return self.current > http.PLAIN_ENCODING

    def is_measurable(self, strict = True):
        if self.is_compressed(): return False
        return True

    def is_exhausted(self):
        if self.pending_s > self.connection.max_pending: return True
        if not self._available: return True
        return False

    def is_restored(self):
        if self.pending_s > self.connection.min_pending: return False
        if not self._available: return False
        return True

    def decode_headers(self, force = False, assert_h = True):
        if not self.end_headers and not force: return
        if self.headers_l and not force: return
        if not self.header_b: return
        is_joinable = len(self.header_b) > 1
        block = b"".join(self.header_b) if is_joinable else self.header_b[0]
        self.headers_l = self.owner.decoder.decode(block)
        self.header_b = []
        if assert_h: self.assert_headers()

    def extend_headers(self, fragment):
        """
        Extends the headers data buffer with the provided
        data fragment. This method may be used for adding
        headers data coming from a continuation frame.

        :type fragment: String
        :param fragment: The data fragment to be used in
        the extension of the headers data.
        """

        self.header_b.append(fragment)

    def extend_data(self, data):
        """
        Adds a data chunk to the buffer associated with the
        stream. Note that the buffer is only populated in case
        the store flag is currently set.

        Even if the store flag is not set this method should be
        called whenever a new data chunk is received in the stream.

        :type data: String
        :param data: The data chunk to be added to the stream's
        internal buffers.
        """

        self._data_l += len(data)
        if not self.store: return
        self._data_b.write(data)

    def remote_update(self, increment):
        """
        Updates the remote window value, the remote windows is
        the window that controls the output stream of bytes and
        should represent the number of available bytes in the
        remote peer that can be immediately processed.

        :type increment: int
        :param increment: The increment in bytes to be added to
        the current remote window value, this value may be negative.
        """

        self.window += increment

    def local_update(self, increment):
        """
        Increments the current local window value with the increment
        (in bytes) passed as parameter.

        The local window represents the number of bytes that can be
        processed in the current local buffer, effectively representing
        the number of bytes that may still be received in the stream.

        In case the window threshold is reached the method triggers
        the sending of the window update frame.

        :type increment: int
        :param increment: The number of bytes that are going to be
        incremented in the local window value.
        """

        self.window_l += increment
        if self.window_l >= self.window_t: return
        self.connection.send_window_update(
            increment = self.window_o - self.window_l,
            stream = self.identifier
        )
        self.window_l = self.window_o

    def get_path(self, normalize = False):
        """
        Retrieves the path associated with the request, this
        value should be interpreted from the HTTP status line.

        In case the normalize flag is set a possible absolute
        URL value should be normalized into an absolute path.
        This may be required under some proxy related scenarios.

        :type normalize: bool
        :param normalize: If the normalization process should be
        applied for absolute URL scenarios.
        :rtype: String
        :return: The path associated with the current request.
        """

        split = self.path_s.split("?", 1)
        path = split[0]
        if not normalize: return path
        if not path.startswith(("http://", "https://")): return path
        return netius.legacy.urlparse(path).path

    def get_query(self):
        """
        Retrieves the (GET) query part of the path, this is considered
        to be the part of the path after the first question mark.

        This query string may be used to parse any possible (GET)
        arguments.

        :rtype: String
        :return: The query part of the path, to be used for parsing
        of (GET) arguments.
        """

        split = self.path_s.split("?", 1)
        if len(split) == 1: return ""
        else: return split[1]

    def get_message_b(self, copy = False, size = 40960):
        """
        Retrieves a new buffer associated with the currently
        loaded message.

        In case the current parsing operation is using a file like
        object for the handling this object it is returned instead.

        The call of this method is only considered to be safe after
        the complete message has been received and processed, otherwise
        and invalid message file structure may be created.

        Note that the returned object will always be set at the
        beginning of the file, so some care should be taken in usage.

        :type copy: bool
        :param copy: If a copy of the file object should be returned
        or if instead the shallow copy associated with the parser should
        be returned instead, this should be used carefully to avoid any
        memory leak from file descriptors.
        :type size: int
        :param size: Size (in bytes) of the buffer to be used in a possible
        copy operation between buffers.
        :rtype: File
        :return: The file like object that may be used to percolate
        over the various parts of the current message contents.
        """

        # restores the message file to the original/initial position and
        # then in case there's no copy required returns it immediately
        self._data_b.seek(0)
        if not copy: return self._data_b

        # determines if the file limit for a temporary file has been
        # surpassed and if that's the case creates a named temporary
        # file, otherwise created a memory based buffer
        use_file = self.store and self.content_l >= self.file_limit
        if use_file: message_f = tempfile.NamedTemporaryFile(mode = "w+b")
        else: message_f = netius.legacy.BytesIO()

        try:
            # iterates continuously reading the contents from the message
            # file and writing them back to the output (copy) file
            while True:
                data = self._data_b.read(size)
                if not data: break
                message_f.write(data)
        finally:
            # resets both of the message file (output and input) to the
            # original position as expected by the infra-structure
            self._data_b.seek(0)
            message_f.seek(0)

        # returns the final (copy) of the message file to the caller method
        # note that the type of this file may be an in memory or stored value
        return message_f

    def get_encodings(self):
        if not self.encodings == None: return self.encodings
        accept_encoding_s = self.headers.get("accept-encoding", "")
        self.encodings = [value.strip() for value in accept_encoding_s.split(",")]
        return self.encodings

    def fragment(self, data):
        reference = min(
            self.connection.window,
            self.window,
            self.window_m
        )
        yield data[:reference]
        data = data[reference:]
        while data:
            yield data[:self.window_m]
            data = data[self.window_m:]

    def fragmentable(self, data):
        if not data: return False
        if self.window_m == 0: return False
        if len(data) <= self.window_m and\
            len(data) <= self.window: return False
        return True

    def flush(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.flush(*args, **kwargs)

    def flush_s(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.flush_s(*args, **kwargs)

    def send_response(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.send_response(*args, **kwargs)

    def send_header(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.send_header(*args, **kwargs)

    def send_part(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.send_part(*args, **kwargs)

    def send_reset(self, *args, **kwargs):
        if not self.is_open(): return 0
        with self.ctx_request(args, kwargs):
            return self.connection.send_rst_stream(*args, **kwargs)

    def assert_headers(self):
        pseudo = True
        pseudos = dict()
        for name, value in self.headers_l:
            is_pseudo = name.startswith(":")
            if not is_pseudo: pseudo = False
            if not name.lower() == name:
                raise netius.ParserError(
                    "Headers must be lower cased",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if name in (":status",):
                raise netius.ParserError(
                    "Response pseudo-header present",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if name in ("connection",):
                raise netius.ParserError(
                    "Invalid header present",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if name == "te" and not value == "trailers":
                raise netius.ParserError(
                    "Invalid value for TE header",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if is_pseudo and name in pseudos:
                raise netius.ParserError(
                    "Duplicated pseudo-header value",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if pseudo and not name in HTTP2_PSEUDO:
                raise netius.ParserError(
                    "Invalid pseudo-header",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if not pseudo and is_pseudo:
                raise netius.ParserError(
                    "Pseudo-header positioned after normal header",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )
            if is_pseudo: pseudos[name] = True

        for name in (":method", ":scheme", ":path"):
            if not name in pseudos:
                raise netius.ParserError(
                    "Missing pseudo-header in request",
                    stream = self.identifier,
                    error_code = PROTOCOL_ERROR
                )

    def assert_ready(self):
        if not self.content_l == -1 and not self._data_l == 0 and\
            not self._data_l == self.content_l:
            raise netius.ParserError(
                "Invalid content-length header value (missmatch)",
                stream = self.identifier,
                error_code = PROTOCOL_ERROR
            )

    @contextlib.contextmanager
    def ctx_request(self, args = None, kwargs = None):
        # in case there's no valid set of keyword arguments
        # a valid and empty one must be created (avoids error)
        if kwargs == None: kwargs = dict()

        # sets the stream keyword argument with the current
        # stream's identifier (provides identification support)
        kwargs["stream"] = self.identifier

        # tries to retrieves a possible callback (method) value
        # and in case it exits uses it to create a new one that
        # calls this one at the end (connection to stream clojure)
        callback = kwargs.get("callback", None)
        if callback: kwargs["callback"] = self._build_c(callback)

        # retrieves the references to the "original"
        # values of the current and stream objects
        current = self.connection.current
        stream_o = self.owner.stream_o

        # replaces the values of the current (encoding)
        # and stream object with the stream based ones
        self.connection.current = self.current
        self.owner.stream_o = self

        try:
            # runs the yield operation meaning that
            # the concrete operation will be performed
            # at this point
            yield
        finally:
            # restores both the stream object and the current
            # values to the original state (before context)
            self.owner.stream_o = stream_o
            self.connection.current = current

    @property
    def parser(self):
        return self

    @property
    def is_ready(self, calculate = True, assert_r = True):
        """
        Determines if the stream is ready, meaning that the complete
        set of headers and data have been passed to peer and the request
        is ready to be passed to underlying layers for processing.

        :type calculate: bool
        :param calculate: If the calculus of the content length should be
        taken into consideration meaning that the content/data length should
        be ensured to be calculated.
        :type assert_r: bool
        :param assert_r: If the extra assert (ready) operation should be
        performed to ensure that proper data values are defined in the request.
        :rtype: bool
        :return: The final value on the is ready (for processing).
        """

        if not self.is_open(): return False
        if calculate: self._calculate()
        if not self.end_headers: return False
        if not self.end_stream: return False
        if assert_r: self.assert_ready()
        return True

    @property
    def is_headers(self):
        return self.end_headers

    def _calculate(self):
        if not self._data_b == None: return
        if not self._data_l == -1: return
        if not self.is_headers: return
        self._calculate_headers()
        self.content_l = self.headers.get("content-length", -1)
        self.content_l = self.content_l and int(self.content_l)
        self._data_b = self._build_b()
        self._data_l = 0

    def _calculate_headers(self):
        util.verify(self.is_headers)
        util.verify(self.headers == None)

        headers_m = dict()
        headers_s = dict()

        for header in self.headers_l:
            key, value = header
            if not type(key) == str: key = str(key)
            if not type(value) == str: value = str(value)
            is_special = key.startswith(":")
            exists = key in headers_m
            if exists:
                sequence = headers_m[key]
                is_list = type(sequence) == list
                if not is_list: sequence = [sequence]
                sequence.append(value)
                value = sequence
            if is_special: headers_s[key] = value
            else: headers_m[key] = value

        host = headers_s.get(":authority", None)
        if host: headers_m["host"] = host

        self.headers = headers_m
        self.method = headers_s.get(":method", None)
        self.path_s = headers_s.get(":path", None)
        if self.method: self.method = str(self.method)
        if self.path_s: self.path_s = str(self.path_s)

    def _build_b(self):
        """
        Builds the buffer object (compliant with file spec) that is
        going to be used to store the message payload for the HTTP
        request.

        Note that in case the file limit value is exceeded a file system
        based temporary file is used.

        :rtype: File
        :return: A file compliant object to be used to store the
        message payload for the HTTP request.
        """

        use_file = self.store and self.content_l >= self.file_limit
        if use_file: return tempfile.NamedTemporaryFile(mode = "w+b")
        else: return netius.legacy.BytesIO()

    def _build_c(self, callback, validate = True):
        """
        Builds the final callback function to be used with a clojure
        around the current stream for proper validation and passing
        of the stream as connection parameter (context).

        :type callback: Function
        :param callback: The function to be used as the basis for the
        callback and for which a clojure is going to be applied.
        :type validate: bool
        :param validate: If stream open validation should be applied
        for the calling of the callback, the idea is that is a stream
        is already closed the callback should not be called.
        :rtype: Function
        :return: The final clojure function that may be used safely for
        callback with proper stream context.
        """

        def inner(connection):
            if validate and not self.is_open(): return
            callback(self)

        return inner
