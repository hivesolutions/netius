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

"""netius.servers.asgi_neo

Async/await based implementation of the ASGI compliant server, built on
top of the Netius HTTP/2 server. Translates the incoming requests into the
standard scope map and drives the application coroutine in the event loop,
relaying the request events to it through the receive awaitable and the
response ones back to the client through the send one. Handles the HTTP,
the WebSocket and the lifespan scopes and adapts the legacy (double
callable) applications into the current calling convention.

This module uses syntax that is only available under the newer interpreters
so it must never be imported directly, the netius.servers.asgi module takes
care of such verification.
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import time
import struct
import base64
import inspect
import hashlib
import traceback

import netius
import netius.common

from . import http
from . import http2
from . import ws

ASGI_VERSION = "3.0"
""" The version of the ASGI specification that is implemented by
the server, this is the value that is announced to the application
under the asgi key of the scope """

SPEC_VERSION = "2.3"
""" The version of the HTTP and WebSocket scope specifications that
the server complies with, note that the lifespan scope uses its own
versioning (as defined by the specification) """

LIFESPAN_VERSION = "2.0"
""" The version of the lifespan scope specification that is complied
with, only the startup and shutdown events are supported """

COMPRESSED_LIMIT = 5242880
""" The default maximum size value for the sending of compressed
content, this should ensure proper resource usage avoiding extreme
high levels of resource usage for compression of large files """

MAX_PENDING = 65536
""" The size in bytes considered to be the maximum allowed in the
sending buffer of a connection, once this value is reached the
application is suspended until the payload is flushed, avoiding the
starvation of the producer to consumer relation """

BUFFER_SIZE = 40960
""" The size (in bytes) of the chunks in which the payload of a
request is handed to the application, avoiding the complete loading
of a large payload in memory """

PUMP_LIMIT = 512
""" The maximum number of iterations of the asyncio event loop that
are run in a single pump operation, bounding the amount of time that
the applications may starve the event loop of the server """

LIFESPAN_TIMEOUT = 30.0
""" The maximum amount of time (in seconds) that the server waits
for the application to acknowledge either the startup or the shutdown
of the lifespan protocol, once this value is reached the server moves
on, avoiding an application from blocking the process forever """

LIFESPAN_INTERVAL = 0.001
""" The amount of time (in seconds) that separates two iterations of
the event loop while waiting for the acknowledgment of a lifespan
event, avoiding the complete usage of a processor while waiting """

CONTINUATION_OPCODE = 0x00
""" The WebSocket operation code that identifies a frame that
carries more payload for the message that is being assembled """

TEXT_OPCODE = 0x01
""" The WebSocket operation code that identifies a frame whose
payload is a UTF-8 encoded string """

BINARY_OPCODE = 0x02
""" The WebSocket operation code that identifies a frame whose
payload is a raw sequence of bytes """

CLOSE_OPCODE = 0x08
""" The WebSocket operation code of the frame that signals the
closing of the connection, it may carry the close code """

PING_OPCODE = 0x09
""" The WebSocket operation code of the frame that requests a
pong frame to be sent back with the same payload """

PONG_OPCODE = 0x0A
""" The WebSocket operation code of the frame sent as the answer
to a ping one """

CLOSE_CODE = 1000
""" The WebSocket close code used whenever the application closes
the connection without providing an explicit one """

CLOSE_NONE = 1005
""" The WebSocket close code reported to the application when the
client closes the connection without providing an explicit one """

CLOSE_REJECT = 403
""" The HTTP status code sent to the client when the application
refuses the WebSocket handshake (no accept message) """


class ASGIServer(http2.HTTP2Server):
    """
    Base class for the creation of an asgi compliant server
    the server should be initialized with the "target" app
    object as reference and a mount point.

    The application is called with the scope of the connection
    and with the receive and send awaitables, that are used
    respectively to consume the events of the request and to
    produce the ones of the response.

    :see: https://asgi.readthedocs.io/en/latest/specs/main.html
    """

    def __init__(
        self,
        app,
        mount="",
        compressed_limit=COMPRESSED_LIMIT,
        max_pending=MAX_PENDING,
        lifespan=True,
        asyncio=None,
        *args,
        **kwargs
    ):
        http2.HTTP2Server.__init__(self, *args, **kwargs)
        self.app = app
        self.mount = mount
        self.mount_l = len(mount)
        self.compressed_limit = compressed_limit
        self.max_pending = max_pending
        self.lifespan = lifespan
        self.asyncio = netius.is_asyncio() if asyncio == None else asyncio
        self.loop_asyncio = netius.new_loop_asyncio() if self.asyncio else None
        self.pumping = False
        self.legacy_app = self._is_legacy(app)
        self.lifespan_t = None
        self.lifespan_v = None
        self.lifespan_m = None
        self.lifespan_f = None
        self.lifespan_q = []

    def cleanup(self):
        http2.HTTP2Server.cleanup(self)

        # closes the event loop that drives the applications as it's no
        # longer going to be used (avoids leaking of resources)
        if not self.loop_asyncio:
            return
        self.loop_asyncio.close()
        self.loop_asyncio = None

    def ticks(self):
        http2.HTTP2Server.ticks(self)

        # runs the pending work of the loop that drives the applications
        # so that both the timers and the callbacks scheduled by them are
        # able to make progress while the server is running
        self._pump()

    def on_connection_c(self, connection):
        http2.HTTP2Server.on_connection_c(self, connection)

        # applies the limit of the sending buffer to the connection so that
        # the payload produced by an application is properly bounded
        connection.max_pending = self.max_pending

    def on_connection_d(self, connection):
        http2.HTTP2Server.on_connection_d(self, connection)

        # notifies a possible application still running for the connection
        # that the other end is gone, so that it may stop its execution
        self._disconnect(connection)

        # tries to run the releasing operation on the current connection
        # so that the proper destruction of objects is performed avoiding
        # leaving any extra memory leak (would create problems)
        self._release(connection)

        # runs the extra release queue operation for the connection so that
        # the (possible) associated queue is properly release (no leaks)
        self._release_queue(connection)

    def on_serve(self):
        http2.HTTP2Server.on_serve(self)
        if self.env:
            self.compressed_limit = self.get_env(
                "COMPRESSED_LIMIT", self.compressed_limit, cast=int
            )
        if self.env:
            self.max_pending = self.get_env("MAX_PENDING", self.max_pending, cast=int)
        if self.env:
            self.lifespan = self.get_env("LIFESPAN", self.lifespan, cast=bool)
        self.info(
            "Starting ASGI server with %d bytes limit on compression ..."
            % self.compressed_limit
        )
        self._start_lifespan()

    def on_stop(self):
        self._stop_lifespan()
        http2.HTTP2Server.on_stop(self)

    def on_data(self, connection, data):
        # in case the connection has already been upgraded the data is no
        # longer part of an HTTP message and must be handled by the frame
        # based infra-structure instead of the HTTP one
        if not self._is_upgraded(connection):
            http2.HTTP2Server.on_data(self, connection, data)
            return

        netius.StreamServer.on_data(self, connection, data)

        # iterates while there's still data pending to be parsed from the
        # current message received using the WS protocol
        while data:
            # retrieves the current (pending) buffer of data for the
            # connection and tries to run the decoder of websockets
            # frame on the complete set of data pending in case there's
            # a problem the (pending) data is added to the buffer
            buffer = self._get_buffer(connection)
            data = buffer + data
            try:
                final = netius.legacy.ord(data[0]) & 0x80 > 0
                opcode = netius.legacy.ord(data[0]) & 0x0F
                decoded, data = netius.common.decode_ws(data)
            except netius.DataError:
                connection.ws_buffer.append(data)
                break
            self.on_data_ws(connection, opcode, decoded, final=final)

    def on_data_http(self, connection, parser):
        http2.HTTP2Server.on_data_http(self, connection, parser)

        # determines if the current request is a websocket upgrade one as
        # that defines the kind of scope that is going to be built for it
        is_upgrade = self._is_upgrade(connection, parser)

        # builds the scope map for the current request and retrieves the
        # buffer with the payload of it, note that for a websocket scope
        # there's no payload to be consumed by the application
        if is_upgrade:
            scope = self._build_scope_ws(connection, parser)
            body = None
        else:
            scope = self._build_scope(connection, parser)
            body = parser.get_message_b(copy=True)

        # verifies if the connection already has a task associated with
        # it, if that's the case the connection is already in use and the current
        # request processing must be delayed for future processing, this is
        # typically associated with HTTP pipelining
        if hasattr(connection, "task") and connection.task:
            if not hasattr(connection, "queue"):
                connection.queue = []
            connection.queue.append((scope, body))
            return

        # calls the proper on scope callback so that the current request
        # is handled and processed (flush operation)
        self.on_scope(connection, scope, body=body)

    def on_scope(self, connection, scope, body=None):
        # resets the state of the connection for the handling of the new
        # scope, note that the messages of a previous request may never be
        # delivered to the application of the current one
        connection.scope = scope
        connection.body = body
        connection.messages = []
        connection.receive_f = None
        connection.started = False
        connection.finished = False
        connection.empty = False

        # in case the scope is a websocket one the connect event is queued
        # so that it's the first one to be received by the application, as
        # defined by the specification
        if scope["type"] == "websocket":
            connection.messages.append(dict(type="websocket.connect"))

        # runs the app logic with the provided scope and the receive and
        # send awaitables, the resulting task is set in the connection for
        # latter retrieval (required for processing/closing)
        coroutine = self._call_app(
            scope, self._build_receive(connection), self._build_send(connection)
        )
        connection.task = self._ensure(coroutine)
        connection.task.add_done_callback(
            lambda future: self._on_task(connection, future)
        )

        # runs the pending work of the application so that the request is
        # handled as soon as possible (avoids waiting for the next tick)
        self._pump()

    def on_data_ws(self, connection, opcode, data, final=True):
        # a close frame ends the connection, the close code is carried by
        # the payload of the frame and an invalid one is reported to the
        # application whenever the client does not provide it
        if opcode == CLOSE_OPCODE:
            code = self._close_code(data)

            # a close frame must be sent back to the client so that the
            # closing handshake is completed, note that the code is only
            # echoed in case a valid one has been provided by the client
            if not connection.finished:
                payload = b"" if code == CLOSE_NONE else struct.pack("!H", code)
                connection.send(
                    netius.common.encode_ws(payload, opcode=CLOSE_OPCODE, mask=False)
                )
                connection.finished = True

            self._push(connection, dict(type="websocket.disconnect", code=code))
            connection.close(flush=True)
            return

        # the answer to a ping frame is a pong one carrying the same payload
        # and it's handled by the server itself, as the specification does
        # not expose this kind of control frames to the application
        if opcode == PING_OPCODE:
            connection.send(
                netius.common.encode_ws(data, opcode=PONG_OPCODE, mask=False)
            )
            return

        # a pong frame is the answer to a ping one sent by the server and
        # as such there's nothing to be done for it
        if opcode == PONG_OPCODE:
            return

        # a continuation frame carries more payload for the message that is
        # currently being assembled, in case there's no such message the
        # frame is a stray one and must be discarded (protocol violation)
        if opcode == CONTINUATION_OPCODE:
            if connection.ws_opcode == None:
                return self.debug("Received stray continuation frame")
            connection.ws_frames.append(data)

        # otherwise a new message is started, keeping the operation code
        # of it as the one that defines the kind of payload of the message
        else:
            connection.ws_opcode = opcode
            connection.ws_frames = [data]

        # in case the frame is not the final one of the message the payload
        # is accumulated while the remaining fragments are received
        if not final:
            return

        # joins the fragments of the message and resets the state of the
        # assembly, so that a new message may be started
        opcode = connection.ws_opcode
        data = b"".join(connection.ws_frames)
        connection.ws_opcode = None
        connection.ws_frames = []

        # builds the receive event according to the kind of payload of the
        # message, note that a text one is decoded using UTF-8 as defined
        # by the WebSocket specification
        if opcode == TEXT_OPCODE:
            message = dict(
                type="websocket.receive", text=netius.legacy.str(data, "utf-8")
            )
        else:
            message = dict(type="websocket.receive", bytes=data)
        self._push(connection, message)

    def _next_queue(self, connection):
        # verifies if the current connection already contains a reference to
        # the queue structure that handles the queueing/pipelining of requests
        # if it does not or the queue is empty returns immediately, as there's
        # nothing currently pending to be done/processed
        if not hasattr(connection, "queue"):
            return
        if not connection.queue:
            return

        # retrieves the current/first element in the connection queue to for
        # the processing and then runs the proper callback for the scope
        scope, body = connection.queue.pop(0)
        self.on_scope(connection, scope, body=body)

    def _build_scope(self, connection, parser):
        # retrieves the path for the current request and then retrieves
        # the query string part for it also, note that the path is the
        # complete one, including the mount point (root path)
        path = parser.get_path(normalize=True)
        query = parser.get_query()

        # decodes the path so that the percent encoded sequences are
        # converted into the characters they represent, as expected by
        # the specification (the raw value is provided separately)
        path_d = self._decode(path)

        # retrieves a possible forwarded protocol value from the request
        # headers and calculates the appropriate (final scheme value)
        # taking the proxy value into account
        forwarded_protocol = parser.headers.get("x-forwarded-proto", None)
        scheme = "https" if connection.ssl else "http"
        scheme = forwarded_protocol if forwarded_protocol else scheme

        # builds the scope map with the complete set of values that define
        # the HTTP connection, so that the application is able to handle
        # the request and respond to it in accordance
        return dict(
            type="http",
            asgi=dict(version=ASGI_VERSION, spec_version=SPEC_VERSION),
            http_version=self._version(parser),
            method=parser.method.upper(),
            scheme=scheme,
            path=path_d,
            raw_path=netius.legacy.bytes(path),
            query_string=netius.legacy.bytes(query),
            root_path=self.mount,
            headers=self._headers(parser),
            client=(connection.address[0], connection.address[1]),
            server=(self.host, self.port),
        )

    def _build_scope_ws(self, connection, parser):
        # builds the base (HTTP) scope for the request and then converts
        # it into a websocket one, as most of the values are shared between
        # the two kinds of scope (as defined by the specification)
        scope = self._build_scope(connection, parser)
        scope["type"] = "websocket"
        scope["scheme"] = "wss" if connection.ssl else "ws"
        scope["subprotocols"] = self._subprotocols(parser)

        # removes the values that are not part of a websocket scope, as the
        # handshake request method is always a GET one
        del scope["method"]

        return scope

    def _build_receive(self, connection):
        async def receive():
            # in case there's a message already queued for the connection
            # it's returned immediately, as no waiting is required
            if connection.messages:
                return connection.messages.pop(0)

            # in case the payload of the request has not been completely
            # consumed a new request event is built for the next chunk of it
            if connection.body:
                return self._message_body(connection)

            # the concurrent usage of the receive awaitable is not allowed
            # by the specification, as the delivery of the events would
            # become an undefined operation
            if connection.receive_f:
                raise netius.NetiusError("Receive already in use")

            # otherwise a future is created and set in the connection so
            # that the next message pushed into it resumes the application
            future = self._future()
            connection.receive_f = future
            return await future

        return receive

    def _build_send(self, connection):
        async def send(message):
            # the sending of a message may require the application to wait
            # for the connection to have capacity for more payload, for such
            # situations a future is returned by the send operation
            future = self._send(connection, message)
            if future:
                await future

        return send

    def _send(self, connection, message):
        message_t = message.get("type", None)
        if message_t == "http.response.start":
            return self._send_start(connection, message)
        elif message_t == "http.response.body":
            return self._send_body(connection, message)
        elif message_t == "websocket.accept":
            return self._send_accept(connection, message)
        elif message_t == "websocket.send":
            return self._send_ws(connection, message)
        elif message_t == "websocket.close":
            return self._send_close(connection, message)
        else:
            raise netius.NetiusError("Invalid message type '%s'" % message_t)

    def _send_start(self, connection, message):
        # a response may only be started once, as sending a new set of
        # headers would invalidate the framing of the connection
        if connection.started:
            raise netius.NetiusError("Response already started")

        # retrieves the parser object from the connection and uses
        # it to retrieve the string version of the HTTP version
        parser = connection.parser
        version_s = parser.version_s

        # retrieves the status code of the response and converts the
        # sequence of byte based tuples into the map of headers that
        # is expected by the underlying infra-structure
        status_c = message.get("status", 200)
        headers = self._headers_map(message.get("headers", []))

        # tries to retrieve the content length value from the headers
        # in case they exist and if the value of them is zero the plain
        # encoding is set in order to avoid extra problems while using
        # chunked encoding with zero length based messages
        length = headers.get("Content-Length", -1)
        length = int(length)
        length = 0 if status_c in http.EMPTY_CODES else length
        if length == 0:
            connection.set_encoding(http.PLAIN_ENCODING)

        # verifies if the length value of the message payload overflow
        # the currently defined limit, if that's the case the connection
        # is set as uncompressed to avoid unnecessary encoding that would
        # consume a lot of resources (mostly processor)
        if length > self.compressed_limit:
            connection.set_uncompressed()

        # tries to determine if the accept ranges value is set and if
        # that's the case forces the uncompressed encoding to avoid possible
        # range mismatch due to re-encoding of the content
        ranges = headers.get("Accept-Ranges", None)
        if ranges == "bytes":
            connection.set_uncompressed()

        # determines if the content range header is set, meaning that
        # a partial chunk value is being sent if that's the case the
        # uncompressed encoding is forced to avoid re-encoding issues
        content_range = headers.get("Content-Range", None)
        if content_range:
            connection.set_uncompressed()

        # verifies if the current connection is using a chunked based
        # stream as this will affect some of the decisions that are
        # going to be taken as part of response header creation
        is_chunked = connection.is_chunked()

        # checks if the provided headers map contains the definition
        # of the content length in case it does not unsets the keep
        # alive setting in the parser because the keep alive setting
        # requires the content length to be defined or the target
        # encoding type to be chunked
        has_length = not length == -1
        if not has_length:
            parser.keep_alive = is_chunked

        # determines if the response may carry a payload, as neither a HEAD
        # request nor some of the status codes allow one, for such situations
        # the payload produced by the application is discarded
        is_head = parser.method and parser.method.upper() == "HEAD"
        connection.empty = is_head or status_c < 200 or status_c in http.EMPTY_CODES

        # an informational or a no content response may never announce a
        # length for a payload that is not going to be sent, as the message
        # is terminated by the first empty line after the headers section
        if status_c < 200 or status_c == 204:
            connection._unset_header(headers, "content-length")

        # applies the base (static) headers to the headers map and then
        # applies the parser based values to the headers map, these
        # values should be dynamic and based in the current state
        # finally applies the connection related headers to the current
        # map of headers so that the proper values are filtered and added
        self._apply_base(headers)
        self._apply_parser(parser, headers)
        self._apply_connection(connection, headers)

        # runs the send header operation on the connection, this operation
        # should serialize the various headers and send them through the
        # current connection according to the currently associated protocol
        connection.send_header(headers=headers, version=version_s, code=status_c)

        # marks the response as started so that a possible failure of the
        # application is no longer able to produce a new response
        connection.started = True

    def _send_body(self, connection, message):
        # the payload of a response may only be sent after the headers
        # of it and never after the response has been completed
        if not connection.started:
            raise netius.NetiusError("Response not started")
        if connection.finished:
            raise netius.NetiusError("Response already completed")

        # retrieves both the payload of the current event and the flag
        # that indicates if more of them are still expected
        body = message.get("body", b"")
        more_body = message.get("more_body", False)

        # a response that may not carry a payload must never write one to
        # the wire, even though the application is free to produce it, as
        # the client would take it as the start of the next response
        if connection.empty:
            body = b""

        # in case more payload is still expected the sending is a partial
        # one, so the application may be suspended in case the connection
        # is no longer able to take more payload (back pressure)
        if more_body:
            if not body:
                return None
            return self._send_pressure(connection, body)

        # sends the last payload of the response through the connection,
        # note that the sending is not a final one as the flushing of the
        # response is the operation that completes it
        if body:
            connection.send_part(body, final=False)

        # marks the response as finished and runs the flush operation in
        # the connection setting the proper callback method for it so that
        # the connection state is defined in the proper way (closed or
        # kept untouched)
        connection.finished = True
        connection.flush_s(callback=self._final)

    def _send_accept(self, connection, message):
        # the handshake of a connection may only be performed once, as
        # the connection has already been upgraded by it
        if self._is_upgraded(connection):
            raise netius.NetiusError("Handshake already performed")

        # retrieves the parser object from the connection and uses
        # it to retrieve the string version of the HTTP version
        parser = connection.parser
        version_s = parser.version_s

        # computes the accept key for the handshake and builds the base
        # set of headers of the response, as defined by the specification
        accept_key = self._accept_key(parser)
        headers = dict()
        headers["Upgrade"] = "websocket"
        headers["Connection"] = "Upgrade"
        headers["Sec-WebSocket-Accept"] = accept_key

        # in case a subprotocol has been negotiated by the application it
        # must be announced back to the client (as expected)
        subprotocol = message.get("subprotocol", None)
        if subprotocol:
            headers["Sec-WebSocket-Protocol"] = subprotocol

        # adds the extra headers provided by the application to the map
        # of headers, note that they are normalized as the ones of a
        # "normal" response would be
        headers.update(self._headers_map(message.get("headers", [])))

        # applies the base (static) headers and sends the switching
        # protocols response, completing the handshake operation
        self._apply_base(headers)
        connection.send_header(
            headers=headers,
            version=version_s,
            code=101,
            code_s="Switching Protocols",
        )

        # marks the connection as an upgraded one so that the data that
        # follows is handled as websocket frames and cancels the closing
        # of the connection by idle timeout, as a websocket connection is
        # expected to be kept open even while no data is exchanged
        connection.ws_handshake = True
        connection.ws_buffer = []
        connection.ws_opcode = None
        connection.ws_frames = []
        connection.unset_idle()

    def _send_ws(self, connection, message):
        # a frame may only be sent through a connection that has already
        # been upgraded, otherwise it would not be understood
        if not self._is_upgraded(connection):
            raise netius.NetiusError("Handshake not performed")

        # retrieves both the possible payloads of the event, note that
        # only one of them is expected to be set (as defined)
        text = message.get("text", None)
        data = message.get("bytes", None)

        # encodes the payload of the event into a frame using the opcode
        # that matches the kind of payload that has been provided
        if not text == None:
            encoded = netius.common.encode_ws(text, opcode=TEXT_OPCODE, mask=False)
        elif not data == None:
            encoded = netius.common.encode_ws(data, opcode=BINARY_OPCODE, mask=False)
        else:
            raise netius.NetiusError("No payload defined for send")

        # sends the frame through the connection, note that the raw send
        # operation is used as the payload is already framed, the application
        # may be suspended in case the connection is exhausted (back pressure)
        return self._send_pressure(connection, encoded, raw=True)

    def _send_close(self, connection, message):
        # a connection may only be closed once, as both the framing and
        # the state of it are no longer valid ones
        if connection.finished:
            raise netius.NetiusError("Connection already closed")

        # in case the handshake has not been performed the closing of the
        # connection is in fact the rejection of it, so a "normal" HTTP
        # response is sent to the client instead of a close frame
        if not self._is_upgraded(connection):
            connection.send_response(
                headers=dict(Connection="close"), code=CLOSE_REJECT, apply=True
            )
            connection.finished = True
            self._close(connection)
            return

        # builds the payload of the close frame with the code provided by
        # the application and sends it, closing the connection afterwards
        code = message.get("code", CLOSE_CODE)
        encoded = netius.common.encode_ws(
            struct.pack("!H", code), opcode=CLOSE_OPCODE, mask=False
        )
        connection.send(encoded)
        connection.finished = True
        self._close(connection)

    def _send_pressure(self, connection, data, raw=False):
        """
        Sends the provided data through the connection, suspending the
        application in case the connection is no longer able to take more
        payload, so that a fast producer is not able to outrun a slow
        consumer (back pressure).

        :type connection: Connection
        :param connection: The connection through which the data is going
        to be sent to the client.
        :type data: bytes
        :param data: The buffer of data that is going to be sent.
        :type raw: bool
        :param raw: If the data is already framed, meaning that it must be
        sent without any extra encoding applied to it.
        :rtype: Future
        :return: The future that the application must wait for before more
        payload is produced, or an invalid value in case the connection is
        still able to take more of it.
        """

        # verifies if the connection is exhausted, meaning that either the
        # payload pending in it has reached the limit or that the flow
        # control window of the stream has been closed
        exhausted = connection.is_exhausted()

        # in case the connection is still able to take more payload the
        # data is sent without any kind of waiting (no back pressure)
        if not exhausted:
            if raw:
                connection.send(data)
            else:
                connection.send_part(data, final=False)
            return None

        # otherwise the application is suspended until the data that has
        # just been sent reaches the connection (drains the buffer)
        future = self._future()
        callback = lambda _connection: self._resolve(future)
        if raw:
            connection.send(data, callback=callback)
        else:
            connection.send_part(data, final=False, callback=callback)
        return future

    def _resolve(self, future):
        # in case the future has been canceled in the mean time (eg: the
        # connection has been closed) there's nothing to be done, as the
        # application is no longer running
        if future.done():
            return

        # sets the result of the future resuming the application and runs
        # the pending work of it, so that no extra latency is introduced
        future.set_result(None)
        self._pump()

    def _push(self, connection, message):
        # in case there's an application waiting for a message the future
        # is resolved with it, resuming the execution of the application
        future = hasattr(connection, "receive_f") and connection.receive_f
        if future:
            connection.receive_f = None
            if not future.done():
                future.set_result(message)
                self._pump()
                return

        # otherwise the message is queued so that it's delivered by the
        # next call to the receive awaitable
        if not hasattr(connection, "messages"):
            return
        connection.messages.append(message)

    def _message_body(self, connection):
        # reads the next chunk of the payload determining if more of them
        # are still pending, note that a partial read means that the end
        # of the payload has been reached
        data = connection.body.read(BUFFER_SIZE)
        more_body = len(data) == BUFFER_SIZE

        # in case the complete payload has been consumed the buffer is
        # released, as it's no longer going to be used
        if not more_body:
            self._release_body(connection)

        return dict(type="http.request", body=data, more_body=more_body)

    def _on_task(self, connection, future):
        # in case the task is no longer the one associated with the connection
        # then it's a stale one, meaning that the connection has already been
        # released and re-used by another request (nothing to be done)
        if not connection.task == future:
            return

        # in case the task has been canceled in the mean time (eg: the
        # connection has been closed) there's nothing to be done, note that
        # the task is kept in the connection so that it's only considered
        # a free one once the response has been completely released
        if future.cancelled():
            return

        # retrieves a possible exception raised by the application and in
        # case there's one logs it, so that the reason for the failure of
        # the request is not lost (the response is handled next)
        exception = future.exception()
        if exception:
            self._log_exception(exception)

        # in case the application has completed the response there's
        # nothing else to be done (expected behaviour)
        if connection.finished:
            return

        # an application that returns without completing the response has
        # violated the specification, so the connection is terminated in
        # the way that is proper for the kind of scope in question
        if self._is_ws(connection):
            self._send_close(connection, dict())
        else:
            self._send_error(connection)

    def _send_error(self, connection):
        # in case the response has already been started there's no way of
        # signaling the error to the client, so the connection is simply
        # closed (the framing is no longer a reliable one)
        if not connection.started:
            connection.send_response(
                data="Internal Server Error",
                headers=dict(Connection="close"),
                code=500,
                apply=True,
            )
        self._close(connection)

    def _log_exception(self, exception):
        # logs the exception and then each of the lines of its traceback,
        # note that the traceback is the one attached to the exception as
        # the raising context is no longer the current one
        lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        self.warning(exception)
        for line in "".join(lines).splitlines():
            self.warning(line, extra=dict(stack=True))

    def _disconnect(self, connection):
        # verifies if there's an application running for the connection
        # and if that's not the case returns immediately, as there's no
        # one to be notified about the disconnection
        task = hasattr(connection, "task") and connection.task
        if not task:
            return

        # pushes the disconnect event that matches the kind of scope of
        # the connection, note that the delivery of it is a best effort
        # one as the application may be canceled before being resumed
        if self._is_ws(connection):
            self._push(connection, dict(type="websocket.disconnect", code=CLOSE_NONE))
        else:
            self._push(connection, dict(type="http.disconnect"))

    def _final(self, connection):
        # retrieves the parser of the current connection and then determines
        # if the current connection is meant to be kept alive
        parser = connection.parser
        keep_alive = parser.keep_alive

        # in case the connection is not meant to be kept alive must
        # must call the proper underlying close operation (expected)
        if not keep_alive:
            self._close(connection)
            return

        # the scope of the connection must be destroyed properly, avoiding
        # any possible memory leak for the current handling and then the
        # queue of pipelined requests must be flushed/processed, this
        # allows the connection to be re-used for new/pending requests
        self._release(connection)
        self._next_queue(connection)

    def _close(self, connection):
        connection.close(flush=True)

    def _release(self, connection):
        self._release_task(connection)
        self._release_body(connection)
        self._release_scope(connection)
        self._release_parser(connection)

    def _release_task(self, connection):
        # verifies if there's a task associated/running under the
        # current connection, if that's not the case returns immediately
        task = hasattr(connection, "task") and connection.task
        if not task:
            return

        # runs the cancel operation on the task, note that this
        # operation is only performed in case the task is still
        # under the running state (normal operation)
        task.cancel()

        # unsets the task from the connection as it's no longer
        # associated with it (as it's considered closed)
        connection.task = None

    def _release_body(self, connection):
        # verifies if there's a payload buffer currently defined in the
        # connection so that it may be closed, this is mandatory to
        # avoid any memory leak (or file descriptor one)
        body = hasattr(connection, "body") and connection.body
        if not body:
            return

        # closes the buffer and unsets it from the connection so that
        # it may no longer be used by any chunk of logic code
        body.close()
        connection.body = None

    def _release_scope(self, connection):
        # tries to retrieve the scope map for the current connection
        # and in case it does not exists returns immediately
        scope = hasattr(connection, "scope") and connection.scope
        if not scope:
            return

        # removes the complete set of key to value associations in the
        # map and unsets the scope value in the current connection
        scope.clear()
        connection.scope = None

    def _release_parser(self, connection):
        # closes the current file objects in the parser, note that the
        # parser still remains active, this operation only clears the
        # current memory structures associated with the parser
        connection.parser.close()

    def _release_queue(self, connection):
        # tries to retrieve a possible defined queue for the provided
        # connection in case it does not exist returns immediately as
        # there's no queue element to be release/cleared
        queue = hasattr(connection, "queue") and connection.queue
        if not queue:
            return

        # iterates over the complete set of queue elements (scope based
        # tuples) to clear their elements properly
        for scope, body in queue:
            # closes the buffer with the payload of the request as it's
            # not going to be handled by any application
            if body:
                body.close()

            # empties the map key references so that no more access
            # to the map is possible (avoids leaks)
            scope.clear()

        # removes the complete set of elements from the queue while
        # maintaining the original list reference/instance
        del queue[:]

    def _start_lifespan(self):
        # in case the lifespan protocol is not enabled for the current
        # server returns immediately, no application is started
        if not self.lifespan:
            return

        # builds the scope of the lifespan protocol and resets the state
        # associated with it, as a new "session" is going to be started
        scope = dict(
            type="lifespan",
            asgi=dict(version=ASGI_VERSION, spec_version=LIFESPAN_VERSION),
        )
        self.lifespan_v = None
        self.lifespan_m = None
        self.lifespan_f = None
        self.lifespan_q = []

        # runs the application under the lifespan scope, note that unlike
        # the connection ones this application is expected to be running
        # for the complete lifetime of the server
        coroutine = self._call_app(
            scope, self._build_receive_lifespan(), self._build_send_lifespan()
        )
        self.lifespan_t = self._ensure(coroutine)
        self.lifespan_t.add_done_callback(self._on_lifespan)

        # sends the startup event to the application and waits for the
        # acknowledgment of it, so that no request is handled before the
        # application is ready to handle it
        self._push_lifespan(dict(type="lifespan.startup"))
        self._wait_lifespan("lifespan.startup")

        # in case the application reported a failure in the startup the
        # serving of the requests may not proceed, as it would be performed
        # against a partially initialized application (as defined)
        if self.lifespan_v == "lifespan.startup.failed":
            raise netius.NetiusError("Lifespan startup failed: %s" % self._lifespan_m())

    def _stop_lifespan(self):
        # in case there's no application running under the lifespan scope
        # there's nothing pending to be done (returns immediately)
        if not self.lifespan_t:
            return

        # sends the shutdown event to the application and waits for the
        # acknowledgment of it, so that a graceful shutdown is performed
        self._push_lifespan(dict(type="lifespan.shutdown"))
        self._wait_lifespan("lifespan.shutdown")

        # unsets the task of the lifespan protocol as the server is no
        # longer running (avoids any extra event handling)
        self.lifespan_t = None

    def _wait_lifespan(self, name):
        # calculates the time limit for the waiting operation, after it
        # the server proceeds even if no acknowledgment has been received
        limit = time.time() + LIFESPAN_TIMEOUT

        # runs the event loop "by hand" until the application acknowledges
        # the event, note that this is required as the event loop is not
        # running while the server is either starting or stopping
        while True:
            if self.lifespan_v and self.lifespan_v.startswith(name):
                break
            if not self.lifespan_t:
                break
            if time.time() > limit:
                self.warning("Timeout waiting for '%s' acknowledgment" % name)
                break
            self.ticks()
            time.sleep(LIFESPAN_INTERVAL)

        # in case the application reported a failure for the event the
        # message provided by it is logged, as required by the specification
        if self.lifespan_v == name + ".failed":
            self.warning(
                "Received '%s' from the application: %s"
                % (self.lifespan_v, self._lifespan_m())
            )

    def _build_receive_lifespan(self):
        async def receive():
            # in case there's a message already queued for the lifespan
            # protocol it's returned immediately, as no waiting is required
            if self.lifespan_q:
                return self.lifespan_q.pop(0)

            # the concurrent usage of the receive awaitable is not allowed
            # by the specification, as the delivery of the events would
            # become an undefined operation
            if self.lifespan_f:
                raise netius.NetiusError("Receive already in use")

            # otherwise a future is created and stored so that the next
            # message pushed into it resumes the application
            future = self._future()
            self.lifespan_f = future
            return await future

        return receive

    def _build_send_lifespan(self):
        async def send(message):
            self.lifespan_v = message.get("type", None)
            self.lifespan_m = message.get("message", None)
            self.debug("Received '%s' from the application" % self.lifespan_v)

        return send

    def _push_lifespan(self, message):
        # in case the application is waiting for a message the future is
        # resolved with it, resuming the execution of the application
        future = self.lifespan_f
        if future:
            self.lifespan_f = None
            if not future.done():
                future.set_result(message)
                self._pump()
                return

        # otherwise the message is queued so that it's delivered by the
        # next call to the receive awaitable
        self.lifespan_q.append(message)

    def _lifespan_m(self):
        # retrieves the message that the application associated with the
        # last of the lifespan events, defaulting to a placeholder one
        return self.lifespan_m if self.lifespan_m else "no message"

    def _on_lifespan(self, future):
        # unsets the task of the lifespan protocol as it's no longer
        # running, meaning that no more events may be delivered to it
        self.lifespan_t = None

        # in case the task has been canceled or has completed properly
        # there's nothing else to be done (expected behaviour)
        if future.cancelled():
            return
        exception = future.exception()
        if not exception:
            return

        # an exception raised under the lifespan scope means that the
        # application does not support the protocol, so it's disabled and
        # the server proceeds as if it was never enabled (as defined)
        self.lifespan = False
        self.debug("Lifespan protocol not supported by the application")
        self.debug(exception)

    def _ensure(self, coroutine):
        # under the asyncio mode of execution the coroutine is run as a
        # "real" asyncio task, so that the complete set of the asyncio
        # primitives (eg: task groups) is available to the application
        if self.asyncio:
            return self.loop_asyncio.create_task(coroutine)
        return self.ensure(coroutine, future=self._future())

    def _future(self):
        # builds the future using the infra-structure that matches the
        # mode of execution, as an application may only await for a future
        # that belongs to the loop that is running it, note that the future
        # is bound to the server and never to the "global" event loop
        if self.asyncio:
            return self.loop_asyncio.create_future()
        return netius.Future(loop=self)

    def _pump(self, limit=PUMP_LIMIT):
        """
        Runs the pending work of the event loop that drives the
        applications, note that under the native mode of execution
        this is a no operation, as the applications are driven by
        the event loop of the server itself.

        :type limit: int
        :param limit: The maximum number of iterations of the loop
        that are going to be run, bounding the amount of time that
        an application may starve the event loop of the server.
        """

        # in case the asyncio mode is not enabled or the loop is already
        # being pumped returns immediately, as the re-entrant execution
        # of an event loop is not a possible operation
        if not self.asyncio:
            return
        if self.pumping:
            return

        # retrieves the reference to both the asyncio module and the loop
        # that drives the applications (the one to be pumped)
        asyncio = netius.get_asyncio()
        loop = self.loop_asyncio

        # saves the loop that asyncio considers to be the running one, as
        # the running of the loop of the applications unsets it, breaking
        # the compatibility layer that netius installs for its own loop
        running = self._running_loop(asyncio)
        self._set_running_loop(asyncio, None)

        self.pumping = True

        try:
            # runs the loop for as many iterations as the ones required
            # to exhaust the callbacks that are ready to be executed, note
            # that the number of them is bounded (avoids starvation)
            for _index in range(limit):
                loop.call_soon(loop.stop)
                loop.run_forever()
                if not self._is_ready(loop):
                    break
        finally:
            self.pumping = False
            self._set_running_loop(asyncio, running)

    def _is_ready(self, loop):
        # verifies if the provided loop still has callbacks that are ready
        # to be executed, note that in case such information is not exposed
        # by the loop a single iteration of it is assumed
        ready = getattr(loop, "_ready", None)
        if ready == None:
            return False
        return len(ready) > 0

    def _running_loop(self, asyncio):
        if not hasattr(asyncio, "_get_running_loop"):
            return None
        return asyncio._get_running_loop()

    def _set_running_loop(self, asyncio, loop):
        if not hasattr(asyncio, "_set_running_loop"):
            return
        asyncio._set_running_loop(loop)

    def _call_app(self, scope, receive, send):
        # in case the application complies with the legacy (double callable)
        # interface it's first called with the scope so that the "real"
        # application is retrieved and then called with the awaitables
        if self.legacy_app:
            return self.app(scope)(receive, send)
        return self.app(scope, receive, send)

    def _accept_key(self, parser):
        """
        Computes the accept key for the WebSocket handshake of the
        request associated with the provided parser.

        The value is calculated according to the specification, by
        hashing the key sent by the client together with the magic
        value of the protocol.

        :type parser: HTTPParser
        :param parser: The parser of the request for which the accept
        key is going to be calculated.
        :rtype: String
        :return: The accept key to be sent back to the client as part
        of the handshake response.
        :see: http://tools.ietf.org/html/rfc6455
        """

        socket_key = parser.headers.get("sec-websocket-key", None)
        if not socket_key:
            raise netius.NetiusError("No socket key found in headers")

        value = netius.legacy.bytes(socket_key + ws.WSServer.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        accept_key = base64.b64encode(hash_digest)
        accept_key = netius.legacy.str(accept_key)
        return accept_key

    def _headers(self, parser):
        """
        Converts the headers of the provided parser into the sequence
        of byte based key to value tuples that is expected to be set
        under the headers key of the scope.

        Note that the name of the headers is lower cased and that a
        repeated header is converted into multiple tuples, as defined
        by the specification.

        :type parser: HTTPParser
        :param parser: The parser from which the headers are going to
        be retrieved and converted.
        :rtype: List
        :return: The sequence of byte based key to value tuples for the
        headers of the request.
        """

        headers = []
        for key, value in netius.legacy.iteritems(parser.headers):
            key = netius.legacy.bytes(key.lower())
            if not isinstance(value, (list, tuple)):
                value = (value,)
            for _value in value:
                headers.append((key, netius.legacy.bytes(_value)))
        return headers

    def _headers_map(self, headers):
        """
        Converts the sequence of byte based key to value tuples sent by
        the application into the map of headers that is expected by the
        underlying infra-structure.

        A header that is repeated is converted into a list of values, so
        that every one of them is sent to the client.

        :type headers: List
        :param headers: The sequence of key to value tuples that is going
        to be converted into a map.
        :rtype: Dictionary
        :return: The map of headers with the names normalized according
        to the HTTP conventions.
        """

        headers_m = dict()
        for key, value in headers:
            key = netius.legacy.str(key)
            value = netius.legacy.str(value)
            if key in headers_m:
                sequence = headers_m[key]
                if not isinstance(sequence, list):
                    sequence = [sequence]
                sequence.append(value)
                value = sequence
            headers_m[key] = value
        self._headers_upper(headers_m)
        return headers_m

    def _subprotocols(self, parser):
        # retrieves the value of the header that announces the sub
        # protocols supported by the client, defaulting to an empty
        # sequence in case it's not defined
        subprotocols = parser.headers.get("sec-websocket-protocol", None)
        if not subprotocols:
            return []
        if isinstance(subprotocols, (list, tuple)):
            subprotocols = ",".join(subprotocols)
        return [value.strip() for value in subprotocols.split(",")]

    def _version(self, parser):
        # converts the string version of the protocol (eg: HTTP/1.1) into
        # the simple version value expected by the specification
        version_s = parser.version_s
        if not version_s:
            return "1.1"
        return version_s.split("/", 1)[-1]

    def _close_code(self, data):
        # a close frame that carries no payload means that no code has
        # been provided by the client (as defined by the specification)
        if len(data) < 2:
            return CLOSE_NONE
        return struct.unpack("!H", data[:2])[0]

    def _get_buffer(self, connection, delete=True):
        # retrieves the (pending) buffer of data of the connection joining
        # its various parts, optionally deleting them from the connection
        if not connection.ws_buffer:
            return b""
        buffer = b"".join(connection.ws_buffer)
        if delete:
            del connection.ws_buffer[:]
        return buffer

    def _is_upgrade(self, connection, parser):
        # the upgrade mechanism is not part of the HTTP/2 specification so
        # a stream of such a connection may never be upgraded, sending the
        # handshake through it would corrupt the framing of the connection
        if not isinstance(connection, http.HTTPConnection):
            return False

        # a websocket upgrade request must announce both the protocol to
        # which the connection is going to be upgraded and the upgrade
        # itself under the connection header (as defined)
        upgrade = parser.headers.get("upgrade", None)
        if not upgrade:
            return False
        if not upgrade.strip().lower() == "websocket":
            return False
        connection_s = parser.headers.get("connection", "")
        return "upgrade" in connection_s.lower()

    def _is_upgraded(self, connection):
        return bool(getattr(connection, "ws_handshake", False))

    def _is_ws(self, connection):
        scope = hasattr(connection, "scope") and connection.scope
        if not scope:
            return False
        return scope.get("type", None) == "websocket"

    @classmethod
    def _is_legacy(cls, app):
        """
        Determines if the provided application complies with the legacy
        (double callable) interface of the 2.0 version of the ASGI
        specification instead of the current (single callable) one.

        :type app: Callable
        :param app: The application for which the interface version is
        going to be determined.
        :rtype: bool
        :return: If the provided application is a legacy (double callable)
        one, meaning that it must be adapted.
        :see: https://asgi.readthedocs.io/en/latest/specs/main.html
        """

        if inspect.isclass(app):
            return True
        if netius.is_coroutine(app):
            return False
        call = getattr(app, "__call__", None)
        return not netius.is_coroutine(call)

    def _decode(self, value):
        """
        Decodes the provided quoted value, normalizing it according
        to the ASGI specification.

        Note that unlike the wsgi counterpart the resulting value is
        a "native" string, as the specification requires the percent
        encoded sequences to be decoded into characters.

        :type value: String
        :param value: The quoted value that should be normalized and
        decoded according to the asgi specification.
        :rtype: String
        :return: The normalized version of the provided quoted value
        that is ready to be provided as part of the scope map.
        :see: https://asgi.readthedocs.io/en/latest/specs/www.html
        """

        return netius.legacy.unquote(value)


async def hello_app(scope, receive, send):
    """
    Simple ASGI application that answers every request with a plain
    text hello world message, meant to be used for demonstration
    and testing purposes.

    :type scope: Dictionary
    :param scope: The scope of the connection for which the application
    is going to be called.
    :type receive: Coroutine
    :param receive: The awaitable that provides the events of the
    connection to the application.
    :type send: Coroutine
    :param send: The awaitable that sends the events produced by the
    application back to the client.
    """

    if not scope["type"] == "http":
        return

    contents = b"Hello World"
    await send(
        dict(
            type="http.response.start",
            status=200,
            headers=[
                (b"content-length", netius.legacy.bytes(str(len(contents)))),
                (b"content-type", b"text/plain"),
            ],
        )
    )
    await send(dict(type="http.response.body", body=contents))


def load_app(value):
    """
    Loads the application defined by the provided value, that should
    be defined using the typical module and attribute separated by a
    colon notation (eg: my_module:app).

    :type value: String
    :param value: The reference to the application that is going to
    be imported and loaded.
    :rtype: Callable
    :return: The application object that has been loaded from the
    provided reference value.
    """

    if not ":" in value:
        raise netius.NetiusError("Invalid application reference '%s'" % value)

    module_s, attribute_s = value.split(":", 1)
    module = __import__(module_s)
    for part in module_s.split(".")[1:]:
        module = getattr(module, part)

    if not hasattr(module, attribute_s):
        raise netius.NetiusError("No application '%s' found" % value)

    return getattr(module, attribute_s)
