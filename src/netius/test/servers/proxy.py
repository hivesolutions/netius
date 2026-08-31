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

import collections
import unittest

import netius.common
import netius.servers

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ProxyConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.ProxyServer(encoding="auto")

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_resolve_encoding(self):
        parser = self._make_parser("gzip;q=0.5, deflate")

        connection = self._make_connection(netius.common.AUTO_ENCODING)
        connection.resolve_encoding(parser)

        # under the automatic mode the codings accepted by the client must be
        # recorded, ordered by descending quality value
        self.assertEqual(connection.current, netius.common.PLAIN_ENCODING)
        self.assertEqual(connection.encodings_a, ["deflate", "gzip"])

        # once the encoding of the response has been resolved a late call must
        # not revoke it, as the response may already be under transmission
        connection.dynamic = False
        connection.set_gzip()
        connection.encodings_a = None
        connection.resolve_encoding(parser)
        self.assertEqual(connection.current, netius.common.GZIP_ENCODING)
        self.assertEqual(connection.encodings_a, None)

        connection = self._make_connection(netius.common.GZIP_ENCODING)
        connection.resolve_encoding(parser)

        # for the remaining modes nothing is negotiated with the client, the
        # encoding is the server wide one (legacy behaviour)
        self.assertEqual(connection.current, netius.common.GZIP_ENCODING)
        self.assertEqual(connection.encodings_a, None)

    def test_set_h2(self):
        connection = self._make_relay()
        connection.set_h2()

        # the switch to the binary protocol rebuilds the parser, so the events
        # that drive the proxy must be bound again or they would be lost
        for name in ("on_headers", "on_partial", "on_available", "on_unavailable"):
            self.assertEqual(name in connection.parser.events, True)

    def test_on_headers(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_relay(legacy=True)

        with mock.patch.object(self.server, "on_headers") as on_headers:
            connection.on_headers()

        # under the legacy protocol the connection and the parser of it are
        # what reaches the server, there being no stream to stand for them
        self.assertEqual(on_headers.call_args[0][0], connection)
        self.assertEqual(on_headers.call_args[0][1], connection.parser)

    def test_on_partial(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_relay(legacy=True)

        with mock.patch.object(self.server, "on_partial") as on_partial:
            connection.on_partial(b"hello")

        # the payload travels together with the contexts, as it is the server
        # that decides what is to be done with it
        self.assertEqual(on_partial.call_args[0][0], connection)
        self.assertEqual(on_partial.call_args[0][2], b"hello")

    def test_on_available(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_relay()
        stream = self._make_stream(connection)

        with mock.patch.object(self.server, "on_available") as on_available:
            connection.on_available()

        # with a stream under way it is the stream that stands for both of the
        # contexts, so that the throttling is applied to it and not to the
        # connection that multiplexes it
        self.assertEqual(on_available.call_args[0][0], stream)
        self.assertEqual(on_available.call_args[0][1], stream)

    def test_on_unavailable(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_relay()
        stream = self._make_stream(connection)

        with mock.patch.object(self.server, "on_unavailable") as on_unavailable:
            connection.on_unavailable()

        self.assertEqual(on_unavailable.call_args[0][0], stream)

        # once the stream is gone the connection takes its place again, which
        # is what keeps the events of a spent parser from being dropped
        connection.parser._del_stream(stream.identifier)

        with mock.patch.object(self.server, "on_unavailable") as on_unavailable:
            connection.on_unavailable()

        self.assertEqual(on_unavailable.call_args[0][0], connection)
        self.assertEqual(on_unavailable.call_args[0][1], connection.parser)

    def _make_connection(self, encoding):
        # builds a proxy connection without the underlying socket, replicating
        # the encoding state that the constructor would otherwise initialize
        connection = netius.servers.proxy.ProxyConnection.__new__(
            netius.servers.proxy.ProxyConnection
        )
        connection.owner = self.server
        connection.encoding = encoding
        connection.current = connection.base_encoding()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        return connection

    def _make_relay(self, legacy=False):
        # builds a proxy connection without the underlying socket, in the state
        # that the relaying of the events of the parser reads
        connection = netius.servers.proxy.ProxyConnection.__new__(
            netius.servers.proxy.ProxyConnection
        )
        connection.owner = self.server
        connection.legacy = legacy
        connection.parser = None
        connection.encoding = netius.common.PLAIN_ENCODING
        connection.window_o = netius.common.HTTP2_WINDOW
        if legacy:
            connection.parser = netius.common.HTTPParser(
                connection, type=netius.common.REQUEST
            )
        else:
            connection.set_h2()
        return connection

    def _make_stream(self, connection):
        # builds an open stream and registers it in the parser, so that it
        # becomes the context under which the events are relayed
        stream = netius.common.http2.HTTP2Stream(identifier=1, owner=connection.parser)
        stream.open()
        connection.parser._set_stream(stream)
        return stream

    def _make_parser(self, accept_encoding):
        parser = netius.common.HTTPParser(self, type=netius.common.REQUEST)
        parser.version = netius.common.HTTP_11
        parser.headers = {"accept-encoding": accept_encoding}
        return parser


class ProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.ProxyServer()
        self.server_a = netius.servers.ProxyServer(encoding="auto")

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()
        self.server_a.cleanup()

    def test_stop(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.server.container, "stop") as stop:
            self.server.stop()

        # the loop is the one of the container, so the stopping of the proxy
        # is the stopping of the container that holds the three of the bases
        self.assertEqual(stop.called, True)

        # a proxy that has been cleaned up has no container left to be stopped,
        # and asking for it again must not raise
        self.server_a.cleanup()
        self.assertEqual(self.server_a.stop(), None)

    def test_connections_dict(self):
        # a container that is not running the proxy would delegate the
        # operation back into it, so the local connections are the ones
        # reported instead (avoids an infinite recursion)
        self.assertEqual(self.server.connections_dict(), [])
        self.assertEqual(self.server.connections_dict(parent=True), [])

        self.server.container.owner = self.server

        # under a running container the connections of every base are reported,
        # the proxy itself and the two clients that back it
        result = self.server.connections_dict()
        self.assertEqual(
            sorted(result.keys()), ["HTTPClient", "ProxyServer", "RawClient"]
        )
        self.assertEqual(result["ProxyServer"], [])

    def test_connection_dict(self):
        # the lookup spans every base of the container, an identifier that
        # names none of their connections giving nothing back
        self.assertEqual(self.server.connection_dict(999), None)

    def test_is_upgrade(self):
        Parser = collections.namedtuple("Parser", "headers")

        parser = Parser(headers={"connection": "Upgrade", "upgrade": "websocket"})
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(
            headers={"connection": "keep-alive, Upgrade", "upgrade": "WebSocket"}
        )
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(headers={"connection": "keep-alive"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(headers={"connection": "Upgrade", "upgrade": "h2c"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(headers={"connection": "notupgrade", "upgrade": "websocket"})
        self.assertEqual(self.server.is_upgrade(parser), False)

        parser = Parser(
            headers={
                "connection": ["keep-alive", "Upgrade"],
                "upgrade": ["websocket"],
            }
        )
        self.assertEqual(self.server.is_upgrade(parser), True)

        parser = Parser(headers={})
        self.assertEqual(self.server.is_upgrade(parser), False)

    def test_tunnel(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()

        with mock.patch.object(
            self.server.raw_client, "connect", return_value=backend
        ) as connect:
            result = self.server.tunnel(
                connection, "host.com", 9090, ssl=True, data=b"data"
            )

        # the back-end connection must be created through the raw client
        # using the requested host, port and secure transport flag
        self.assertEqual(result, backend)
        self.assertEqual(connect.call_args[0], ("host.com", 9090))
        self.assertEqual(connect.call_args[1], dict(ssl=True))

        # the back-end connection must be set as the tunnel connection of
        # the front-end and the reverse mapping must exist in the conn map
        self.assertEqual(connection.tunnel_c, backend)
        self.assertIn(backend, self.server.conn_map)
        self.assertEqual(self.server.conn_map[backend], connection)

        # the data and response values must be stored in the back-end so
        # that they may be used once the connection is established
        self.assertEqual(backend.tunnel_d, b"data")
        self.assertEqual(backend.tunnel_r, None)

    def test_reason_connection(self):
        class Connection(object):
            pass

        # a plain connection is the one to be marked, as there's no
        # protocol wrapping it under the old architecture
        connection = Connection()
        self.server.reason_connection(connection, netius.REASON_EXPLICIT)
        self.assertEqual(connection.close_reason, netius.REASON_EXPLICIT)

        # under the new architecture the value is a protocol, so it's the
        # underlying connection that must be marked, as that's the object
        # known by the diagnostics
        protocol = Connection()
        protocol.connection = Connection()
        self.server.reason_connection(protocol, netius.REASON_UPSTREAM_ERROR)
        self.assertEqual(protocol.connection.close_reason, netius.REASON_UPSTREAM_ERROR)
        self.assertEqual(hasattr(protocol, "close_reason"), False)

        # a protocol with no underlying connection must be gracefully
        # handled, as the connection may not have been established yet
        protocol = Connection()
        protocol.connection = None
        self.server.reason_connection(protocol, netius.REASON_ERROR)
        self.assertEqual(hasattr(protocol, "close_reason"), False)

    def test_pair_connection(self):
        class Connection(object):

            def __init__(self, id):
                self.id = id

        # a back-end connection that is not mapped must be ignored, as
        # there's no front-end counterpart to be associated with it
        backend = Connection("backend")
        self.server.pair_connection(backend)
        self.assertEqual(hasattr(backend, "close_paired"), False)

        # both sides of a mapped exchange must end up knowing about the
        # identifier of the other one, so that they may be correlated
        frontend = Connection("frontend")
        self.server.conn_map[backend] = frontend
        self.server.pair_connection(backend)
        self.assertEqual(backend.close_paired, "frontend")
        self.assertEqual(frontend.close_paired, "backend")

        # a protocol is resolved into its connection, so that it's the
        # identifier of such connection that is used for the pairing
        protocol = Connection("protocol")
        protocol.connection = Connection("underlying")
        self.server.conn_map[protocol] = frontend
        self.server.pair_connection(protocol)
        self.assertEqual(protocol.connection.close_paired, "frontend")
        self.assertEqual(frontend.close_paired, "underlying")

    def test__prx_encoding(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()
        parser = self._make_response_parser()
        headers = {"content-type": "text/html"}

        codec = self.server_a._prx_encoding(connection, parser, headers, None)

        # an identity payload of a compressible media type and of a size
        # within the bounds must be compressed with the resolved coding
        self.assertEqual(codec["name"], "gzip")
        self.assertEqual(codec["encoding"], netius.common.GZIP_ENCODING)
        self.assertEqual(connection.encodings_a, ["gzip", "deflate"])
        self.assertEqual(connection.dynamic, True)

        # the explicit identity coding must be removed from the headers so
        # that the resolved coding may be announced in its place
        headers = {"content-type": "text/html", "content-encoding": "identity"}
        codec = self.server_a._prx_encoding(connection, parser, headers, "identity")
        self.assertEqual(codec["name"], "gzip")
        self.assertEqual("content-encoding" in headers, False)

    def test__prx_encoding_encoded(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()
        parser = self._make_response_parser()

        for content_encoding in ("gzip", "br"):
            headers = {
                "content-type": "text/html",
                "content-encoding": content_encoding,
            }
            codec = self.server_a._prx_encoding(
                connection, parser, headers, content_encoding
            )

            # a payload that does not arrive under the identity coding must
            # be forwarded byte-identical, keeping the coding of the back-end
            self.assertEqual(codec, None)
            self.assertEqual(headers["content-encoding"], content_encoding)
            self.assertEqual(connection.dynamic, True)

            # the representation does not depend on the codings accepted by
            # the client, so no vary header must be announced for it
            self.assertEqual(connection.encodings_a, None)

    def test__prx_encoding_accept(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        parser = self._make_response_parser()

        for accept_encoding in ("", "identity", "gzip;q=0, deflate;q=0"):
            connection = self._make_frontend(accept_encoding=accept_encoding)
            headers = {"content-type": "text/html"}
            codec = self.server_a._prx_encoding(connection, parser, headers, None)

            # a client that does not accept any of the supported codings must
            # never receive a compressed payload
            self.assertEqual(codec, None)
            self.assertEqual("gzip" in connection.encodings_a, False)

            # the response was still eligible, so the representation depends
            # on the codings accepted and the vary header must be announced
            self.assertNotEqual(connection.encodings_a, None)

    def test__prx_encoding_status(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()

        # the informational, empty and partial status codes must never be
        # compressed as their payload either does not exist or is partial
        for code_s in ("101", "204", "206", "304"):
            parser = self._make_response_parser(code_s=code_s)
            headers = {"content-type": "text/html"}
            codec = self.server_a._prx_encoding(connection, parser, headers, None)
            self.assertEqual(codec, None)
            self.assertEqual(connection.encodings_a, None)

        # a response to a HEAD request carries no payload, so there's nothing
        # to be compressed in it (the length must be preserved)
        connection = self._make_frontend(method="HEAD")
        parser = self._make_response_parser()
        headers = {"content-type": "text/html"}
        codec = self.server_a._prx_encoding(connection, parser, headers, None)
        self.assertEqual(codec, None)

        # an older front-end has no chunked framing available and so it can
        # never receive a compressed payload
        connection = self._make_frontend(version=netius.common.HTTP_10)
        codec = self.server_a._prx_encoding(connection, parser, headers, None)
        self.assertEqual(codec, None)

    def test__prx_encoding_preserve(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()
        parser = self._make_response_parser()

        # the no-transform cache directive forbids the changing of the coding
        # of the payload, the same applies to the partial payloads
        headers = {"content-type": "text/html", "cache-control": "no-transform"}
        self.assertEqual(
            self.server_a._prx_encoding(connection, parser, headers, None), None
        )

        headers = {"content-type": "text/html", "content-range": "bytes 0-10/20"}
        self.assertEqual(
            self.server_a._prx_encoding(connection, parser, headers, None), None
        )

        # a repeated cache control header is equivalent to a single one with
        # the directives joined, so the directive must be found in any of them
        headers = {
            "content-type": "text/html",
            "cache-control": ["no-transform", "max-age=60"],
        }
        self.assertEqual(
            self.server_a._prx_encoding(connection, parser, headers, None), None
        )

        headers = {
            "content-type": "text/html",
            "cache-control": ["max-age=60", "no-transform"],
        }
        self.assertEqual(
            self.server_a._prx_encoding(connection, parser, headers, None), None
        )

    def test__prx_encoding_types(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()
        parser = self._make_response_parser()

        # a media type for which the compression provides no relevant gain
        # must not even be considered eligible (no vary announcement)
        for content_type in ("image/jpeg", "text/event-stream"):
            headers = {"content-type": content_type}
            codec = self.server_a._prx_encoding(connection, parser, headers, None)
            self.assertEqual(codec, None)
            self.assertEqual(connection.encodings_a, None)

    def test__prx_encoding_size(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_frontend()

        # a payload that is too small to pay for the framing overhead or too
        # large to be compressed synchronously must be forwarded as is
        for content_l in (0, self.server_a.compress_min - 1):
            parser = self._make_response_parser(content_l=content_l)
            headers = {"content-type": "text/html"}
            codec = self.server_a._prx_encoding(connection, parser, headers, None)
            self.assertEqual(codec, None)
            self.assertEqual(connection.encodings_a, None)

        parser = self._make_response_parser(content_l=self.server_a.compress_max + 1)
        headers = {"content-type": "text/html"}
        codec = self.server_a._prx_encoding(connection, parser, headers, None)
        self.assertEqual(codec, None)
        self.assertEqual(connection.encodings_a, None)

        # a payload of undeclared length is still eligible, the decision on
        # it being deferred until enough of it has been received
        parser = self._make_response_parser(content_l=-1)
        headers = {"content-type": "text/html"}
        codec = self.server_a._prx_encoding(connection, parser, headers, None)
        self.assertEqual(codec["name"], "gzip")

    def test__prx_header(self):
        # the last definition of a repeated header is the one that prevails
        # whenever a single value is requested for it
        headers = {"content-type": ["text/html", "text/plain"]}
        self.assertEqual(
            self.server_a._prx_header(headers, "content-type"), "text/plain"
        )

        # the list based fields must instead be joined, as a repeated header
        # is equivalent to a single one with the values comma separated
        headers = {"cache-control": ["no-transform", "max-age=60"]}
        self.assertEqual(
            self.server_a._prx_header(headers, "cache-control", join=True),
            "no-transform,max-age=60",
        )

        # a header defined only once must be returned as is and an undefined
        # one must resolve to an invalid value
        headers = {"cache-control": "no-transform"}
        self.assertEqual(
            self.server_a._prx_header(headers, "cache-control", join=True),
            "no-transform",
        )
        self.assertEqual(self.server_a._prx_header(headers, "content-type"), None)

    def test__prx_authority(self):
        # a target in the authority form must be resolved into its host and
        # port components, only the allowed ports being accepted for a tunnel
        self.assertEqual(self.server._prx_authority("host.com:443"), ("host.com", 443))

        # a target towards a port that is not an allowed one must be refused
        # so that the proxy may not be used as a generic relay
        self.assertEqual(self.server._prx_authority("host.com:22"), (None, None))
        self.assertEqual(self.server._prx_authority("host.com:80"), (None, None))

        # a malformed target must also be refused, either because no port is
        # provided or because the provided one is not a valid number
        self.assertEqual(self.server._prx_authority("host.com"), (None, None))
        self.assertEqual(self.server._prx_authority("host.com:"), (None, None))
        self.assertEqual(self.server._prx_authority(":443"), (None, None))
        self.assertEqual(self.server._prx_authority("host.com:https"), (None, None))
        self.assertEqual(self.server._prx_authority("host.com:99999"), (None, None))

        # only the ASCII digits are valid, a unicode digit must not be taken
        # as a valid port as it may not be converted into an integer
        self.assertEqual(self.server._prx_authority("host.com:\xb2"), (None, None))

        # an IPv6 literal must be properly handled, as the target is split
        # around the final colon and not around the first one, note that the
        # delimiters are removed as the resolver does not expect them
        self.assertEqual(self.server._prx_authority("[::1]:443"), ("::1", 443))
        self.assertEqual(self.server._prx_authority("[]:443"), (None, None))

        # with no restriction in place every valid port must be accepted, as
        # the allowed ports sequence is an empty one
        self.server.connect_ports = ()
        self.assertEqual(self.server._prx_authority("host.com:22"), ("host.com", 22))

    def test__prx_codec(self):
        # the coding must be resolved using the server preference order out
        # of the ones that are also accepted by the client
        self.assertEqual(self.server_a._prx_codec(["gzip", "deflate"])["name"], "gzip")
        self.assertEqual(self.server_a._prx_codec(["deflate", "gzip"])["name"], "gzip")
        self.assertEqual(self.server_a._prx_codec(["deflate"])["name"], "deflate")

        # a client that accepts no supported coding must not have any coding
        # resolved for it (no compression is performed)
        self.assertEqual(self.server_a._prx_codec([]), None)
        self.assertEqual(self.server_a._prx_codec(["br", "zstd"]), None)

        # a coding that is not enabled in the server must never be used even
        # in case it's both registered and accepted by the client
        self.server_a.compress_encodings = ["deflate"]
        self.assertEqual(
            self.server_a._prx_codec(["gzip", "deflate"])["name"], "deflate"
        )

    def test__prx_release(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        buffer = dict(
            headers={"Content-Type": "text/html"},
            version="HTTP/1.1",
            code=200,
            code_s="OK",
            codec=netius.servers.http.CODECS["gzip"],
            data=[b"chunk"],
            length=5,
        )
        connection = self._make_frontend()
        connection.encoding_b = buffer

        self.server_a._prx_release(connection, length=5)

        # the response that was being held must be sent to the front-end
        # and the structure unset from the connection
        self.assertEqual(connection.send_header.call_count, 1)
        self.assertEqual(connection.send_part.call_count, 1)
        self.assertEqual(connection.encoding_b, None)

        # the payload must not be retained, as the flush deadline still
        # holds a reference to the structure until it's run
        self.assertEqual(buffer["data"], [])
        self.assertEqual(buffer["headers"], None)

        # a release of an already released response must be a no operation,
        # so that a pending deadline never sends the response a second time
        self.server_a._prx_release(connection)
        self.assertEqual(connection.send_header.call_count, 1)

    def test__apply_accept(self):
        # under the automatic mode the back-end is asked for the identity
        # coding, so that the proxy becomes the compression authority
        headers = {"accept-encoding": "gzip, deflate"}
        self.server_a._apply_accept(headers)
        self.assertEqual(headers["accept-encoding"], "identity")

        # the codings accepted by the client may be forwarded instead, so
        # that a back-end that does better than the proxy wins
        self.server_a.compress_forward_accept = True
        headers = {"accept-encoding": "gzip, deflate"}
        self.server_a._apply_accept(headers)
        self.assertEqual(headers["accept-encoding"], "gzip, deflate")

        # for the remaining modes the header is never changed by the proxy
        headers = {"accept-encoding": "gzip, deflate"}
        self.server._apply_accept(headers)
        self.assertEqual(headers["accept-encoding"], "gzip, deflate")

    def test_on_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.tunnel_c = None
        self.server.on_data(connection, b"hello")

        # with no tunnel in place the data belongs to the proxy itself (the
        # handshake or a plain client proxy), so it is handed to the parser
        self.assertEqual(connection.parse.call_args[0][0], b"hello")

        connection = self._make_tunnelled()
        connection.tunnel_c.is_exhausted.return_value = False
        self.server.on_data(connection, b"hello")

        # once the tunnel is up the data is relayed to the other end of it,
        # under a callback that resumes this one as the buffer drains
        self.assertEqual(connection.tunnel_c.send.call_args[0][0], b"hello")
        self.assertEqual(
            connection.tunnel_c.send.call_args[1]["callback"], self.server._throttle
        )
        self.assertEqual(connection.parse.called, False)
        self.assertEqual(connection.disable_read.called, False)

        connection = self._make_tunnelled()
        connection.tunnel_c.is_exhausted.return_value = True
        self.server.on_data(connection, b"hello")

        # with the buffer of the other end full the reading of this one is
        # turned off, which is what keeps the two in step
        self.assertEqual(connection.disable_read.called, True)

    def test_on_connection_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        tunnel_c = connection.tunnel_c
        proxy_c = connection.proxy_c

        self.server.on_connection_d(connection)

        # both of the ends that the connection was paired with are closed and
        # marked as such, so that the diagnostics may tell them apart from the
        # ones that were closed by their own peer
        self.assertEqual(tunnel_c.connection.close_reason, netius.REASON_EXPLICIT)
        self.assertEqual(tunnel_c.close.called, True)
        self.assertEqual(proxy_c.connection.close_reason, netius.REASON_EXPLICIT)
        self.assertEqual(proxy_c.close.called, True)

        # the references are released, as holding them would keep both of the
        # ends (and their buffers) alive for as long as the connection is
        self.assertEqual(connection.tunnel_c, None)
        self.assertEqual(connection.proxy_c, None)
        self.assertEqual(connection.encoding_b, None)

    def test_on_stream_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        stream = mock.MagicMock()
        proxy_c = stream.proxy_c

        self.server.on_stream_d(stream)

        # under the binary protocol it's the stream that owns the exchange, so
        # the release must happen for it and not for the connection that
        # multiplexes it (which outlives the stream)
        self.assertEqual(proxy_c.connection.close_reason, netius.REASON_EXPLICIT)
        self.assertEqual(proxy_c.close.called, True)
        self.assertEqual(stream.tunnel_c, None)
        self.assertEqual(stream.proxy_c, None)
        self.assertEqual(stream.encoding_b, None)

    def test_on_headers(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        self.server.on_headers(connection, None)

        # outside of the automatic mode nothing is negotiated with the client,
        # so the (per request) resolution cost is not paid at all
        self.assertEqual(connection.resolve_encoding.called, False)

        self.server_a.on_headers(connection, None)

        # under the automatic mode the encoding is resolved as soon as the
        # request headers are known, ahead of any rewriting of them
        self.assertEqual(connection.resolve_encoding.called, True)

    def test_on_partial(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled()
        connection.proxy_c = None

        # a connection with no back-end (a raw tunnel or a proxy that is not
        # yet established) has nowhere to forward the payload to
        self.assertEqual(self.server.on_partial(connection, None, b"hello"), None)

        connection = self._make_throttled()
        self.server.on_partial(connection, None, b"hello")

        # the payload is forced into the back-end, the reading of the front-end
        # being left on as the buffer of the back-end has room for it
        self.assertEqual(connection.proxy_c.send_base.call_args[0][0], b"hello")
        self.assertEqual(connection.disable_read.called, False)

        connection = self._make_throttled(exhausted=True)
        self.server.on_partial(connection, None, b"hello")

        # with the buffer of the back-end full the reading of the front-end is
        # turned off, which is what stops the payload from piling up
        self.assertEqual(connection.disable_read.called, True)

    def test_on_available(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled()

        with mock.patch.object(self.server, "reads") as reads:
            self.server.on_available(connection, None)

        # the reading of the back-end is turned back on once the buffer of
        # the front-end has drained, and the poll is told about it
        self.assertEqual(connection.proxy_c.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

    def test_on_available_enabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled(renable=True)

        self.server.on_available(connection, None)

        # a back-end whose reading was never turned off has nothing to be
        # turned back on, so it is left as it is
        self.assertEqual(connection.proxy_c.enable_read.called, False)

    def test_on_available_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled(restored=False)

        self.server.on_available(connection, None)

        # with the buffer of the front-end still holding data the back-end
        # is kept quiet, as reading more would only add to it
        self.assertEqual(connection.proxy_c.enable_read.called, False)

    def test_on_unavailable(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled(renable=True, exhausted=True)

        self.server.on_unavailable(connection, None)

        # the buffer of the front-end is full, so the reading of the
        # back-end is turned off until it drains again
        self.assertEqual(connection.proxy_c.disable_read.called, True)

    def test_on_unavailable_disabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled(exhausted=True)

        self.server.on_unavailable(connection, None)

        # a back-end that is already quiet is left alone, instead of being
        # turned off a second time
        self.assertEqual(connection.proxy_c.disable_read.called, False)

    def test_on_unavailable_room(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_throttled(renable=True)

        self.server.on_unavailable(connection, None)

        # with room left in the buffer of the front-end there is nothing to
        # defend against, so the back-end keeps reading
        self.assertEqual(connection.proxy_c.disable_read.called, False)

    def test__throttle(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a back-end that is already gone asks for nothing of the front-end
        # that it was mapped to
        self.assertEqual(self.server._throttle(None), None)

        backend = mock.MagicMock()
        backend.is_restored.return_value = False

        # a back-end whose buffer still holds data is under back-pressure, so
        # the throttling of the front-end must remain in place
        self.assertEqual(self.server._throttle(backend), None)

        backend = mock.MagicMock()
        backend.is_restored.return_value = True

        # a back-end that is no longer mapped (eg: a connection under a
        # graceful close) has no front-end left to be resumed
        self.assertEqual(self.server._throttle(backend), None)

        frontend = mock.MagicMock()
        frontend.renable = False
        self.server.conn_map[backend._protocol] = frontend

        with mock.patch.object(self.server, "reads") as reads:
            self.server._throttle(backend)

        # the protocol is what stands for the back-end under the new
        # architecture, so it's the key under which the front-end is found
        self.assertEqual(frontend.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

        frontend.enable_read.reset_mock()
        frontend.renable = True
        self.server._throttle(backend)

        # a front-end whose reading was never turned off has nothing to be
        # turned back on, so it is left as it is
        self.assertEqual(frontend.enable_read.called, False)

    def test__prx_throttle(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # neither a connection that is gone nor one that still holds data asks
        # for anything of the back-end that faces it
        self.assertEqual(self.server._prx_throttle(None), None)

        connection = self._make_throttled(restored=False)
        self.server._prx_throttle(connection)

        self.assertEqual(connection.proxy_c.enable_read.called, False)

        connection = self._make_throttled()
        connection.proxy_c = None

        # a connection with no back-end has nothing to be resumed, which is
        # the case of a raw tunnel or of a proxy that is not established
        self.assertEqual(self.server._prx_throttle(connection), None)

        connection = self._make_throttled()

        with mock.patch.object(self.server, "reads") as reads:
            self.server._prx_throttle(connection)

        # the reading of the back-end is turned back on once the buffer of the
        # front-end has drained, and the poll is told about it
        self.assertEqual(connection.proxy_c.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

    def test__raw_throttle(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_tunnelled()

        with mock.patch.object(self.server, "reads") as reads:
            self.server._raw_throttle(connection)

        # the reading of the other side of the tunnel is turned back on
        # once this one has drained, which is what keeps the two in step
        self.assertEqual(connection.tunnel_c.enable_read.called, True)
        self.assertEqual(reads.call_args[1]["state"], False)

    def test__raw_throttle_missing(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # neither a connection that is gone nor one that still holds data
        # asks for anything of the side that faces it
        self.assertEqual(self.server._raw_throttle(None), None)

        connection = self._make_tunnelled(restored=False)
        self.server._raw_throttle(connection)

        self.assertEqual(connection.tunnel_c.enable_read.called, False)

    def test__raw_throttle_untunnelled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_tunnelled()
        connection.tunnel_c = None

        # a connection that faces no tunnel has no other side to be told
        # about it, so nothing is done for it
        self.assertEqual(self.server._raw_throttle(connection), None)

        connection = self._make_tunnelled(renable=True)
        self.server._raw_throttle(connection)

        self.assertEqual(connection.tunnel_c.enable_read.called, False)

    def test_on_raw_connect_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()
        backend.tunnel_d = b"data"
        backend.tunnel_r = None
        self.server.conn_map[backend] = connection

        self.server._on_raw_connect(self.server.raw_client, backend)

        # the buffered data must be forwarded to the back-end and no
        # acknowledge response must be sent to the front-end connection
        self.assertEqual(backend.send.call_args[0], (b"data",))
        self.assertEqual(connection.send_response.call_count, 0)

        # the data reference must be unset after being sent so that the
        # request buffer is not retained for the lifetime of the tunnel
        self.assertEqual(backend.tunnel_d, None)

    def test_on_raw_connect_response(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()
        backend.tunnel_d = None
        backend.tunnel_r = (200, "Connection established")
        self.server.conn_map[backend] = connection

        self.server._on_raw_connect(self.server.raw_client, backend)

        # the acknowledge response must be sent to the front-end connection
        # and no data must be forwarded to the back-end connection
        self.assertEqual(connection.send_response.call_count, 1)
        self.assertEqual(connection.send_response.call_args[1]["code"], 200)
        self.assertEqual(backend.send.call_count, 0)

    def test_on_raw_data(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.is_exhausted.return_value = False
        backend = mock.MagicMock()
        self.server.conn_map[backend] = connection

        self.server._on_raw_data(self.server.raw_client, backend, b"hello")

        # the data of the back-end is relayed to the front-end under a callback
        # that resumes the back-end as the buffer of the front-end drains
        self.assertEqual(connection.send.call_args[0][0], b"hello")
        self.assertEqual(
            connection.send.call_args[1]["callback"], self.server._raw_throttle
        )
        self.assertEqual(backend.disable_read.called, False)

        connection.is_exhausted.return_value = True
        self.server._on_raw_data(self.server.raw_client, backend, b"hello")

        # with the buffer of the front-end full the reading of the back-end is
        # turned off, which is what stops the data from piling up
        self.assertEqual(backend.disable_read.called, True)

    def test_on_raw_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        backend = mock.MagicMock()
        self.server.conn_map[backend] = connection

        self.server._on_raw_close(self.server.raw_client, backend)

        # the front-end is closed with the pending data flushed and under a
        # reason that names the back-end as the origin of the closing
        self.assertEqual(connection.close.call_args[1]["flush"], True)
        self.assertEqual(
            connection.close.call_args[1]["reason"], netius.REASON_UPSTREAM_ERROR
        )

        # the mapping is released, as holding it would keep both of the ends
        # (and their buffers) alive for the lifetime of the proxy
        self.assertEqual(backend in self.server.conn_map, False)

    def _make_frontend(
        self,
        accept_encoding="gzip, deflate",
        method="GET",
        version=netius.common.HTTP_11,
    ):
        # builds a front-end connection stand-in that carries the request
        # values probed by the eligibility gates of the automatic mode
        connection = mock.MagicMock()
        connection.encoding_c = None
        connection.encodings_a = None
        connection.dynamic = None
        connection.encoding_b = None
        connection.encoding_w.return_value = netius.common.PLAIN_ENCODING
        connection.encoding_name.return_value = None
        connection.is_measurable.return_value = True
        connection.parser = mock.MagicMock()
        connection.parser.method = method
        connection.parser.version = version
        connection.parser.get_encodings.return_value = netius.common.parse_encodings(
            accept_encoding
        )
        return connection

    def _make_response_parser(self, code_s="200", content_l=4096):
        # builds a back-end response parser stand-in with only the values
        # that are relevant for the resolution of the encoding
        parser = mock.MagicMock()
        parser.code_s = code_s
        parser.content_l = content_l
        return parser

    def _make_throttled(self, renable=False, restored=True, exhausted=False):
        # builds a front-end connection stand-in together with the back-end
        # one that faces it, in the state that the throttling gates read
        connection = mock.MagicMock()
        connection.is_restored.return_value = restored
        connection.is_exhausted.return_value = exhausted
        connection.proxy_c.renable = renable
        connection.proxy_c.is_exhausted.return_value = exhausted
        return connection

    def _make_tunnelled(self, renable=False, restored=True):
        # builds a connection stand-in together with the other end of the
        # tunnel that it is paired with, under the same terms
        connection = mock.MagicMock()
        connection.is_restored.return_value = restored
        connection.tunnel_c.renable = renable
        return connection
