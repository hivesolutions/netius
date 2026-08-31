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
import importlib
import unittest

import netius
import netius.common
import netius.servers

REQUEST = b"GET /hello?name=world HTTP/1.1\r\nHost: netius.hive.pt\r\n\r\n"
""" The raw contents of a simple request to be used as the
base one for the majority of the tests """

REQUEST_WS = (
    b"GET /ws HTTP/1.1\r\n"
    b"Host: netius.hive.pt\r\n"
    b"Upgrade: websocket\r\n"
    b"Connection: Upgrade\r\n"
    b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
    b"Sec-WebSocket-Protocol: chat, superchat\r\n"
    b"Sec-WebSocket-Version: 13\r\n\r\n"
)
""" The raw contents of a websocket upgrade request, the key
is the one used by the examples of the specification """


class ASGIServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if not netius.is_neo():
            self.skipTest("Skipping test: async/await unavailable")
        self.servers = []
        self.connections = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for connection in self.connections:
            connection.parser.destroy()
        for server in self.servers:
            server.cleanup()

    def test_init(self):
        server = self._make_server()

        self.assertNotEqual(server.app, None)
        self.assertEqual(server.mount, "")
        self.assertEqual(server.mount_l, 0)
        self.assertEqual(server.compressed_limit, netius.servers.asgi.COMPRESSED_LIMIT)
        self.assertEqual(server.lifespan, True)
        self.assertEqual(server.asyncio, False)
        self.assertEqual(server.loop_asyncio, None)
        self.assertEqual(server.legacy_app, False)
        self.assertEqual(server.lifespan_t, None)

    def test_init_values(self):
        server = self._make_server(
            mount="/api", compressed_limit=1024, lifespan=False, asyncio=True
        )

        self.assertEqual(server.mount, "/api")
        self.assertEqual(server.mount_l, 4)
        self.assertEqual(server.compressed_limit, 1024)
        self.assertEqual(server.lifespan, False)
        self.assertEqual(server.asyncio, True)
        self.assertNotEqual(server.loop_asyncio, None)

    def test_cleanup(self):
        server = self._make_server(asyncio=True)
        loop = server.loop_asyncio

        server.cleanup()

        # the loop that drives the applications is owned by the server so
        # it must be closed together with it (avoids leaking of resources)
        self.assertEqual(loop.is_closed(), True)
        self.assertEqual(server.loop_asyncio, None)

    def test_on_connection_c(self):
        server = self._make_server(max_pending=1024)
        connection = self._make_connection(server)
        connection.max_pending = -1

        server.on_connection_c(connection)

        # the limit of the sending buffer of the server must be applied to
        # the connection, as it's the one that bounds the back pressure
        self.assertEqual(connection.max_pending, 1024)

    def test_on_connection_d(self):
        server = self._make_server(app=self._app_receive)
        connection = self._make_connection(server)
        connection.parse(REQUEST)

        server.on_connection_d(connection)

        # the destruction of the connection must both notify the application
        # about it and release the structures associated with the request
        self.assertEqual(connection.messages, [dict(type="http.disconnect")])
        self.assertEqual(connection.task, None)
        self.assertEqual(connection.scope, None)
        self.assertEqual(connection.body, None)

    def test_on_serve(self):
        server = self._make_server(app=self._app_lifespan)
        server.on_serve()

        # the startup event must have been both delivered to the application
        # and acknowledged by it before the serving of requests starts
        self.assertEqual(server.lifespan_v, "lifespan.startup.complete")
        self.assertNotEqual(server.lifespan_t, None)

    def test_on_serve_env(self):
        server = self._make_server(app=self._app_lifespan)
        server.env = True

        with netius.conf_override("COMPRESSED_LIMIT", "1024"):
            with netius.conf_override("LIFESPAN", "0"):
                server.on_serve()

        # the configuration of the server may be overridden by the
        # environment, as it happens with the rest of the servers
        self.assertEqual(server.compressed_limit, 1024)
        self.assertEqual(server.lifespan, False)
        self.assertEqual(server.lifespan_t, None)

    def test_on_stop(self):
        server = self._make_server(app=self._app_lifespan)
        server.on_serve()

        server.on_stop()

        # the shutdown event must have been acknowledged by the application
        # and the task released, as the server is no longer running
        self.assertEqual(server.lifespan_v, "lifespan.shutdown.complete")
        self.assertEqual(server.lifespan_t, None)

    def test_on_data(self):
        server = self._make_server()
        connection = self._make_connection(server)

        server.on_data(connection, REQUEST)

        # while the connection has not been upgraded the data is handled
        # by the HTTP infra-structure, so it must reach the parser
        self.assertEqual(connection.parser.method, "get")

        connection.ws_handshake = True
        connection.ws_buffer = []
        connection.messages = []
        connection.receive_f = None

        server.on_data(connection, netius.common.encode_ws("frame"))

        # once upgraded the data is a sequence of frames, so it must be
        # decoded and delivered to the application instead
        self.assertEqual(
            connection.messages, [dict(type="websocket.receive", text="frame")]
        )

    def test_on_data_partial(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.ws_handshake = True
        connection.ws_buffer = []
        connection.messages = []
        connection.receive_f = None

        frame = netius.common.encode_ws("partial")
        server.on_data(connection, frame[:4])

        # an incomplete frame may not be decoded so it must be buffered
        # while waiting for the remaining part of it
        self.assertEqual(connection.messages, [])
        self.assertEqual(connection.ws_buffer, [frame[:4]])

        server.on_data(connection, frame[4:])

        self.assertEqual(
            connection.messages, [dict(type="websocket.receive", text="partial")]
        )
        self.assertEqual(connection.ws_buffer, [])

    def test_on_data_http(self):
        server = self._make_server(app=self._app_receive)
        connection = self._make_connection(server)

        connection.parse(REQUEST)

        # the arrival of a complete request must build the scope for it
        # and start the application that is going to handle it
        self.assertEqual(connection.scope["type"], "http")
        self.assertEqual(connection.scope["path"], "/hello")
        self.assertNotEqual(connection.task, None)

    def test_on_data_http_queue(self):
        server = self._make_server(app=self._app_receive)
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.parse(REQUEST)

        # a request that arrives while another one is still being handled
        # is queued, so that the pipelining of them is possible
        self.assertEqual(len(connection.queue), 1)
        self.assertEqual(connection.queue[0][0]["type"], "http")

        connection.parse(REQUEST)

        # the queue is a shared one, so the requests that follow are
        # appended to the one that already exists
        self.assertEqual(len(connection.queue), 2)

    def test_on_data_http_pending(self):
        server = self._make_server(app=netius.servers.asgi.hello_app)
        connection = self._make_connection(server, deliver=False)

        connection.parse(REQUEST)
        self._run(server)

        # the application has completed the response but the flushing of it
        # is still pending, so the connection is not yet a free one
        self.assertEqual(connection.finished, True)
        self.assertNotEqual(connection.task, None)

        connection.parse(REQUEST)

        # a request that arrives while the response of the previous one has
        # not been released must be queued, as the releasing of it would
        # otherwise cancel the application that is handling the new one
        self.assertEqual(len(connection.queue), 1)

        self._deliver(connection)
        self._run(server)
        self._deliver(connection)

        # the releasing of the response dispatches the queued request, whose
        # response must reach the client as well (no request is lost)
        self.assertEqual(connection.queue, [])
        self.assertEqual(self._data(connection).count(b"Hello World"), 2)

    def test_on_data_http_ws(self):
        server = self._make_server(app=self._app_receive)
        connection = self._make_connection(server)

        connection.parse(REQUEST_WS)

        # an upgrade request must be handled under the websocket scope
        # and the connect event queued as the first one of it
        self.assertEqual(connection.scope["type"], "websocket")
        self.assertEqual(connection.body, None)
        self.assertEqual(connection.messages, [dict(type="websocket.connect")])

    def test_on_scope(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        scope = dict(type="http")

        server.on_scope(connection, scope, body=None)

        # the starting of a new scope must reset the complete set of state
        # associated with the handling of a request
        self.assertEqual(connection.scope, scope)
        self.assertEqual(connection.messages, [])
        self.assertEqual(connection.receive_f, None)
        self.assertEqual(connection.started, False)
        self.assertEqual(connection.finished, False)
        self.assertNotEqual(connection.task, None)

    def test_on_data_ws(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None

        server.on_data_ws(connection, netius.servers.asgi.TEXT_OPCODE, b"hello")
        server.on_data_ws(connection, netius.servers.asgi.BINARY_OPCODE, b"raw")

        # the kind of payload of the event depends on the operation code
        # of the frame that has been received (as defined)
        self.assertEqual(
            connection.messages,
            [
                dict(type="websocket.receive", text="hello"),
                dict(type="websocket.receive", bytes=b"raw"),
            ],
        )

    def test_on_data_ws_ping(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None

        server.on_data_ws(connection, netius.servers.asgi.PING_OPCODE, b"beat")

        # a ping frame is answered by the server with a pong one carrying
        # the same payload, the application is never notified about it
        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(decoded, b"beat")
        self.assertEqual(connection.messages, [])

        server.on_data_ws(connection, netius.servers.asgi.PONG_OPCODE, b"beat")

        self.assertEqual(connection.messages, [])

    def test_on_data_ws_close(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.finished = False

        server.on_data_ws(
            connection, netius.servers.asgi.CLOSE_OPCODE, struct.pack("!H", 1001)
        )

        # the closing handshake requires a close frame to be sent back to
        # the client, echoing the code that has been provided by it
        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(struct.unpack("!H", decoded[:2])[0], 1001)

        # the close code of the frame must be reported to the application
        # and the connection closed, as the other end is gone
        self.assertEqual(
            connection.messages, [dict(type="websocket.disconnect", code=1001)]
        )
        self.assertEqual(connection.finished, True)
        self.assertEqual(connection.closed, True)

    def test_on_data_ws_close_empty(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.finished = False

        server.on_data_ws(connection, netius.servers.asgi.CLOSE_OPCODE, b"")

        # a client that provides no close code is reported to the application
        # with the reserved one, that may never be sent in a frame, so the
        # frame that is echoed back carries no payload at all
        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(decoded, b"")
        self.assertEqual(
            connection.messages,
            [dict(type="websocket.disconnect", code=netius.servers.asgi.CLOSE_NONE)],
        )

    def test_on_data_ws_close_sent(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.finished = True

        server.on_data_ws(
            connection, netius.servers.asgi.CLOSE_OPCODE, struct.pack("!H", 1000)
        )

        # with a close frame already sent by the server the handshake is
        # complete, so no extra frame may be sent
        self.assertEqual(self._data(connection), b"")
        self.assertEqual(connection.closed, True)

    def test_on_data_ws_fragmented(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.ws_opcode = None
        connection.ws_frames = []

        server.on_data_ws(
            connection, netius.servers.asgi.TEXT_OPCODE, b"hel", final=False
        )

        # while the final frame of the message has not been received the
        # payload is accumulated, with no event delivered
        self.assertEqual(connection.messages, [])
        self.assertEqual(connection.ws_frames, [b"hel"])

        server.on_data_ws(
            connection, netius.servers.asgi.CONTINUATION_OPCODE, b"lo", final=True
        )

        # the message is delivered as a single event using the kind of
        # payload announced by the first frame of it
        self.assertEqual(
            connection.messages, [dict(type="websocket.receive", text="hello")]
        )
        self.assertEqual(connection.ws_frames, [])
        self.assertEqual(connection.ws_opcode, None)

    def test_on_data_ws_stray(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.ws_opcode = None
        connection.ws_frames = []

        server.on_data_ws(connection, netius.servers.asgi.CONTINUATION_OPCODE, b"stray")

        # a continuation frame that does not continue any message is an
        # invalid one, so it must be discarded
        self.assertEqual(connection.messages, [])
        self.assertEqual(connection.ws_frames, [])

    def test__next_queue(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)

        # with no queue associated with the connection there's nothing to
        # be done, the same applying to an empty one
        server._next_queue(connection)
        connection.queue = []
        server._next_queue(connection)

        self.assertEqual(connection.scope["path"], "/hello")

        scope = dict(type="http")
        connection.queue.append((scope, None))
        connection.task = None

        server._next_queue(connection)

        # the first scope of the queue must be the one to be handled, being
        # removed from the queue as part of the operation
        self.assertEqual(connection.scope, scope)
        self.assertEqual(connection.queue, [])

    def test__build_scope(self):
        server = self._make_server(mount="/api")
        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST)

        scope = server._build_scope(connection, parser)

        self.assertEqual(scope["type"], "http")
        self.assertEqual(scope["asgi"]["version"], netius.servers.asgi.ASGI_VERSION)
        self.assertEqual(
            scope["asgi"]["spec_version"], netius.servers.asgi.SPEC_VERSION
        )
        self.assertEqual(scope["http_version"], "1.1")
        self.assertEqual(scope["method"], "GET")
        self.assertEqual(scope["scheme"], "http")
        self.assertEqual(scope["path"], "/hello")
        self.assertEqual(scope["raw_path"], b"/hello")
        self.assertEqual(scope["query_string"], b"name=world")
        self.assertEqual(scope["root_path"], "/api")
        self.assertEqual(scope["headers"], [(b"host", b"netius.hive.pt")])
        self.assertEqual(scope["client"], ("127.0.0.1", 5000))
        self.assertEqual(scope["server"], (server.host, server.port))

    def test__build_scope_scheme(self):
        server = self._make_server()
        connection = self._make_connection(server, ssl=True)
        parser = self._parse(connection, REQUEST)

        scope = server._build_scope(connection, parser)

        # a connection established under a secure channel must be reported
        # to the application using the proper scheme value
        self.assertEqual(scope["scheme"], "https")

        connection = self._make_connection(server)
        parser = self._parse(
            connection,
            b"GET / HTTP/1.1\r\nHost: netius.hive.pt\r\nX-Forwarded-Proto: https\r\n\r\n",
        )

        scope = server._build_scope(connection, parser)

        # the protocol announced by a proxy in front of the server takes
        # precedence over the one of the connection itself
        self.assertEqual(scope["scheme"], "https")

    def test__build_scope_ws(self):
        server = self._make_server()
        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST_WS)

        scope = server._build_scope_ws(connection, parser)

        self.assertEqual(scope["type"], "websocket")
        self.assertEqual(scope["scheme"], "ws")
        self.assertEqual(scope["path"], "/ws")
        self.assertEqual(scope["subprotocols"], ["chat", "superchat"])
        self.assertEqual("method" in scope, False)

        connection = self._make_connection(server, ssl=True)
        parser = self._parse(connection, REQUEST_WS)

        scope = server._build_scope_ws(connection, parser)

        self.assertEqual(scope["scheme"], "wss")

    def test__build_receive(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = [dict(type="websocket.connect")]
        connection.body = None
        connection.receive_f = None

        receive = server._build_receive(connection)

        # a message that is already queued must be delivered immediately
        # as there's no reason for the application to be suspended
        message = self._resolve(receive())
        self.assertEqual(message, dict(type="websocket.connect"))

        # with no message queued the application is suspended until one
        # is pushed into the connection (resuming it)
        coroutine = receive()
        future = self._suspend(coroutine)
        self.assertNotEqual(future, None)
        self.assertEqual(connection.receive_f, future)

        # the specification does not allow the concurrent usage of the
        # receive awaitable, as the delivery of the events would become
        # an undefined operation
        self.assertRaises(netius.NetiusError, self._suspend, receive())

        server._push(connection, dict(type="websocket.disconnect", code=1000))

        message = self._resolve(coroutine)
        self.assertEqual(message, dict(type="websocket.disconnect", code=1000))

    def test__build_receive_body(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.messages = []
        connection.receive_f = None
        connection.body = netius.legacy.BytesIO(b"payload")

        receive = server._build_receive(connection)

        # the payload of the request must be delivered to the application
        # as a request event, with no more of them pending
        message = self._resolve(receive())
        self.assertEqual(
            message, dict(type="http.request", body=b"payload", more_body=False)
        )
        self.assertEqual(connection.body, None)

    def test__build_send(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = False

        send = server._build_send(connection)

        self._resolve(send(dict(type="http.response.start", status=204, headers=[])))

        self.assertEqual(connection.started, True)

    def test__build_send_pressure(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        connection.started = True
        connection.finished = False
        connection.empty = False
        connection.pending_s = server.max_pending + 1

        send = server._build_send(connection)

        # a partial payload suspends the application until it reaches the
        # connection, so the awaitable may not be completed right away
        coroutine = send(dict(type="http.response.body", body=b"x", more_body=True))
        future = self._suspend(coroutine)

        self.assertEqual(future.done(), False)

        self._deliver(connection)

        self.assertEqual(self._resolve(coroutine), None)

    def test__send(self):
        server = self._make_server()
        connection = self._make_connection(server)
        calls = []

        # replaces the handlers of the events by ones that record their
        # usage, so that the routing of the messages may be verified
        server._send_start = lambda c, m: calls.append("start")
        server._send_body = lambda c, m: calls.append("body")
        server._send_accept = lambda c, m: calls.append("accept")
        server._send_ws = lambda c, m: calls.append("send")
        server._send_close = lambda c, m: calls.append("close")

        for message_t in (
            "http.response.start",
            "http.response.body",
            "websocket.accept",
            "websocket.send",
            "websocket.close",
        ):
            server._send(connection, dict(type=message_t))

        self.assertEqual(calls, ["start", "body", "accept", "send", "close"])

        # a message whose type is not part of the specification is an
        # error that must be reported to the application
        self.assertRaises(
            netius.NetiusError, server._send, connection, dict(type="http.invalid")
        )

    def test__send_start(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)

        server._send_start(
            connection,
            dict(
                status=200,
                headers=[(b"content-length", b"5"), (b"content-type", b"text/plain")],
            ),
        )

        data = self._data(connection)
        self.assertIn(b"HTTP/1.1 200 OK\r\n", data)
        self.assertIn(b"Content-Length: 5\r\n", data)
        self.assertIn(b"Content-Type: text/plain\r\n", data)
        self.assertIn(b"Connection: keep-alive\r\n", data)
        self.assertEqual(connection.started, True)

        # the headers of a response may only be sent once, as a new set
        # of them would invalidate the framing of the connection
        self.assertRaises(
            netius.NetiusError,
            server._send_start,
            connection,
            dict(status=200, headers=[]),
        )

    def test__send_start_empty(self):
        server = self._make_server()
        connection = self._make_connection(
            server, encoding=netius.common.CHUNKED_ENCODING
        )
        connection.parse(REQUEST)

        server._send_start(
            connection, dict(status=204, headers=[(b"content-length", b"11")])
        )

        # a response that may not carry a payload must never be sent using
        # the chunked encoding, as there's nothing to be framed
        self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)

        # neither may it announce a length for a payload that is not going
        # to be sent, as the client would wait for it forever
        self.assertEqual(b"Content-Length" in self._data(connection), False)
        self.assertEqual(connection.empty, True)

    def test__send_start_head(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(b"HEAD / HTTP/1.1\r\nHost: netius.hive.pt\r\n\r\n")

        server._send_start(
            connection, dict(status=200, headers=[(b"content-length", b"11")])
        )

        # the response to a HEAD request announces the length of the payload
        # that it would carry, but never the payload itself
        self.assertIn(b"Content-Length: 11\r\n", self._data(connection))
        self.assertEqual(connection.empty, True)

        connection.data = []
        server._send_body(connection, dict(body=b"Hello World"))

        self.assertEqual(self._data(connection), b"")

    def test__send_start_uncompressed(self):
        server = self._make_server(compressed_limit=8)
        connection = self._make_connection(server, encoding=netius.common.GZIP_ENCODING)
        connection.parse(REQUEST)

        server._send_start(
            connection, dict(status=200, headers=[(b"content-length", b"1024")])
        )

        # a payload larger than the limit may not be compressed, as the
        # cost of doing so would not be a reasonable one
        self.assertEqual(connection.current, netius.common.CHUNKED_ENCODING)

    def test__send_start_ranges(self):
        server = self._make_server()
        connection = self._make_connection(server, encoding=netius.common.GZIP_ENCODING)
        connection.parse(REQUEST)

        server._send_start(
            connection,
            dict(
                status=206,
                headers=[
                    (b"content-length", b"4"),
                    (b"accept-ranges", b"bytes"),
                    (b"content-range", b"bytes 0-3/8"),
                ],
            ),
        )

        # the re-encoding of a partial payload would invalidate the range
        # that is announced for it, so it may never be compressed
        self.assertEqual(connection.current, netius.common.CHUNKED_ENCODING)

    def test__send_start_length(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)

        server._send_start(connection, dict(status=200, headers=[]))

        # a response with no length announced for it may only be kept alive
        # in case a chunked encoding is being used to frame it
        self.assertEqual(connection.parser.keep_alive, False)

    def test__send_body(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = False
        connection.finished = False

        # the payload of a response may only be sent once the headers of
        # it have been sent, otherwise there's no framing for it
        self.assertRaises(
            netius.NetiusError, server._send_body, connection, dict(body=b"early")
        )

        connection.started = True

        future = server._send_body(connection, dict(body=b"partial", more_body=True))

        # while more payload is expected the response is not a finished
        # one, so no flushing of the connection may be performed
        self.assertEqual(self._data(connection), b"partial")
        self.assertEqual(connection.finished, False)

        # a connection that is still able to take more payload never
        # suspends the application that is producing it
        self.assertEqual(future, None)

        server._send_body(connection, dict(body=b"final"))

        self.assertEqual(self._data(connection), b"partialfinal")
        self.assertEqual(connection.finished, True)

        # a response that has been completed may no longer be extended
        # with more payload (the framing is closed)
        self.assertRaises(
            netius.NetiusError, server._send_body, connection, dict(body=b"late")
        )

    def test__send_body_pressure(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        connection.started = True
        connection.finished = False
        connection.empty = False

        # exhausts the sending buffer of the connection so that it's no
        # longer able to take more payload
        connection.pending_s = server.max_pending + 1

        future = server._send_body(connection, dict(body=b"partial", more_body=True))

        # while the payload has not reached the connection the application
        # remains suspended, no more payload may be produced by it
        self.assertEqual(future.done(), False)

        self._deliver(connection)

        self.assertEqual(future.done(), True)

        # a partial event that carries no payload has nothing to wait for,
        # so the application is never suspended by it
        future = server._send_body(connection, dict(more_body=True))

        self.assertEqual(future, None)

    def test__send_body_empty(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = True
        connection.finished = False

        server._send_body(connection, dict())

        # a response that carries no payload is a valid one, the flushing
        # of the connection is the operation that completes it
        self.assertEqual(connection.finished, True)

    def test__send_accept(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST_WS)

        server._send_accept(
            connection, dict(subprotocol="chat", headers=[(b"x-custom", b"value")])
        )

        data = self._data(connection)
        self.assertIn(b"HTTP/1.1 101 Switching Protocols\r\n", data)
        self.assertIn(b"Upgrade: websocket\r\n", data)
        self.assertIn(b"Connection: Upgrade\r\n", data)
        self.assertIn(b"Sec-Websocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n", data)
        self.assertIn(b"Sec-Websocket-Protocol: chat\r\n", data)
        self.assertIn(b"X-Custom: value\r\n", data)

        # the connection is no longer an HTTP one, so the data that follows
        # is handled as frames and the idle timeout no longer applies
        self.assertEqual(connection.ws_handshake, True)
        self.assertEqual(connection.ws_buffer, [])
        self.assertEqual(connection.ws_opcode, None)
        self.assertEqual(connection.ws_frames, [])

        # the handshake may only be performed once, as the connection has
        # already been upgraded by the first one
        self.assertRaises(netius.NetiusError, server._send_accept, connection, dict())

    def test__send_accept_plain(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST_WS)

        server._send_accept(connection, dict())

        # with no subprotocol negotiated by the application none may be
        # announced back to the client
        data = self._data(connection)
        self.assertIn(b"HTTP/1.1 101 Switching Protocols\r\n", data)
        self.assertEqual(b"Sec-Websocket-Protocol" in data, False)

    def test__send_ws(self):
        server = self._make_server()
        connection = self._make_connection(server)

        # a frame may only be sent through a connection whose handshake
        # has already been performed (upgraded one)
        self.assertRaises(
            netius.NetiusError, server._send_ws, connection, dict(text="hello")
        )

        connection.ws_handshake = True

        future = server._send_ws(connection, dict(text="hello"))

        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(decoded, b"hello")

        # a connection that is still able to take more payload never
        # suspends the application that is producing the frames
        self.assertEqual(future, None)

        # once the sending buffer of the connection is exhausted the
        # application is suspended until the frame reaches it
        connection.pending_s = server.max_pending + 1

        future = server._send_ws(connection, dict(text="hello"))

        self.assertEqual(future.done(), True)

        connection.pending_s = 0
        connection.data = []
        server._send_ws(connection, dict(bytes=b"raw"))

        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(decoded, b"raw")

        # an event that carries no payload at all is an invalid one, as
        # either the text or the bytes key must be set
        self.assertRaises(netius.NetiusError, server._send_ws, connection, dict())

    def test__send_close(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST_WS)
        connection.ws_handshake = True

        server._send_close(connection, dict(code=1001))

        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(struct.unpack("!H", decoded[:2])[0], 1001)
        self.assertEqual(connection.finished, True)
        self.assertEqual(connection.closed, True)

        # a connection may only be closed once, as both the framing and
        # the state of it are no longer valid ones
        self.assertRaises(netius.NetiusError, server._send_close, connection, dict())

    def test__send_close_reject(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST_WS)

        server._send_close(connection, dict())

        # closing a connection whose handshake has not been performed is
        # the rejection of it, so a "normal" response is sent instead
        self.assertIn(b"HTTP/1.1 403 Forbidden\r\n", self._data(connection))
        self.assertEqual(connection.closed, True)

    def test__resolve(self):
        server = self._make_server()
        future = server._future()

        server._resolve(future)

        self.assertEqual(future.done(), True)

        # a future that is no longer running means that the application has
        # been canceled, so there's no result to be set on it
        future = self._make_future(server, cancel=True)

        server._resolve(future)

        self.assertEqual(future.cancelled(), True)

    def test__push(self):
        server = self._make_server()
        connection = self._make_connection(server)

        # a connection that is not handling a scope has no place to store
        # the message, so it must be discarded
        server._push(connection, dict(type="http.disconnect"))

        connection.messages = []
        connection.receive_f = None

        server._push(connection, dict(type="http.disconnect"))

        self.assertEqual(connection.messages, [dict(type="http.disconnect")])

        # a future that is no longer running means that the application
        # has been canceled, so the message must be queued instead
        connection.messages = []
        connection.receive_f = self._make_future(server, cancel=True)

        server._push(connection, dict(type="http.disconnect"))

        self.assertEqual(connection.receive_f, None)
        self.assertEqual(connection.messages, [dict(type="http.disconnect")])

    def test__message_body(self):
        server = self._make_server()
        connection = self._make_connection(server)
        size = netius.servers.asgi.BUFFER_SIZE
        connection.body = netius.legacy.BytesIO(b"L" * (size + 1))

        message = server._message_body(connection)

        # a payload larger than the buffer must be delivered in multiple
        # events, with all of them but the last one announcing more
        self.assertEqual(message["more_body"], True)
        self.assertEqual(len(message["body"]), size)

        message = server._message_body(connection)

        self.assertEqual(message["more_body"], False)
        self.assertEqual(message["body"], b"L")
        self.assertEqual(connection.body, None)

    def test__on_task(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.finished = True
        connection.task = self._make_future(server)

        server._on_task(connection, connection.task)

        # an application that completed the response has nothing pending to
        # be done, note that the task is kept in the connection so that it's
        # only considered a free one once the response has been released
        self.assertNotEqual(connection.task, None)
        self.assertEqual(connection.closed, False)

    def test__on_task_stale(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = False
        connection.finished = False
        connection.task = self._make_future(server)

        server._on_task(connection, self._make_future(server))

        # a task that is no longer the one of the connection is a stale one,
        # meaning that the connection has already been re-used by another
        # request, so no response may be sent on behalf of it
        self.assertEqual(self._data(connection), b"")
        self.assertEqual(connection.closed, False)

    def test__on_task_canceled(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.finished = False

        future = self._make_future(server, cancel=True)
        connection.task = future
        server._on_task(connection, future)

        # a canceled task means that the connection is gone, so no response
        # may be sent through it (nothing to be done)
        self.assertEqual(connection.closed, False)

    def test__on_task_exception(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = False
        connection.finished = False

        future = self._make_future(server, exception=RuntimeError("boom"))
        connection.task = future
        server._on_task(connection, future)

        # a failure of the application must be reported to the client as
        # an internal error, so that it's not left waiting for a response
        self.assertIn(b"HTTP/1.1 500 Internal Server Error\r\n", self._data(connection))
        self.assertEqual(connection.closed, True)

    def test__on_task_ws(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST_WS)
        connection.scope = dict(type="websocket")
        connection.finished = False
        connection.ws_handshake = True
        connection.task = self._make_future(server)

        server._on_task(connection, connection.task)

        # an application that returns while the connection is still open
        # closes it, using the framing that matches the kind of scope
        decoded, _remaining = netius.common.decode_ws(self._data(connection))
        self.assertEqual(
            struct.unpack("!H", decoded[:2])[0], netius.servers.asgi.CLOSE_CODE
        )

    def test__send_error(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.started = True

        server._send_error(connection)

        # with the response already started there's no way of signaling
        # the error, so the connection is simply closed
        self.assertEqual(self._data(connection), b"")
        self.assertEqual(connection.closed, True)

    def test__log_exception(self):
        server = self._make_server()

        try:
            raise RuntimeError("boom")
        except RuntimeError as exception:
            server._log_exception(exception)

    def test__disconnect(self):
        server = self._make_server()
        connection = self._make_connection(server)

        # with no application running for the connection there's no one
        # to be notified about the disconnection
        connection.task = None
        server._disconnect(connection)

        connection.task = self._make_future(server)
        connection.scope = dict(type="websocket")
        connection.messages = []
        connection.receive_f = None

        server._disconnect(connection)

        self.assertEqual(
            connection.messages,
            [dict(type="websocket.disconnect", code=netius.servers.asgi.CLOSE_NONE)],
        )

    def test__final(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)
        connection.parser.keep_alive = True

        server._final(connection)

        # a connection that is meant to be kept alive must be released so
        # that it may be re-used by the requests that follow
        self.assertEqual(connection.closed, False)
        self.assertEqual(connection.scope, None)

        connection.parser.keep_alive = False
        server._final(connection)

        self.assertEqual(connection.closed, True)

    def test__release(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.parse(REQUEST)

        server._release(connection)

        self.assertEqual(connection.task, None)
        self.assertEqual(connection.body, None)
        self.assertEqual(connection.scope, None)

    def test__release_task(self):
        server = self._make_server()
        connection = self._make_connection(server)

        # a connection with no task associated with it has nothing to be
        # released (no operation)
        connection.task = None
        server._release_task(connection)

        connection.task = self._make_future(server, done=False)
        server._release_task(connection)

        self.assertEqual(connection.task, None)

    def test__release_body(self):
        server = self._make_server()
        connection = self._make_connection(server)

        connection.body = None
        server._release_body(connection)

        connection.body = netius.legacy.BytesIO(b"payload")
        server._release_body(connection)

        self.assertEqual(connection.body, None)

    def test__release_scope(self):
        server = self._make_server()
        connection = self._make_connection(server)

        connection.scope = None
        server._release_scope(connection)

        scope = dict(type="http")
        connection.scope = scope
        server._release_scope(connection)

        # the map of the scope must be emptied so that the references that
        # it holds are dropped (avoids leaks)
        self.assertEqual(scope, dict())
        self.assertEqual(connection.scope, None)

    def test__release_queue(self):
        server = self._make_server()
        connection = self._make_connection(server)

        server._release_queue(connection)

        scope = dict(type="http")
        body = netius.legacy.BytesIO(b"payload")
        connection.queue = [(scope, body), (dict(type="http"), None)]

        server._release_queue(connection)

        self.assertEqual(connection.queue, [])
        self.assertEqual(scope, dict())
        self.assertEqual(body.closed, True)

    def test__start_lifespan(self):
        server = self._make_server(app=self._app_lifespan, lifespan=False)

        # with the lifespan protocol disabled no application is started
        # under such scope (no operation)
        server._start_lifespan()

        self.assertEqual(server.lifespan_t, None)

    def test__start_lifespan_failed(self):
        server = self._make_server(app=self._app_lifespan_failed)

        # an application that fails to start may not be served, as the
        # requests would be handled by a partially initialized one
        self.assertRaises(netius.NetiusError, server._start_lifespan)

        self.assertEqual(server.lifespan_v, "lifespan.startup.failed")
        self.assertEqual(server.lifespan_m, "boom")

    def test__start_lifespan_unsupported(self):
        server = self._make_server(app=self._app_lifespan_unsupported)

        server._start_lifespan()

        # an application that fails under the lifespan scope does not
        # support the protocol, so it must be disabled
        self.assertEqual(server.lifespan, False)
        self.assertEqual(server.lifespan_t, None)

    def test__stop_lifespan(self):
        server = self._make_server(app=self._app_lifespan)

        # with no application running under the lifespan scope there's
        # nothing pending to be done (no operation)
        server._stop_lifespan()

        self.assertEqual(server.lifespan_t, None)

    def test__wait_lifespan(self):
        server = self._make_server(app=self._app_lifespan)
        server.lifespan_t = self._make_future(server)

        # the waiting operation is bounded in time so that an application
        # that never acknowledges the event is not able to block the server
        netius.servers.asgi_neo.LIFESPAN_TIMEOUT = -1.0
        try:
            server._wait_lifespan("lifespan.startup")
        finally:
            netius.servers.asgi_neo.LIFESPAN_TIMEOUT = 30.0

        self.assertEqual(server.lifespan_v, None)

    def test__push_lifespan(self):
        server = self._make_server()

        server._push_lifespan(dict(type="lifespan.startup"))

        self.assertEqual(server.lifespan_q, [dict(type="lifespan.startup")])

        # a future that is no longer running means that the application
        # is gone, so the message must be queued instead
        server.lifespan_q = []
        server.lifespan_f = self._make_future(server, cancel=True)

        server._push_lifespan(dict(type="lifespan.shutdown"))

        self.assertEqual(server.lifespan_f, None)
        self.assertEqual(server.lifespan_q, [dict(type="lifespan.shutdown")])

    def test__build_receive_lifespan(self):
        server = self._make_server()
        receive = server._build_receive_lifespan()

        server._push_lifespan(dict(type="lifespan.startup"))

        # a message that is already queued must be delivered immediately
        # as there's no reason for the application to be suspended
        message = self._resolve(receive())
        self.assertEqual(message, dict(type="lifespan.startup"))

        # with no message queued the application is suspended until one
        # is pushed into the server (resuming it)
        coroutine = receive()
        future = self._suspend(coroutine)
        self.assertEqual(server.lifespan_f, future)

        # the specification does not allow the concurrent usage of the
        # receive awaitable, as the delivery of the events would become
        # an undefined operation
        self.assertRaises(netius.NetiusError, self._suspend, receive())

        server._push_lifespan(dict(type="lifespan.shutdown"))

        message = self._resolve(coroutine)
        self.assertEqual(message, dict(type="lifespan.shutdown"))

    def test__on_lifespan(self):
        server = self._make_server()
        server.lifespan_t = self._make_future(server, done=False)

        server._on_lifespan(self._make_future(server, cancel=True))

        # a canceled task is the result of the stopping of the server and
        # never of a lack of support for the protocol
        self.assertEqual(server.lifespan, True)
        self.assertEqual(server.lifespan_t, None)

    def test__ensure(self):
        server = self._make_server()

        task = server._ensure(self._app_noop(dict(type="http"), None, None))
        self._run(server)

        self.assertEqual(task.done(), True)

        server = self._make_server(asyncio=True)

        # the asyncio mode is only able to run a "native" coroutine, so
        # the demo application is the one used for the verification
        task = server._ensure(
            netius.servers.asgi.hello_app(dict(type="lifespan"), None, None)
        )
        self._run(server)

        # under the asyncio mode the application is run as a "real" asyncio
        # task, so that the primitives of it become available
        self.assertEqual(task.done(), True)
        self.assertEqual(isinstance(task, netius.Future), False)

    def test__future(self):
        server = self._make_server()

        self.assertEqual(isinstance(server._future(), netius.Future), True)

        server = self._make_server(asyncio=True)

        self.assertEqual(isinstance(server._future(), netius.Future), False)

    def test__pump(self):
        server = self._make_server()

        # under the native mode of execution the pumping of the loop is
        # not a required operation (no operation)
        server._pump()

        server = self._make_server(asyncio=True)
        server.pumping = True

        # a loop may not be run in a re-entrant way, so a pump that is
        # requested from within another one is ignored
        server._pump()

        server.pumping = False
        state = []
        server.loop_asyncio.call_soon(lambda: state.append(True))

        server._pump()

        self.assertEqual(state, [True])

    def test__pump_limit(self):
        server = self._make_server(asyncio=True)
        state = []

        def callback():
            state.append(True)
            server.loop_asyncio.call_soon(callback)

        server.loop_asyncio.call_soon(callback)

        server._pump(limit=2)

        # the number of iterations of the loop is a bounded one, so that
        # a busy application is not able to starve the event loop
        self.assertEqual(len(state), 2)

    def test__is_ready(self):
        server = self._make_server(asyncio=True)

        self.assertEqual(server._is_ready(server.loop_asyncio), False)

        server.loop_asyncio.call_soon(lambda: None)

        self.assertEqual(server._is_ready(server.loop_asyncio), True)
        self.assertEqual(server._is_ready(object()), False)

    def test__running_loop(self):
        server = self._make_server(asyncio=True)

        # an interpreter that does not expose the currently running loop
        # must be handled gracefully (no compatibility layer)
        self.assertEqual(server._running_loop(object()), None)
        server._set_running_loop(object(), None)

    def test__call_app(self):
        server = self._make_server(app=self._app_legacy)

        self.assertEqual(server.legacy_app, True)

        coroutine = server._call_app(dict(type="http"), None, None)
        task = server._ensure(coroutine)
        self._run(server)

        # a legacy application is first called with the scope so that the
        # "real" application is retrieved and then called with the rest
        self.assertEqual(task.done(), True)
        self.assertEqual(task.exception(), None)

    def test__accept_key(self):
        server = self._make_server()
        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST_WS)

        accept_key = server._accept_key(parser)

        # the accept key is the one of the example of the specification
        # so that the compliance of the calculus may be verified
        self.assertEqual(accept_key, "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST)

        self.assertRaises(netius.NetiusError, server._accept_key, parser)

    def test__headers(self):
        server = self._make_server()
        connection = self._make_connection(server)
        parser = self._parse(
            connection,
            b"GET / HTTP/1.1\r\nHost: netius.hive.pt\r\n"
            b"X-Custom: first\r\nX-Custom: second\r\n\r\n",
        )

        headers = server._headers(parser)

        # a header that is repeated must be converted into multiple tuples
        # so that none of the values is lost
        self.assertIn((b"host", b"netius.hive.pt"), headers)
        self.assertIn((b"x-custom", b"first"), headers)
        self.assertIn((b"x-custom", b"second"), headers)

    def test__headers_map(self):
        server = self._make_server()

        headers = server._headers_map(
            [
                (b"content-type", b"text/plain"),
                (b"set-cookie", b"first=1"),
                (b"set-cookie", b"second=2"),
            ]
        )

        # the name of the headers is normalized and a repeated one is
        # converted into the sequence of its values
        self.assertEqual(headers["Content-Type"], "text/plain")
        self.assertEqual(headers["Set-Cookie"], ["first=1", "second=2"])

        headers = server._headers_map(
            [
                (b"set-cookie", b"first=1"),
                (b"set-cookie", b"second=2"),
                (b"set-cookie", b"third=3"),
            ]
        )

        self.assertEqual(headers["Set-Cookie"], ["first=1", "second=2", "third=3"])

    def test__subprotocols(self):
        server = self._make_server()
        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST_WS)

        self.assertEqual(server._subprotocols(parser), ["chat", "superchat"])

        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST)

        self.assertEqual(server._subprotocols(parser), [])

        connection = self._make_connection(server)
        parser = self._parse(
            connection,
            b"GET /ws HTTP/1.1\r\nHost: netius.hive.pt\r\n"
            b"Sec-WebSocket-Protocol: chat\r\n"
            b"Sec-WebSocket-Protocol: superchat\r\n\r\n",
        )

        # the sub protocols may be announced under multiple headers, all
        # of them must be reported to the application
        self.assertEqual(server._subprotocols(parser), ["chat", "superchat"])

    def test__version(self):
        server = self._make_server()
        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST)

        self.assertEqual(server._version(parser), "1.1")

        parser.version_s = None

        self.assertEqual(server._version(parser), "1.1")

    def test__close_code(self):
        server = self._make_server()

        self.assertEqual(server._close_code(struct.pack("!H", 1001)), 1001)
        self.assertEqual(server._close_code(b""), netius.servers.asgi.CLOSE_NONE)

    def test__get_buffer(self):
        server = self._make_server()
        connection = self._make_connection(server)
        connection.ws_buffer = []

        self.assertEqual(server._get_buffer(connection), b"")

        connection.ws_buffer = [b"first", b"second"]

        self.assertEqual(server._get_buffer(connection), b"firstsecond")
        self.assertEqual(connection.ws_buffer, [])

        connection.ws_buffer = [b"kept"]

        self.assertEqual(server._get_buffer(connection, delete=False), b"kept")
        self.assertEqual(connection.ws_buffer, [b"kept"])

    def test__is_upgrade(self):
        server = self._make_server()
        connection = self._make_connection(server)

        self.assertEqual(
            server._is_upgrade(connection, self._parse(connection, REQUEST_WS)), True
        )

        connection = self._make_connection(server)

        self.assertEqual(
            server._is_upgrade(connection, self._parse(connection, REQUEST)), False
        )

        connection = self._make_connection(server)
        parser = self._parse(
            connection, b"GET / HTTP/1.1\r\nHost: n.pt\r\nUpgrade: h2c\r\n\r\n"
        )

        # an upgrade to a protocol other than the websocket one is not
        # something that the server is able to handle
        self.assertEqual(server._is_upgrade(connection, parser), False)

        connection = self._make_connection(server)
        parser = self._parse(
            connection, b"GET / HTTP/1.1\r\nHost: n.pt\r\nUpgrade: websocket\r\n\r\n"
        )

        # the upgrade must also be announced under the connection header
        # otherwise the request is not a valid handshake one
        self.assertEqual(server._is_upgrade(connection, parser), False)

        connection = self._make_connection(server)
        parser = self._parse(connection, REQUEST_WS)
        stream = netius.common.HTTP2Stream.__new__(netius.common.HTTP2Stream)

        # the upgrade mechanism is not part of the HTTP/2 specification so
        # a stream of such connection may never be upgraded
        self.assertEqual(server._is_upgrade(stream, parser), False)

    def test__is_upgraded(self):
        server = self._make_server()
        connection = self._make_connection(server)

        self.assertEqual(server._is_upgraded(connection), False)

        connection.ws_handshake = True

        self.assertEqual(server._is_upgraded(connection), True)

    def test__is_ws(self):
        server = self._make_server()
        connection = self._make_connection(server)

        connection.scope = None
        self.assertEqual(server._is_ws(connection), False)

        connection.scope = dict(type="http")
        self.assertEqual(server._is_ws(connection), False)

        connection.scope = dict(type="websocket")
        self.assertEqual(server._is_ws(connection), True)

    def test__is_legacy(self):
        cls = netius.servers.ASGIServer

        # a class based application is the typical shape of the legacy
        # (double callable) interface of the specification
        self.assertEqual(cls._is_legacy(LegacyApp), True)
        self.assertEqual(cls._is_legacy(self._app_legacy), True)
        self.assertEqual(cls._is_legacy(netius.servers.asgi.hello_app), False)
        self.assertEqual(cls._is_legacy(ModernApp()), False)

    def test__decode(self):
        server = self._make_server()

        self.assertEqual(server._decode("/hello%20world"), "/hello world")

    def test_hello_app(self):
        server = self._make_server(app=netius.servers.asgi.hello_app)
        connection = self._make_connection(server)

        connection.parse(REQUEST)
        self._run(server)

        # the complete request cycle must be handled by the application
        # with the response reaching the client (end to end)
        data = self._data(connection)
        self.assertIn(b"HTTP/1.1 200 OK\r\n", data)
        self.assertIn(b"Content-Length: 11\r\n", data)
        self.assertIn(b"Hello World", data)
        self.assertEqual(connection.finished, True)

    def test_hello_app_asyncio(self):
        server = self._make_server(app=netius.servers.asgi.hello_app, asyncio=True)
        connection = self._make_connection(server)

        connection.parse(REQUEST)
        self._run(server)

        # the same request cycle must be handled in the same way while
        # running the application under the asyncio mode of execution
        data = self._data(connection)
        self.assertIn(b"HTTP/1.1 200 OK\r\n", data)
        self.assertIn(b"Hello World", data)
        self.assertEqual(connection.finished, True)

    def test_hello_app_scope(self):
        # an application is only expected to handle the kinds of scope
        # that it supports, returning immediately for the other ones
        coroutine = netius.servers.asgi.hello_app(dict(type="lifespan"), None, None)

        self.assertEqual(self._resolve(coroutine), None)

    def _make_server(self, app=None, **kwargs):
        app = self._app_noop if app == None else app
        server = netius.servers.ASGIServer(app=app, **kwargs)
        self.servers.append(server)
        return server

    def _make_connection(
        self, server, encoding=netius.common.PLAIN_ENCODING, ssl=False, deliver=True
    ):
        # builds a connection without the underlying socket, creating by
        # hand the parser that the opening of it would otherwise create
        connection = netius.servers.http.HTTPConnection(
            owner=server,
            socket=None,
            address=("127.0.0.1", 5000),
            ssl=ssl,
            encoding=encoding,
        )
        connection.max_pending = server.max_pending
        connection.parser = netius.common.HTTPParser(
            connection, type=netius.common.REQUEST, store=True
        )
        connection.parser.bind("on_data", connection.on_data)

        # replaces both the sending and the closing operations by ones
        # that record their usage, as there's no socket to be used
        connection.data = []
        connection.callbacks = []
        connection.closed = False
        connection.send = lambda data, **kwargs: self._send(
            connection, data, deliver, **kwargs
        )
        connection.close = lambda **kwargs: self._close_c(connection)

        self.connections.append(connection)
        return connection

    def _make_future(self, server, done=True, cancel=False, exception=None):
        future = server.build_future()
        if cancel:
            future.cancel()
        elif exception:
            future.set_exception(exception)
        elif done:
            future.set_result(None)
        return future

    def _send(self, connection, data, deliver, delay=True, callback=None, **kwargs):
        # accumulates the data that would otherwise be sent through the
        # socket, running the callback as if it had been delivered, unless
        # the connection is meant to hold the delivery of it
        connection.data.append(netius.legacy.bytes(data))
        if callback:
            if deliver:
                callback(connection)
            else:
                connection.callbacks.append(callback)
        return len(data) if data else 0

    def _deliver(self, connection):
        # runs the callbacks that were being held by the connection, as if
        # the data associated with them had just reached the client
        callbacks = list(connection.callbacks)
        del connection.callbacks[:]
        for callback in callbacks:
            callback(connection)

    def _close_c(self, connection):
        connection.closed = True

    def _parse(self, connection, data):
        connection.parser.parse(data)
        return connection.parser

    def _data(self, connection):
        return b"".join(connection.data)

    def _run(self, server, count=16):
        # runs a bounded number of iterations of the event loop of the
        # server, so that the applications are able to make progress
        for _index in range(count):
            server.ticks()

    def _resolve(self, coroutine):
        # drives the provided coroutine object until its completion,
        # returning the value produced by it, note that this is only
        # valid for a coroutine that never suspends its execution
        try:
            coroutine.send(None)
        except StopIteration as exception:
            return exception.args[0] if exception.args else None
        raise AssertionError("Coroutine did not complete")

    def _await(self, coroutine, result):
        # generator based equivalent of the await keyword, driving the
        # provided coroutine object and yielding the future that it
        # blocks upon so that the event loop is able to resume it, the
        # value produced by it is stored in the provided list
        while True:
            try:
                value = coroutine.send(None)
            except StopIteration as exception:
                result.append(exception.args[0] if exception.args else None)
                break
            yield value

    def _suspend(self, coroutine):
        # runs the provided coroutine object until it suspends its
        # execution, returning the future that it's blocked upon
        return coroutine.send(None)

    @netius.coroutine
    def _app_noop(self, scope, receive, send):
        yield

    @netius.coroutine
    def _app_receive(self, scope, receive, send):
        self._resolve(receive())
        yield

    @netius.coroutine
    def _app_lifespan(self, scope, receive, send):
        while True:
            result = []
            for value in self._await(receive(), result):
                yield value
            message = result[0]
            if message["type"] == "lifespan.startup":
                self._resolve(send(dict(type="lifespan.startup.complete")))
            elif message["type"] == "lifespan.shutdown":
                self._resolve(send(dict(type="lifespan.shutdown.complete")))
                break

    @netius.coroutine
    def _app_lifespan_failed(self, scope, receive, send):
        self._resolve(receive())
        self._resolve(send(dict(type="lifespan.startup.failed", message="boom")))
        yield

    @netius.coroutine
    def _app_lifespan_unsupported(self, scope, receive, send):
        raise netius.NetiusError("Lifespan not supported")
        yield

    def _app_legacy(self, scope):
        # returns the "real" application, the one that is going to be
        # called with the awaitables (double callable interface)
        def app(receive, send):
            return self._app_noop(scope, receive, send)

        return app


class ASGIStubTest(unittest.TestCase):

    def test_unsupported(self):
        if not netius.is_neo():
            self.skipTest("Skipping test: async/await unavailable")

        module = netius.servers.asgi
        is_neo = netius.is_neo

        # replaces the verification of the support for the async/await
        # syntax so that the stub versions of the symbols are the ones
        # that get created by the reloading of the module
        netius.is_neo = lambda: False

        try:
            importlib.reload(module)
            self.assertRaises(netius.NetiusError, module.ASGIServer)
            self.assertRaises(netius.NetiusError, module.hello_app)
            self.assertRaises(netius.NetiusError, module.load_app, "module:app")
        finally:
            netius.is_neo = is_neo
            importlib.reload(module)


class LoadAppTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if not netius.is_neo():
            self.skipTest("Skipping test: async/await unavailable")

    def test_load_app(self):
        app = netius.servers.asgi.load_app("netius.servers.asgi:hello_app")

        self.assertEqual(app, netius.servers.asgi.hello_app)

    def test_load_app_invalid(self):
        # a reference that does not follow the module and attribute
        # notation may not be resolved into an application
        self.assertRaises(
            netius.NetiusError, netius.servers.asgi.load_app, "netius.servers.asgi"
        )

        self.assertRaises(
            netius.NetiusError,
            netius.servers.asgi.load_app,
            "netius.servers.asgi:invalid",
        )


class LegacyApp(object):
    """
    Application that complies with the legacy (double callable)
    interface of the specification, used to verify the detection
    of the interface version of an application.
    """

    def __init__(self, scope):
        self.scope = scope


class ModernApp(object):
    """
    Application that complies with the current (single callable)
    interface of the specification, used to verify the detection
    of the interface version of an application.
    """

    @netius.coroutine
    def __call__(self, scope, receive, send):
        yield
