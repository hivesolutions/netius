#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import ssl
import struct

import netius.common

from . import http

class HTTP2Connection(http.HTTPConnection):

    def __init__(
        self,
        legacy = True,
        window = netius.common.HTTP2_WINDOW,
        settings = netius.common.HTTP2_SETTINGS_OPTIMAL,
        settings_r = netius.common.HTTP2_SETTINGS,
        *args,
        **kwargs
    ):
        http.HTTPConnection.__init__(self, *args, **kwargs)
        self.legacy = legacy
        self.settings = dict(settings)
        self.settings_r = dict(settings_r)
        self.window = window
        self.window_o = self.settings[netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE]
        self.window_l = self.window_o
        self.window_t = self.window_o // 2
        self.preface = False
        self.preface_b = b""
        self.frames = []
        self.unavailable = {}

    def open(self, *args, **kwargs):
        http.HTTPConnection.open(self, *args, **kwargs)
        if not self.is_open(): return
        if not self.legacy: self.set_h2()

    def info_dict(self, full = False):
        info = http.HTTPConnection.info_dict(self, full = full)
        info.update(
            legacy = self.legacy,
            window = self.window,
            window_o = self.window_o,
            window_l = self.window_l,
            window_t = self.window_t,
            frames = len(self.frames)
        )
        return info

    def flush_s(self, stream = None, callback = None):
        return self.send_part(
            b"",
            stream = stream,
            final = True,
            flush = True,
            callback = callback
        )

    def set_h2(self):
        self.legacy = False
        if self.parser: self.parser.destroy()
        self.parser = netius.common.HTTP2Parser(self, store = True)
        self.parser.bind("on_data", self.on_data)
        self.parser.bind("on_header", self.on_header)
        self.parser.bind("on_payload", self.on_payload)
        self.parser.bind("on_frame", self.on_frame)
        self.parser.bind("on_data_h2", self.on_data_h2)
        self.parser.bind("on_headers_h2", self.on_headers_h2)
        self.parser.bind("on_rst_stream", self.on_rst_stream)
        self.parser.bind("on_settings", self.on_settings)
        self.parser.bind("on_ping", self.on_ping)
        self.parser.bind("on_goaway", self.on_goaway)
        self.parser.bind("on_window_update", self.on_window_update)
        self.parser.bind("on_continuation", self.on_continuation)

    def parse(self, data):
        if not self.legacy and not self.preface:
            data = self.parse_preface(data)
            if not data: return
        try:
            return self.parser.parse(data)
        except netius.ParserError as error:
            if not self.legacy: raise
            self.send_response(
                code = error.code,
                apply = True
            )

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

    def send_plain(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        callback = None
    ):
        if self.legacy: return http.HTTPConnection.send_plain(
            self,
            data,
            stream = stream,
            final = final,
            delay = delay,
            callback = callback
        )

        # verifies if the data should be fragmented for the provided
        # stream and if that's not required send the required data
        # straight away with any required splitting/fragmentation of it
        if not self.fragmentable_stream(stream, data):
            return self.send_data(
                data,
                stream = stream,
                end_stream = final,
                delay = delay,
                callback = callback
            )

        # sends the same data but using a fragmented approach where the
        # data is going to be splitted according to the maximum determined
        # frame size, this is required to overcome limitations in the connection
        # that has been established with the other peer
        return self.send_fragmented(
            data,
            stream = stream,
            final = final,
            delay = delay,
            callback = callback
        )

    def send_chunked(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        callback = None
    ):
        if self.legacy: return http.HTTPConnection.send_chunked(
            self,
            data,
            stream = stream,
            final = final,
            delay = delay,
            callback = callback
        )
        return self.send_plain(
            data,
            stream = stream,
            final = final,
            delay = delay,
            callback = callback
        )

    def send_fragmented(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        callback = None
    ):
        count = 0
        fragments = self.fragment_stream(stream, data)
        fragments = list(fragments)
        fragments_l = len(fragments)

        for index in netius.legacy.xrange(fragments_l):
            is_last = index == fragments_l - 1
            fragment = fragments[index]
            if is_last:
                count += self.send_data(
                    fragment,
                    stream = stream,
                    end_stream = final,
                    delay = delay,
                    callback = callback
                )
            else:
                count += self.send_data(
                    fragment,
                    stream = stream,
                    end_stream = False,
                    delay = delay
                )

        return count

    def send_response(
        self,
        data = None,
        headers = None,
        version = None,
        code = 200,
        code_s = None,
        apply = False,
        stream = None,
        final = True,
        flush = True,
        delay = True,
        callback = None
    ):
        # in case the legacy mode is enabled the send response call is
        # forwarded to the upper layers so that it's handled properly
        if self.legacy: return http.HTTPConnection.send_response(
            self,
            data = data,
            headers = headers,
            version = version,
            code = code,
            code_s = code_s,
            apply = apply,
            stream = stream,
            final = final,
            flush = flush,
            delay = delay,
            callback = callback
        )

        # retrieves the various parts that define the response
        # and runs a series of normalization processes to retrieve
        # the relevant information of the data to be sent to client
        data = data or b""
        data = netius.legacy.bytes(data)
        headers = headers or dict()
        data_l = len(data) if data else 0
        is_empty = code in (204, 304) and data_l == 0

        # runs a series of verifications taking into account the type
        # of the method defined in the current request, for instance if
        # the current request is a HEAD one then no data is sent (as expected)
        if self.parser_ctx.method and self.parser_ctx.method.upper() == "HEAD":
            data = b""

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
            code_s = code_s,
            stream = stream
        )

        # sends the part/payload information (data) to the client and optionally
        # flushes the current internal buffers to enforce sending of the value
        count += self.send_part(
            data,
            stream = stream,
            final = final,
            flush = flush,
            delay = delay,
            callback = callback
        )
        return count

    def send_header(
        self,
        headers = None,
        version = None,
        code = 200,
        code_s = None,
        stream = None,
        final = False,
        delay = True,
        callback = None
    ):
        # in case the legacy mode is enabled the send header call is
        # forwarded to the upper layers so that it's handled properly
        if self.legacy: return http.HTTPConnection.send_header(
            self,
            headers = headers,
            version = version,
            code = code,
            code_s = code_s,
            stream = stream,
            delay = delay,
            callback = callback
        )

        # verifies if the headers value has been provided and in case it
        # has not creates a new empty dictionary (runtime compatibility)
        headers = headers or dict()

        # defines the proper default base HTTP version in case it has not
        # been provided as part the default values
        version = version or "HTTP/2.0"

        # creates the headers base list that is going to store the various
        # header tuples representing the headers in canonical http2 form
        headers_b = []
        headers_b.append((":status", str(code)))

        # iterates over the complete set of raw header values to normalize
        # them and add them to the currently defined base list
        for key, value in netius.legacy.iteritems(headers):
            key = netius.common.header_down(key)
            if key in ("connection", "transfer-encoding"): continue
            if not isinstance(value, list): value = (value,)
            for _value in value: headers_b.append((key, _value))

        # verifies if this is considered to be the final operation in the stream
        # and if that's the case creates a new callback for the closing of the
        # stream at the end of the operation, this is required for proper collection
        if final:
            old_callback = callback

            def callback(connection):
                self.close_stream(stream, final = final)
                old_callback and old_callback(connection)

        # runs the send headers operations that should send the headers list
        # to the other peer and returns the number of bytes sent
        count = self.send_headers(
            headers_b,
            end_stream = final,
            stream = stream,
            delay = delay,
            callback = callback
        )

        # "notifies" the owner of the connection that the headers have been
        # sent all the HTTP header information should be present
        self.owner.on_send_http(
            self.connection_ctx,
            self.parser_ctx,
            headers = headers,
            version = version,
            code = code,
            code_s = code_s
        )

        # returns the final number of bytes that have been sent during the current
        # operation of sending headers to the other peer
        return count

    def send_part(
        self,
        data,
        stream = None,
        final = True,
        flush = False,
        delay = True,
        callback = None
    ):
        if self.legacy: return http.HTTPConnection.send_part(
            self,
            data,
            stream = stream,
            final = final,
            flush = flush,
            delay = delay,
            callback = callback
        )

        # verifies if this is considered to be the final operation in the stream
        # and if that's the case creates a new callback for the closing of the
        # stream at the end of the operation, this is required for proper collection
        if final:
            old_callback = callback

            def callback(connection):
                self.close_stream(stream, final = final)
                old_callback and old_callback(connection)

        # verifies if the current connection/stream is flushed meaning that it requires
        # a final chunk of data to be sent to the peer, if that's not the case there's
        # no need to run the flushing as a possible empty data frame may be sent which
        # may cause errors to be raised from the server side
        flush = flush and self.is_flushed()

        if flush:
            count = self.send_base(
                data,
                stream = stream,
                final = False
            )
            self.flush(stream = stream, callback = callback)
        else:
            count = self.send_base(
                data,
                stream = stream,
                final = final,
                delay = delay,
                callback = callback
            )
        return count

    def send_frame(
        self,
        type = 0x01,
        flags = 0x00,
        payload = b"",
        stream = 0x00,
        delay = True,
        callback = None
    ):
        size = len(payload)
        size_h = size >> 16
        size_l = size & 0xffff
        header = struct.pack("!BHBBI", size_h, size_l, type, flags, stream)
        message = header + payload
        self.owner.on_send_http2(self, self.parser, type, flags, payload, stream)
        return self.send(message, delay = delay, callback = callback)

    def send_data(
        self,
        data = b"",
        end_stream = True,
        stream = None,
        delay = True,
        callback = None
    ):
        # builds the flags byte taking into account the various
        # options that have been passed to the sending of data
        flags = 0x00
        data_l = len(data)
        if end_stream: flags |= 0x01

        # builds the callback clojure so that the connection state
        # is properly updated upon the sending of data
        callback = self._build_c(callback, stream, data_l)

        # verifies if the stream is available for the amount of data
        # that is currently being sent and if that's not the case delays
        # the sending of the frame to when the stream becomes available
        if not self.available_stream(stream, data_l):
            count = self.delay_frame(
                type = netius.common.DATA,
                flags = flags,
                payload = data,
                stream = stream,
                delay = delay,
                callback = callback
            )
            self.try_unavailable(stream)
            return count

        # runs the increments remove window value, decrementing the window
        # by the size of the data being sent
        self.increment_remote(stream, data_l * -1, all = True)

        # runs the "proper" sending of the data frame, registering the callback
        # with the expected clojure
        count = self.send_frame(
            type = netius.common.DATA,
            flags = flags,
            payload = data,
            stream = stream,
            delay = delay,
            callback = callback
        )

        # runs the try unavailable method to verify if the stream did became
        # unavailable after the sending of the data
        self.try_unavailable(stream)

        # returns the final number of bytes sent to the called method, this should
        # match the value of the data length
        return count

    def send_headers(
        self,
        headers = [],
        end_stream = False,
        end_headers = True,
        stream = None,
        delay = True,
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
            stream = stream,
            delay = delay,
            callback = callback
        )

    def send_rst_stream(
        self,
        error_code = 0x00,
        stream = None,
        delay = True,
        callback = None
    ):
        payload = struct.pack("!I", error_code)
        return self.send_frame(
            type = netius.common.RST_STREAM,
            payload = payload,
            stream = stream,
            delay = delay,
            callback = callback
        )

    def send_settings(
        self,
        settings = (),
        ack = False,
        delay = True,
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
        opaque = b"\0\0\0\0\0\0\0\0",
        ack = False,
        delay = True,
        callback = None
    ):
        flags = 0x00
        if ack: flags |= 0x01
        return self.send_frame(
            type = netius.common.PING,
            flags = flags,
            payload = opaque,
            delay = delay,
            callback = callback
        )

    def send_goaway(
        self,
        last_stream = 0x00,
        error_code = 0x00,
        message = "",
        close = True,
        delay = True,
        callback = None
    ):
        if close:
            old_callback = callback

            def callback(connection):
                self.close()
                old_callback and old_callback(connection)

        message = netius.legacy.bytes(message)
        payload = struct.pack("!II", last_stream, error_code)
        payload += message
        return self.send_frame(
            type = netius.common.GOAWAY,
            payload = payload,
            delay = delay,
            callback = callback
        )

    def send_window_update(
        self,
        increment = 0,
        stream = None,
        delay = True,
        callback = None
    ):
        payload = struct.pack("!I", increment)
        return self.send_frame(
            type = netius.common.WINDOW_UPDATE,
            payload = payload,
            stream = stream,
            delay = delay,
            callback = callback
        )

    def send_delta(self):
        delta = self.window_l -\
            netius.common.HTTP2_SETTINGS[netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE]
        if delta == 0: return
        self.send_window_update(increment = delta, stream = 0x00)

    def delay_frame(self, *args, **kwargs):
        # retrieves the reference to the stream identifier for which
        # the frame is meant to be sent, and then uses this same value
        # to try to retrieve the target stream of the frame
        stream = kwargs["stream"]
        stream = self.parser._get_stream(stream)

        # adds the frame structure (tuple) as the structure describing
        # the frame to be delayed, then increments the frame counter in
        # the stream so that it represent a proper value
        self.frames.append((args, kwargs))
        stream.frames += 1

        # returns a zero value indicating that no bytes have been sent
        # "immediately" by this method
        return 0

    def flush_frames(self, all = True):
        """
        Runs the flush operation on the delayed/pending frames, meaning
        that the window/availability tests are going to be run, checking
        if the various streams and connection are ready for sending the
        frames.

        In case the all flag is active the complete set of frames are going
        to be tested for sending, this operation implies more resource usage.

        This method should be called after a window update frame is
        received so that the pending frames may be sent.

        :type all: bool
        :param all: If the complete set of frames should be tested, or
        if instead at the first testing fail the control flow should be
        returned immediately.
        :rtype: bool
        :return: If all the pending frames have been successfully flushed.
        """

        # starts the values for both the offset value to be used in the
        # pop operation and the dictionary to be used in the storage of
        # the bitset of streams marked as started in the iteration
        offset = 0
        starved = dict() if all else None

        # iterates over the complete set of frames pending to to be sent
        # (delayed) trying to send each of them until one fails and the
        # flushing operation is delayed until further requesting
        while offset < len(self.frames):
            # retrieves the reference to the current frame tuple to
            # be sent and retrieves the stream and payload from it
            frame = self.frames[offset]
            args, kwargs = frame
            stream = kwargs["stream"]
            payload = kwargs["payload"]
            payload_l = len(payload)

            # verifies that the stream is currently place in the list of
            # stream that are considered unavailable as this is a state
            # required for proper execution
            netius.verify(stream in self.unavailable)

            # verifies if the stream associated with the frame to be
            # sent is in the started map and if that's the case continue
            # the current loop immediately (cannot flush frame)
            if starved and stream in starved:
                offset += 1
                continue

            # retrieves the reference to the stream object from the
            # identifier of the stream, this may an invalid/unset value
            _stream = self.parser._get_stream(stream, strict = False)

            # verifies if the current stream to be flushed is still
            # open and if that's not the case removes the frame from
            # the frames queue and skips the current iteration
            if not _stream or not _stream.is_open():
                self.frames.pop(offset)
                if _stream: _stream.frames -= 1
                continue

            # makes sure that the stream is currently marked as not available
            # this should be the state for every stream that has pending frames
            netius.verify(not _stream._available)

            # verifies if there's available "space" in the stream flow
            # to send the current payload and in case there's not breaks
            # the current loop as there's nothing else to be done, delays
            # pending frames for a new flush operation, note that the
            # return value is invalid (meaning that the stream may not
            # be available), a special failover operation exists if the
            # all flush operation is enabled in which the stream is marked
            # as starved and the current iteration is skipped trying to
            # flush frames from different streams
            available = self.available_stream(stream, payload_l, strict = False)
            if not available and not all: return False
            if not available and all:
                starved[stream] = True
                offset += 1
                continue

            # removes the frame from both of the frame queues (both global
            # and stream) so that it is no longer going to be used for flush
            self.frames.pop(offset)
            _stream.frames -= 1

            # decrements the current stream window by the size of the payload
            # and then runs the send frame operation for the pending frame
            self.increment_remote(stream, payload_l * -1, all = True)
            self.send_frame(*args, **kwargs)

        # returns the final result with a valid value meaning that all of the
        # flush operations have been successful (no frames pending in connection)
        return True if offset == 0 else False

    def flush_available(self):
        """
        Runs the (became) available flush operation that tries to determine
        all the streams that were under the "blocked" state and became
        "unblocked", notifying them about that "edge" operation.

        This operation must be performed after any of the blocking constraints
        is changed (eg: connection window, stream window, etc.).
        """

        # iterates over the complete set of streams (identifiers) that are
        # currently under the unavailable/blocked state, to try to determine
        # if they became unblocked by the "current operation"
        for stream in netius.legacy.keys(self.unavailable):
            self.try_available(stream)

    def set_settings(self, settings):
        self.settings_r.update(settings)

    def close_stream(self, stream, final = False, flush = False, reset = False):
        if not self.parser._has_stream(stream): return
        stream = self.parser._get_stream(stream)
        if not stream: return
        stream.end_stream_l = final
        stream.close(flush = flush, reset = reset)

    def available_stream(self, stream, length, strict = True):
        if self.window == 0: return False
        if self.window < length: return False
        stream = self.parser._get_stream(stream)
        if not stream: return True
        if stream.window == 0: return False
        if stream.window < length: return False
        if strict and stream.frames: return False
        return True

    def fragment_stream(self, stream, data):
        stream = self.parser._get_stream(stream)
        return stream.fragment(data)

    def fragmentable_stream(self, stream, data):
        stream = self.parser._get_stream(stream)
        return stream.fragmentable(data)

    def open_stream(self, stream):
        stream = self.parser._get_stream(stream, strict = False)
        if not stream : return False
        return True if stream and stream.is_open() else False

    def try_available(self, stream, strict = True):
        """
        Tries to determine if the stream with the provided identifier
        has just became available (unblocked from blocked state), this
        happens when the required window value (either connection or
        stream is increased properly).

        :type stream: int
        :param stream: The identifier of the stream that is going to
        be tested from proper connection availability.
        :type strict: bool
        :param strict: If the strict mode should be used in the availability
        testing, this implies extra verifications.
        """

        # verifies if the stream is currently present in the map of unavailable
        # or blocked streams and if that's the case returns immediately as
        # the connection is not blocked
        if not stream in self.unavailable: return

        # tries to retrieve the stream object reference from the identifier and
        # in case none is retrieved (probably stream closed) returns immediately
        # and removes the stream from the map of unavailability
        _stream = self.parser._get_stream(stream, strict = False)
        if not _stream:
            del self.unavailable[stream]
            return

        # tries to determine if the stream is available for the sending of at
        # least one byte and if that's not the case returns immediately, not
        # setting the stream as available
        if not self.available_stream(stream, 1, strict = strict): return

        # removes the stream from the map of unavailable stream and "notifies"
        # the stream about the state changing operation to available/unblocked
        del self.unavailable[stream]
        _stream.available()

    def try_unavailable(self, stream, strict = True):
        """
        Runs the unavailability test on the stream with the provided identifier
        meaning that a series of validation will be performed to try to determine
        if for some reason is not possible to send any more data frames to the
        stream until some window changes. A stream that is under the unavailable
        state is considered "blocked".

        :type stream: int
        :param stream: The identifier of the stream that is going to
        be tested from proper connection unavailability.
        :type strict: bool
        :param strict: If the strict mode should be used in the availability
        testing, this implies extra verifications.
        """

        # in case the stream identifier is already present in the unavailable
        # map it cannot be marked as unavailable again
        if stream in self.unavailable: return

        # tries to retrieve the reference to the stream object to be tested
        # an in case none is found (connection closed) returns immediately
        _stream = self.parser._get_stream(stream, strict = False)
        if not _stream: return

        # runs the proper availability verification by testing the capacity
        # of the stream to send one byte and in case there's capacity to send
        # that byte the stream is considered available or unblocked, so the
        # control flow must be returned (stream not marked)
        if self.available_stream(stream, 1, strict = strict): return

        # marks the stream as unavailable and "notifies" the stream object
        # about the changing to the unavailable/blocked state
        self.unavailable[stream] = True
        _stream.unavailable()

    def increment_remote(self, stream, increment, all = False):
        """
        Increments the size of the remove window associated with
        the stream passed by argument by the size defined in the
        increment field (in bytes).

        If the stream is not provided or invalid the global window
        is updated instead of the stream one.

        :type stream: int
        :param stream: The identifier of the stream that is going
        to have its window incremented, or invalid if the global
        connection window is meant to be updated.
        :type increment: int
        :param increment: The increment in bytes for the window,
        this value may be negative for decrement operations.
        :type all: bool
        :param all: If all the resources (connection and stream)
        should be updated by the increment operation.
        """

        if not stream or all: self.window += increment
        if not stream: return
        stream = self.parser._get_stream(stream)
        if not stream: return
        stream.remote_update(increment)

    def increment_local(self, stream, increment):
        # increments the global connection local window
        # by the provided value, and then verifies if the
        # threshold has been passed, if that's the case
        # the window updated frame must be sent so that
        # the remove end point is properly notified
        self.window_l += increment
        if self.window_l < self.window_t:
            self.send_window_update(
                increment = self.window_o - self.window_l,
                stream = 0x00
            )
            self.window_l = self.window_o

        # tries to retrieve the stream associates with the
        # provided identifier and then runs the local update
        # operation in it (may trigger window update flushing)
        stream = self.parser._get_stream(stream)
        if not stream: return
        stream.local_update(increment)

    def error_connection(
        self,
        last_stream = 0x00,
        error_code = 0x00,
        message = "",
        close = True,
        callback = None
    ):
        self.send_goaway(
            last_stream = last_stream,
            error_code = error_code,
            message = message,
            close = close,
            callback = callback
        )

    def error_stream(
        self,
        stream,
        last_stream = 0x00,
        error_code = 0x00,
        message = "",
        close = True,
        callback = None
    ):
        self.send_rst_stream(
            error_code = error_code,
            stream = stream,
            callback = lambda c: self.error_connection(
                last_stream = last_stream,
                error_code = error_code,
                message = message,
                close = close,
                callback = callback
            )
        )

    def on_header(self, header):
        self.owner.on_header_http2(self, self.parser, header)

    def on_payload(self):
        self.owner.on_payload_http2(self, self.parser)

    def on_frame(self):
        self.owner.on_frame_http2(self, self.parser)

    def on_data_h2(self, stream, contents):
        self.increment_local(
            stream and stream.identifier,
            increment = len(contents) * -1
        )
        self.owner.on_data_http2(self, self.parser, stream, contents)

    def on_headers_h2(self, stream):
        self.owner.on_headers_http2(self, self.parser, stream)

    def on_rst_stream(self, stream, error_code):
        self.owner.on_rst_stream_http2(self, self.parser, stream, error_code)

    def on_settings(self, settings, ack):
        self.owner.on_settings_http2(self, self.parser, settings, ack)

    def on_ping(self, opaque, ack):
        self.owner.on_ping_http2(self, self.parser, opaque, ack)

    def on_goaway(self, last_stream, error_code, extra):
        self.owner.on_goaway_http2(self, self.parser, last_stream, error_code, extra)

    def on_window_update(self, stream, increment):
        self.increment_remote(stream and stream.identifier, increment)
        self.flush_frames()
        self.flush_available()
        self.owner.on_window_update_http2(self, self.parser, stream, increment)

    def on_continuation(self, stream):
        self.owner.on_continuation_http2(self, self.parser, stream)

    def is_throttleable(self):
        if self.legacy: return http.HTTPConnection.is_throttleable(self)
        return False

    @property
    def connection_ctx(self):
        if self.legacy: return super(HTTP2Connection, self).connection_ctx
        if not self.parser: return self
        if not self.parser.stream_o: return self
        return self.parser.stream_o

    @property
    def parser_ctx(self):
        if self.legacy: return super(HTTP2Connection, self).parser_ctx
        if not self.parser: return None
        if not self.parser.stream_o: return self.parser
        return self.parser.stream_o

    def _build_c(self, callback, stream, data_l):
        stream = self.parser._get_stream(stream, strict = False)
        if not stream: return callback

        stream.pending_s += data_l
        old_callback = callback

        def callback(connection):
            stream.pending_s -= data_l
            if not old_callback: return
            return old_callback(connection)

        return callback

    def _flush_plain(self, stream = None, callback = None):
        self.send_part(b"", stream = stream, callback = callback)

    def _flush_chunked(self, stream = None, callback = None):
        if self.legacy: return http.HTTPConnection._flush_chunked(
            self,
            stream = stream,
            callback = callback
        )
        self._flush_plain(stream = stream, callback = callback)

class HTTP2Server(http.HTTPServer):

    def __init__(
        self,
        legacy = True,
        safe = False,
        settings = netius.common.HTTP2_SETTINGS_OPTIMAL,
        *args,
        **kwargs
    ):
        self.legacy = legacy
        self.safe = safe
        self.settings = settings
        self.settings_t = netius.legacy.items(self.settings)
        self.has_h2 = self._has_h2()
        self.has_all_h2 = self._has_all_h2()
        self._protocols = []
        self.safe = self.get_env("SAFE", self.safe, cast = bool)
        http.HTTPServer.__init__(self, *args, **kwargs)

    @classmethod
    def _has_hpack(cls):
        try: import hpack #@UnusedImport
        except ImportError: return False
        return True

    @classmethod
    def _has_alpn(cls):
        return ssl.HAS_ALPN

    @classmethod
    def _has_npn(cls):
        return ssl.HAS_NPN

    def info_dict(self, full = False):
        info = http.HTTPServer.info_dict(self, full = full)
        info.update(
            legacy = self.legacy,
            safe = self.safe,
            has_h2 = self.has_h2,
            has_all_h2 = self.has_all_h2
        )
        return info

    def get_protocols(self):
        if self._protocols: return self._protocols
        if not self.safe and self.has_h2: self._protocols.extend(["h2"])
        if self.legacy: self._protocols.extend(["http/1.1", "http/1.0"])
        return self._protocols

    def build_connection(self, socket, address, ssl = False):
        return HTTP2Connection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding,
            legacy = self.legacy,
            settings = self.settings
        )

    def on_exception(self, exception, connection):
        if hasattr(connection, "legacy") and connection.legacy:
            return http.HTTPServer.on_exception(self, exception, connection)
        if not isinstance(exception, netius.NetiusError):
            return http.HTTPServer.on_exception(self, exception, connection)
        try: self._handle_exception(exception, connection)
        except Exception: connection.close()

    def on_ssl(self, connection):
        http.HTTPServer.on_ssl(self, connection)
        if self.safe or not self.has_h2: return
        protocol = connection.ssl_protocol()
        if not protocol == "h2": return
        connection.set_h2()

    def on_serve(self):
        http.HTTPServer.on_serve(self)
        safe_s = "with" if self.safe else "without"
        self.info("Starting HTTP2 server %s safe mode ..." % safe_s)
        if not self.has_h2: self.info("No support for HTTP2 is available ...")
        elif not self.has_all_h2: self.info("Limited support for HTTP2 is available ...")
        for setting, name in netius.common.HTTP2_TUPLES:
            if not self.env: continue
            value = self.get_env(name, None, cast = int)
            if value == None: continue
            self.settings[setting] = value
            self.info("Setting HTTP2 setting %s with value '%d' ..." % (name, value))
        self.settings_t = netius.legacy.items(self.settings)

    def on_preface_http2(self, connection, parser):
        connection.send_settings(settings = self.settings_t)
        connection.send_delta()

    def on_header_http2(self, connection, parser, header):
        pass

    def on_payload_http2(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_frame(connection, parser)

    def on_frame_http2(self, connection, parser):
        pass

    def on_data_http2(self, connection, parser, stream, contents):
        pass

    def on_headers_http2(self, connection, parser, stream):
        pass

    def on_rst_stream_http2(self, connection, parser, stream, error_code):
        if not stream: return
        stream.end_stream = True
        stream.end_stream_l = True
        stream.close(reset = False)

    def on_settings_http2(self, connection, parser, settings, ack):
        if ack: return
        self.debug("Received settings %s for connection" % str(settings))
        connection.set_settings(dict(settings))
        connection.send_settings(ack = True)

    def on_ping_http2(self, connection, parser, opaque, ack):
        if ack: return
        connection.send_ping(opaque = opaque, ack = True)

    def on_goaway_http2(self, connection, parser, last_stream, error_code, extra):
        if error_code == 0x00: return
        self._log_error(error_code, extra)

    def on_window_update_http2(self, connection, parser, stream, increment):
        self.debug("Window updated with increment %d bytes" % increment)

    def on_continuation_http2(self, connection, parser, stream):
        pass

    def on_send_http2(self, connection, parser, type, flags, payload, stream):
        is_debug = self.is_debug()
        is_debug and self._log_send(connection, parser, type, flags, payload, stream)

    def _has_h2(self):
        cls = self.__class__
        if not cls._has_hpack(): return False
        return True

    def _has_all_h2(self):
        cls = self.__class__
        if not cls._has_hpack(): return False
        if not cls._has_alpn(): return False
        if not cls._has_npn(): return False
        return True

    def _handle_exception(self, exception, connection):
        stream = exception.get_kwarg("stream")
        error_code = exception.get_kwarg("error_code", 0x00)
        message = exception.get_kwarg("message", "")
        ignore = exception.get_kwarg("ignore", False)
        self.warning(exception)
        self.log_stack()
        if ignore: return connection.send_ping(ack = True)
        if stream: return connection.error_stream(
            stream,
            error_code = error_code,
            message = message
        )
        return connection.error_connection(
            error_code = error_code,
            message = message
        )

    def _log_frame(self, connection, parser):
        self.debug(
            "Received frame 0x%02x (%s) for stream %d with length %d bytes" %\
            (parser.type, parser.type_s, parser.stream, parser.length)
        )

        self._log_frame_details(
            parser,
            parser.type_s,
            parser.flags,
            parser.payload,
            parser.stream,
            False
        )

    def _log_error(self, error_code, extra):
        message = netius.legacy.str(extra)
        self.warning(
            "Received error 0x%02x with message '%s'" %\
            (error_code, message)
        )

    def _log_send(self, connection, parser, type, flags, payload, stream):
        length = len(payload)
        type_s = parser.get_type_s(type)

        self.debug(
            "Sent frame 0x%02x (%s) for stream %d with length %d bytes" %\
            (type, type_s, stream, length)
        )

        self._log_frame_details(parser, type_s, flags, payload, stream, True)

    def _log_window(self, parser, stream, remote = False):
        name = "SEND" if remote else "RECV"
        connection = parser.connection
        window = connection.window if remote else connection.window_l
        self.debug("Connection %s window size is %d bytes" % (name, window))
        stream = parser._get_stream(stream, strict = False)
        if not stream: return
        window = stream.window if remote else stream.window_l
        self.debug(
            "Stream %d (dependency = %d, weight = %d) %s window size is %d bytes" %\
            (stream.identifier, stream.dependency, stream.weight, name, window)
        )

    def _log_frame_details(self, parser, type_s, flags, payload, stream, out):
        type_l = type_s.lower()
        method_s = "_log_frame_" + type_l
        if not hasattr(self, method_s): return
        method = getattr(self, method_s)
        method(parser, flags, payload, stream, out)

    def _log_frame_flags(self, type_s, *args):
        flags = ", ".join(args)
        pluralized = "flags" if len(args) > 1 else "flag"
        if flags: self.debug("%s with %s %s active" % (type_s, pluralized, flags))
        else: self.debug("Frame %s with no flags active" % type_s)

    def _log_frame_data(self, parser, flags, payload, stream, out):
        _stream = parser._get_stream(stream, strict = False)
        flags_l = self._flags_l(flags, (("END_STREAM", 0x01),))
        self._log_frame_flags("DATA", *flags_l)
        if _stream: self.debug("Frame DATA for path '%s'" % _stream.path_s)
        self._log_window(parser, stream, remote = out)

    def _log_frame_headers(self, parser, flags, payload, stream, out):
        flags_l = self._flags_l(
            flags,
            (
                ("END_STREAM", 0x01),
                ("END_HEADERS", 0x04),
                ("PADDED", 0x08),
                ("PRIORITY", 0x20)
            )
        )
        self._log_frame_flags("HEADERS", *flags_l)

    def _log_frame_rst_stream(self, parser, flags, payload, stream, out):
        error_code, = struct.unpack("!I", payload)
        self.debug("Frame RST_STREAM with error code %d" % error_code)

    def _log_frame_goaway(self, parser, flags, payload, stream, out):
        last_stream, error_code = struct.unpack("!II", payload[:8])
        extra = payload[8:]
        self.debug(
            "Frame GOAWAY with last stream %d, error code %d and message %s" %\
            (last_stream, error_code, extra)
        )

    def _log_frame_window_update(self, parser, flags, payload, stream, out):
        increment, = struct.unpack("!I", payload)
        self.debug("Frame WINDOW_UPDATE with increment %d" % increment)
        self._log_window(parser, stream, remote = not out)

    def _flags_l(self, flags, definition):
        flags_l = []
        for name, value in definition:
            valid = True if flags & value else False
            if not valid: continue
            flags_l.append(name)
        return flags_l
