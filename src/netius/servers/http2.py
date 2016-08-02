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

class HTTP2Connection(http.HTTPConnection):

    def __init__(
        self,
        legacy = True,
        window = netius.common.HTTP2_WINDOW,
        settings = netius.common.HTTP2_SETTINGS_OPTIMAL,
        *args,
        **kwargs
    ):
        http.HTTPConnection.__init__(self, *args, **kwargs)
        self.legacy = legacy
        self.settings = dict(settings)
        self.window = window
        self.window_o = self.settings[netius.common.http2.SETTINGS_INITIAL_WINDOW_SIZE]
        self.window_l = self.window_o
        self.window_t = self.window_o // 2
        self.preface = False
        self.preface_b = b""
        self.frames = []

    def open(self, *args, **kwargs):
        http.HTTPConnection.open(self, *args, **kwargs)
        if not self.legacy: self.set_h2()

    def set_h2(self):
        self.legacy = False
        if self.parser: self.parser.destroy()
        self.parser = netius.common.HTTP2Parser(self, store = True)
        self.parser.bind("on_header", self.on_header)
        self.parser.bind("on_frame", self.on_frame)
        self.parser.bind("on_data_h2", self.on_data_h2)
        self.parser.bind("on_headers_h2", self.on_headers_h2)
        self.parser.bind("on_rst_stream", self.on_rst_stream)
        self.parser.bind("on_settings", self.on_settings)
        self.parser.bind("on_ping", self.on_ping)
        self.parser.bind("on_goaway", self.on_goaway)
        self.parser.bind("on_window_update", self.on_window_update)

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

    def send_plain(
        self,
        data,
        stream = None,
        final = True,
        delay = False,
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
        delay = False,
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
        delay = False,
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
        delay = False,
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
        delay = False,
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

        # defines the proper default base http version in case it has not
        # been provided as part the default values
        version = version or "HTTP/2.0"

        # creates the headers base list that is going to store the various
        # header tuples representing the headers in canonical http2 form
        headers_b = []
        headers_b.append((":status", str(code)))

        # iterates over the complete set of raw header values to normalize
        # them and add them to the currently defined base list
        for key, value in headers.items():
            key = netius.common.header_down(key)
            if key in ("connection", "transfer-encoding"): continue
            if not type(value) == list: value = (value,)
            for _value in value: headers_b.append((key, _value))

        # verifies if this is considered to be the final operation in the stream
        # and if that's the case creates a new callback for the closing of the
        # stream at the end of the operation, this is required for proper collection
        if final:
            old_callback = callback

            def callback(connection):
                old_callback and old_callback(connection)
                self.close_stream(stream, final = final)

        # runs the send headers operations that should send the headers list
        # to the other peer and returns the number of bytes sent
        count = self.send_headers(
            headers_b,
            end_stream = final,
            stream = stream,
            delay = delay,
            callback = callback
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
        delay = False,
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
                old_callback and old_callback(connection)
                self.close_stream(stream, final = final)

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
        data_l = len(data)
        if end_stream: flags |= 0x01
        if not self.available_stream(stream, data_l):
            return self.delay_frame(
                type = netius.common.DATA,
                flags = flags,
                payload = data,
                stream = stream,
                delay = delay,
                callback = callback
            )
        self.increment_remote(stream, data_l * -1)
        return self.send_frame(
            type = netius.common.DATA,
            flags = flags,
            payload = data,
            stream = stream,
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
            stream = stream,
            delay = delay,
            callback = callback
        )

    def send_rst_stream(
        self,
        error_code = 0x00,
        stream = None,
        delay = False,
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
        opaque = b"\0\0\0\0\0\0\0\0",
        ack = False,
        delay = False,
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
        delay = False,
        callback = None
    ):
        if close:
            old_callback = callback

            def callback(connection):
                old_callback and old_callback(connection)
                self.close()

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
        delay = False,
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
        stream = kwargs["stream"]
        stream = self.parser._get_stream(stream)
        self.frames.append((args, kwargs))
        return 0

    def flush_frames(self):
        while self.frames:
            frame = self.frames[0]
            args, kwargs = frame
            stream = kwargs["stream"]
            payload = kwargs["payload"]
            payload_l = len(payload)

            # verifies if the current stream to be flushed is still
            # open and if that's not the case removed the frame from
            # the frames queue and skips the current iteration
            open = self.open_stream(stream)
            if not open: self.frames.pop(0); continue

            # verifies if there's available "space" in the stream flow
            # to send the current payload and in case there's not breaks
            # the current loop as there's nothing else to be done, delays
            # pending frames for a new flush operation
            available = self.available_stream(stream, payload_l)
            if not available: break

            # decrements the current stream window by the size of the payload
            # and then runs the send frame operation for the pending frame
            self.increment_remote(stream, payload_l * -1)
            self.send_frame(*args, **kwargs)
            self.frames.pop(0)

    def set_settings(self, settings):
        self.settings.update(settings)

    def close_stream(self, stream, final = False):
        if not self.parser._has_stream(stream): return
        stream = self.parser._get_stream(stream)
        if not stream: return
        stream.end_stream_l = final
        stream.close()

    def available_stream(self, stream, length):
        if self.window == 0: return False
        if self.window < length: return False
        _stream = stream
        stream = self.parser._get_stream(stream)
        if not stream: return True
        if stream.window == 0: return False
        if stream.window < length: return False
        return True

    def fragment_stream(self, stream, data):
        stream = self.parser._get_stream(stream)
        return stream.fragment(data)

    def fragmentable_stream(self, stream, data):
        stream = self.parser._get_stream(stream)
        return stream.fragmentable(data)

    def open_stream(self, stream):
        stream = self.parser._get_stream(stream)
        return True if stream and stream.is_open() else False

    def increment_remote(self, stream, increment):
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
        """

        if not stream: self.window += increment
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
            self.windows_l = self.window_o

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

    def on_frame(self):
        self.owner.on_frame_http2(self, self.parser)

    def on_data_h2(self, stream, contents):
        self.increment_local(stream and stream.identifier, increment = len(contents) * -1)
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
        self.owner.on_window_update_http2(self, self.parser, stream, increment)

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

    def _flush_plain(self, stream = None, callback = None):
        self.send_plain(b"", stream = stream, callback = callback)

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
        safe = True,
        settings = netius.common.HTTP2_SETTINGS_OPTIMAL,
        *args,
        **kwargs
    ):
        self.legacy = legacy
        self.safe = safe
        self.settings = settings
        self.settings_t = netius.legacy.items(self.settings)
        self._protocols = []
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
            legacy = self.legacy,
            settings = self.settings
        )

    def on_exception(self, exception, connection):
        legacy = lambda: http.HTTPServer.on_exception(self, exception, connection)
        if not isinstance(exception, netius.NetiusError): return legacy()
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

    def on_ssl(self, connection):
        http.HTTPServer.on_ssl(self, connection)
        if self.safe: return
        protocol = connection.ssl_protocol()
        if not protocol == "h2": return
        connection.set_h2()

    def on_preface_http2(self, connection, parser):
        connection.send_settings(settings = self.settings_t)
        connection.send_delta()

    def on_header_http2(self, connection, parser, header):
        pass

    def on_frame_http2(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_frame(connection, parser)

    def on_data_http2(self, connection, parser, stream, contents):
        if not stream.is_ready: return
        self.on_data_http(stream, stream)

    def on_headers_http2(self, connection, parser, stream):
        if not stream.is_ready: return
        self.on_data_http(stream, stream)

    def on_rst_stream_http2(self, connection, parser, stream, error_code):
        stream.end_stream = True
        stream.end_stream_l = True
        stream.close()

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

    def _log_frame(self, connection, parser):
        self.debug(
            "Received frame 0x%02x (%s) for stream %d with length %d bytes" %\
            (parser.type, parser.type_s, parser.stream, parser.length)
        )

    def _log_error(self, error_code, extra):
        self.warning(
            "Received error 0x%02x with message '%s'" %\
            (error_code, extra)
        )
