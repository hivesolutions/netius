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

"""netius.servers.proxy

Base (reverse) proxy server built on top of the Netius HTTP/2 server.
Receives the front-end traffic and forwards each request to an upstream
back-end through an internal HTTP client, while a raw client handles plain
TCP tunnelling for cases such as CONNECT or bridged WebSocket traffic.
Pending data is throttled using configurable buffer thresholds to keep the
producer and consumer sides balanced. Intended to be subclassed rather than
used directly.
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius.common
import netius.clients

from . import http
from . import http2

BUFFER_RATIO = 1.5
""" The ratio for the calculus of the internal socket
buffer size from the maximum pending buffer size """

MIN_RATIO = 0.8
""" The ration for the calculus of the minimum pending
value this is going to be used to re-enable the operation
and start the filling of the buffer again """

MAX_PENDING = netius.CHUNK_SIZE * 8
""" The size in bytes considered to be the maximum
allowed in the sending buffer, this maximum value
avoids the starvation of the producer to consumer
relation that could cause memory problems """

COMPRESS_TIMEOUT = 1.0
""" The maximum amount of time (in seconds) that a response
may be held while waiting for enough payload to decide on the
compression, avoids holding a slow trickling back-end forever """


class ProxyConnection(http2.HTTP2Connection):

    def open(self, *args, **kwargs):
        http2.HTTP2Connection.open(self, *args, **kwargs)
        if not self.is_open():
            return
        self.parser.store = False
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_partial", self.on_partial)
        self.parser.bind("on_available", self.on_available)
        self.parser.bind("on_unavailable", self.on_unavailable)

    def resolve_encoding(self, parser):
        # under the automatic mode the parent resolution is run so that the
        # codings accepted by the client are recorded, for the remaining
        # modes the encoding is the server wide one and nothing is
        # negotiated with the client (legacy behaviour)
        if not self.encoding == netius.common.AUTO_ENCODING:
            return

        # in case the encoding of the response has already been resolved
        # nothing is done, otherwise a late resolution (eg: the request body
        # completing after an early response) would revoke the decision
        if not self.dynamic == None:
            return

        http2.HTTP2Connection.resolve_encoding(self, parser)

    def set_h2(self):
        http2.HTTP2Connection.set_h2(self)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_partial", self.on_partial)
        self.parser.bind("on_available", self.on_available)
        self.parser.bind("on_unavailable", self.on_unavailable)

    def on_headers(self):
        self.owner.on_headers(self.connection_ctx, self.parser_ctx)

    def on_partial(self, data):
        self.owner.on_partial(self.connection_ctx, self.parser_ctx, data)

    def on_available(self):
        self.owner.on_available(self.connection_ctx, self.parser_ctx)

    def on_unavailable(self):
        self.owner.on_unavailable(self.connection_ctx, self.parser_ctx)


class ProxyServer(http2.HTTP2Server):
    """
    High-level HTTP/2 (reverse) proxy built on top of Netius' streaming
    primitives.

    This class is meant to be used as a base class for proxy servers.
    It is not meant to be used directly.

    The class glues together three distinct building blocks that live
    inside a lightweight Container:

    1. A listening `HTTP2Server` (this class) that receives the front-end
       traffic.
    2. An internal `HTTPClient` that forwards the request to the
       upstream/back-end using either HTTP/1.1 or HTTP/2.
    3. A `RawClient` used for plain TCP tunnelling (e.g. `CONNECT` or
       WebSocket bridged traffic).

    Design decisions and rationale:

    * **Event-driven & non-blocking** - inherits from :class:`HTTP2Server`
      so every connection is cooperatively multiplexed by the Netius
      loop.
    * **Dynamic encoding pipeline** - the `dynamic` flag enables
      transparent negotiation between plain, chunked and compressed
      bodies, mirroring the behaviour of :class:`HTTPServer`.
    * **Back-pressure aware** - when `throttle` is *True* the proxy
      pauses reading from the client once the pending bytes in the
      outbound socket exceed `MAX_PENDING` and resumes when the buffer
      drains below `min_pending`. This prevents producer-consumer
      starvation and uncontrolled memory growth.
    * **Origin rewriting** - with `trust_origin` set to *False* the
      proxy rewrites `Host`, `Origin` and `Via` headers in order to
      guarantee a single authoritative origin and mitigate header
      spoofing. Setting it to *True* provides a fully transparent mode
      useful for trusted/internal deployments.
    * **Connection correlation** - `conn_map` keeps a one-to-one mapping
      between downstream connections and their upstream counterpart so
      that errors and partial bodies propagate in both directions.
    * **Single loop deployment** - every component shares the same event
      loop; the surrounding :class:`Container` only orchestrates their
      life-cycle, making the proxy easy to embed alongside other Netius
      servers.

    The public API (`start()`, `stop()`, `cleanup()`) follows the same
    conventions used across Netius, allowing the proxy server to be
    combined with other agents in a larger container or run standalone.
    """

    def __init__(
        self,
        dynamic=True,
        throttle=True,
        trust_origin=False,
        max_pending=MAX_PENDING,
        compress_forward_accept=False,
        compress_buffer=True,
        compress_timeout=COMPRESS_TIMEOUT,
        *args,
        **kwargs
    ):
        http2.HTTP2Server.__init__(
            self,
            receive_buffer_c=int(max_pending * BUFFER_RATIO),
            send_buffer_c=int(max_pending * BUFFER_RATIO),
            *args,
            **kwargs
        )
        self.dynamic = dynamic
        self.throttle = throttle
        self.trust_origin = trust_origin
        self.max_pending = max_pending
        self.min_pending = int(max_pending * MIN_RATIO)
        self.compress_forward_accept = compress_forward_accept
        self.compress_buffer = compress_buffer
        self.compress_timeout = compress_timeout
        self.conn_map = {}

        self.http_client = netius.clients.HTTPClient(
            thread=False,
            auto_release=False,
            receive_buffer=max_pending,
            send_buffer=max_pending,
            *args,
            **kwargs
        )
        self.http_client.bind("headers", self._on_prx_headers)
        self.http_client.bind("message", self._on_prx_message)
        self.http_client.bind("partial", self._on_prx_partial)
        self.http_client.bind("connect", self._on_prx_connect)
        self.http_client.bind("acquire", self._on_prx_acquire)
        self.http_client.bind("close", self._on_prx_close)
        self.http_client.bind("error", self._on_prx_error)

        self.raw_client = netius.clients.RawClient(
            thread=False,
            receive_buffer=int(max_pending * BUFFER_RATIO),
            send_buffer=int(max_pending * BUFFER_RATIO),
            *args,
            **kwargs
        )
        self.raw_client.bind("connect", self._on_raw_connect)
        self.raw_client.bind("data", self._on_raw_data)
        self.raw_client.bind("close", self._on_raw_close)

        self.container = netius.Container(*args, **kwargs)
        self.container.add_base(self)
        self.container.add_base(self.http_client)
        self.container.add_base(self.raw_client)

    def start(self):
        # starts the container this should trigger the start of the
        # event loop in the container and the proper listening of all
        # the connections in the current environment
        self.container.start(self)

    def stop(self):
        # verifies if there's a container object currently defined in
        # the object and in case it does exist propagates the stop call
        # to the container so that the proper stop operation is performed
        if not self.container:
            return
        self.container.stop()

    def cleanup(self):
        http2.HTTP2Server.cleanup(self)

        # saves the container reference so that it may be used latter
        # and then unsets it under the current instance
        container = self.container
        self.container = None

        # verifies if the container is valid and if that's not the case
        # returns the control flow immediately (as expected)
        if not container:
            return

        # runs the cleanup operation on the cleanup, this should properly
        # propagate the operation to the owner container (as expected)
        container.cleanup()

        # unsets the references to the inner clients that compose the
        # proxy server, avoids possible memory leaks
        self.http_client = None
        self.raw_client = None

    def info_dict(self, full=False):
        info = http2.HTTP2Server.info_dict(self, full=full)
        info.update(
            dynamic=self.dynamic,
            throttle=self.throttle,
            max_pending=self.max_pending,
            min_pending=self.min_pending,
            compress_forward_accept=self.compress_forward_accept,
            compress_buffer=self.compress_buffer,
            conn_map_size=len(self.conn_map),
            http_client=self.http_client.info_dict(full=full),
            raw_client=self.raw_client.info_dict(full=full),
        )
        return info

    def connections_dict(self, full=False, parent=False):
        if parent:
            return http2.HTTP2Server.connections_dict(self, full=full)
        return self.container.connections_dict(full=full)

    def connection_dict(self, id, full=False):
        return self.container.connection_dict(id, full=full)

    def tunnel(self, connection, host, port, ssl=False, data=None, response=None):
        """
        Establishes a raw (byte oriented) tunnel between the provided
        (front-end) connection and a newly created back-end connection
        targeting the requested host and port.

        After this call any data received from the front-end is relayed
        verbatim to the back-end (and vice versa) using the raw pump,
        meaning that no HTTP parsing is performed and protocols such as
        WebSocket can be transparently proxied.

        The optional data value is sent to the back-end as soon as the
        connection is established, this is used to forward the original
        upgrade request so that the back-end may reply with the proper
        switching protocols response (flowing back through the tunnel).

        The optional response value is the (code, code string) tuple to
        be sent to the front-end once the back-end connection is
        established, this is used by the CONNECT method to acknowledge
        the tunnel, for transparent upgrades it should be unset so that
        the back-end response is the one flowing back to the front-end.

        :type connection: Connection
        :param connection: The front-end connection that is going to be
        tunneled to the back-end.
        :type host: String
        :param host: The host of the back-end endpoint to connect to.
        :type port: int
        :param port: The port of the back-end endpoint to connect to.
        :type ssl: bool
        :param ssl: If the back-end connection should be established
        using a secure (SSL/TLS) transport.
        :type data: bytes
        :param data: The optional set of bytes to be sent to the back-end
        immediately after the connection is established.
        :type response: Tuple
        :param response: The optional (code, code string) tuple to be
        sent to the front-end on tunnel establishment.
        :rtype: Connection
        :return: The back-end (tunnel) connection that has just been
        created and associated with the front-end connection.
        """

        _connection = self.raw_client.connect(host, port, ssl=ssl)
        _connection.max_pending = self.max_pending
        _connection.min_pending = self.min_pending
        _connection.tunnel_d = data
        _connection.tunnel_r = response
        connection.tunnel_c = _connection
        self.conn_map[_connection] = connection
        return _connection

    def is_upgrade(self, parser):
        """
        Determines if the request associated with the provided parser
        represents a WebSocket upgrade request, this is the case when
        the connection header contains the upgrade token and the upgrade
        header is set to the websocket value.

        :type parser: HTTPParser
        :param parser: The parser of the request that is going to be
        verified for the presence of a WebSocket upgrade.
        :rtype: bool
        :return: If the request represents a WebSocket upgrade request.
        """

        headers = parser.headers
        connection = headers.get("connection", "")
        upgrade = headers.get("upgrade", "")

        # normalizes both values into a single string as the HTTP parser
        # stores repeated headers as a list, using the last definition in
        # such case (consistent with the regular header retrieval)
        if isinstance(connection, (list, tuple)):
            connection = connection[-1] if connection else ""
        if isinstance(upgrade, (list, tuple)):
            upgrade = upgrade[-1] if upgrade else ""

        # matches the upgrade option as a complete (comma separated) token
        # of the connection header instead of a substring, avoiding false
        # positives for values such as 'notupgrade'
        tokens = [value.strip() for value in connection.lower().split(",")]
        return "upgrade" in tokens and upgrade.lower() == "websocket"

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)

        # tries to retrieve the reference to the tunnel connection
        # currently set in the connection in case it does not exists
        # (initial handshake or HTTP client proxy) runs the parse
        # step on the data and then returns immediately
        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c:
            connection.parse(data)
            return

        # verifies that the current size of the pending buffer is greater
        # than the maximum size for the pending buffer the read operations
        # if that the case the read operations must be disabled
        should_throttle = self.throttle and connection.is_throttleable()
        should_disable = should_throttle and tunnel_c.is_exhausted()
        if should_disable:
            connection.disable_read()

        # performs the sending operation on the data but uses the throttle
        # callback so that the connection read operations may be resumed if
        # the buffer has reached certain (minimum) levels
        tunnel_c.send(data, callback=self._throttle)

    def on_connection_d(self, connection):
        http2.HTTP2Server.on_connection_d(self, connection)

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c

        if tunnel_c:
            tunnel_c.close()
        if proxy_c:
            proxy_c.close()

        setattr(connection, "tunnel_c", None)
        setattr(connection, "proxy_c", None)
        setattr(connection, "encoding_b", None)

    def on_stream_d(self, stream):
        http2.HTTP2Server.on_stream_d(self, stream)

        tunnel_c = hasattr(stream, "tunnel_c") and stream.tunnel_c
        proxy_c = hasattr(stream, "proxy_c") and stream.proxy_c

        if tunnel_c:
            tunnel_c.close()
        if proxy_c:
            proxy_c.close()

        setattr(stream, "tunnel_c", None)
        setattr(stream, "proxy_c", None)
        setattr(stream, "encoding_b", None)

    def on_serve(self):
        http2.HTTP2Server.on_serve(self)
        if self.env:
            self.dynamic = self.get_env("DYNAMIC", self.dynamic, cast=bool)
        if self.env:
            self.throttle = self.get_env("THROTTLE", self.throttle, cast=bool)
        if self.env:
            self.trust_origin = self.get_env(
                "TRUST_ORIGIN", self.trust_origin, cast=bool
            )
        if self.env:
            self.compress_forward_accept = self.get_env(
                "COMPRESS_FORWARD_ACCEPT", self.compress_forward_accept, cast=bool
            )
        if self.env:
            self.compress_buffer = self.get_env(
                "COMPRESS_BUFFER", self.compress_buffer, cast=bool
            )
        if self.env:
            self.compress_timeout = self.get_env(
                "COMPRESS_TIMEOUT", self.compress_timeout, cast=float
            )
        if self.is_auto():
            self.info("Using automatic encoding (negotiated) in proxy ...")
        elif self.dynamic:
            self.info("Using dynamic encoding (no content re-encoding) in proxy ...")
        if self.throttle:
            self.info("Throttling connections in proxy ...")
        else:
            self.info("Not throttling connections in proxy ...")
        if self.trust_origin:
            self.info('Origin is considered "trustable" by proxy')

    def on_data_http(self, connection, parser):
        http2.HTTP2Server.on_data_http(self, connection, parser)

        # retrieves the proxy connection and returns in case it's not set
        # (eg: a raw tunnel connection or a not yet established proxy), this
        # also guards against the attribute being explicitly unset to None
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        if not proxy_c:
            return

        should_throttle = self.throttle and connection.is_throttleable()
        should_disable = should_throttle and proxy_c.is_exhausted()
        if should_disable:
            connection.disable_read()
        proxy_c.flush(force=True, callback=self._throttle)

    def on_headers(self, connection, parser):
        # resolves the encoding as soon as the request headers are available,
        # this must happen before the sub-classes rewrite the headers of the
        # request (the header map is the one of the front-end parser)
        connection.resolve_encoding(parser)

    def on_partial(self, connection, parser, data):
        # retrieves the proxy connection and returns in case it's not set
        # (eg: a raw tunnel connection or a not yet established proxy), this
        # also guards against the attribute being explicitly unset to None
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        if not proxy_c:
            return

        should_throttle = self.throttle and connection.is_throttleable()
        should_disable = should_throttle and proxy_c.is_exhausted()
        if should_disable:
            connection.disable_read()
        proxy_c.send_base(data, force=True, callback=self._throttle)

    def on_available(self, connection, parser):
        proxy_c = connection.proxy_c
        if not proxy_c.renable == False:
            return
        if not connection.is_restored():
            return
        proxy_c.enable_read()
        self.reads((proxy_c.socket,), state=False)

    def on_unavailable(self, connection, parser):
        proxy_c = connection.proxy_c
        if proxy_c.renable == False:
            return
        should_throttle = self.throttle and proxy_c.is_throttleable()
        should_disable = should_throttle and connection.is_exhausted()
        if not should_disable:
            return
        proxy_c.disable_read()

    def build_connection(self, socket, address, ssl=False):
        return ProxyConnection(
            owner=self,
            socket=socket,
            address=address,
            ssl=ssl,
            encoding=self.encoding,
            max_pending=self.max_pending,
            min_pending=self.min_pending,
        )

    def _throttle(self, _connection):
        # connection may be unset for situations where the transport
        # is already closed, in that case the control flow should be
        # returned immediately (nothing to do)
        if _connection == None:
            return

        # verifies that the pending send buffer has drained below the
        # minimum pending threshold, if it hasn't the connection is still
        # under back-pressure and throttling should remain active
        if not _connection.is_restored():
            return

        # tries to resolve a protocol from the possible transport
        # parameter (parameter can be a protocol or a transport)
        # and then uses the resolved value as the key, notice that
        # in case the connection is in a final closing flush state
        # (graceful closing) the connection mapping may have already
        # been removed (requires early return)
        _connection_key = getattr(_connection, "_protocol", _connection)
        if not _connection_key in self.conn_map:
            return
        connection = self.conn_map[_connection_key]

        if not connection.renable == False:
            return
        connection.enable_read()
        self.reads((connection.socket,), state=False)

    def _prx_close(self, connection):
        connection.close(flush=True)

    def _prx_keep(self, connection):
        pass

    def _prx_throttle(self, connection):
        if connection == None:
            return
        if not connection.is_restored():
            return

        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        if not proxy_c:
            return
        if not proxy_c.renable == False:
            return

        proxy_c.enable_read()
        self.reads((proxy_c.socket,), state=False)

    def _prx_encoding(self, connection, parser, headers, content_encoding):
        """
        Runs the negotiation of the response encoding for the automatic
        encoding mode, submitting the back-end response to the complete
        set of eligibility gates and resolving the content coding to be
        applied to it.

        The single rule of the automatic mode is that only the payloads
        that arrive from the back-end under the identity coding may be
        compressed, this is what removes both the decoding leg and the
        failures caused by codings that are not implemented.

        :type connection: Connection
        :param connection: The front-end connection (or stream) that the
        response is going to be sent through.
        :type parser: HTTPParser
        :param parser: The parser of the back-end response.
        :type headers: Dictionary
        :param headers: The headers of the back-end response, the identity
        content encoding is removed from them when present.
        :type content_encoding: String
        :param content_encoding: The content coding of the back-end response.
        :rtype: Dictionary
        :return: The codec to be used in the compression of the response or
        an invalid value in case it should be forwarded byte-identical.
        """

        # the response is forwarded byte-identical by default, note that the
        # per response state is set explicitly so that both postures may
        # co-exist in the same server (and even in the same connection)
        connection.dynamic = True
        connection.encodings_a = None

        # the payload must arrive from the back-end under the identity coding,
        # any other coding is passed through untouched, note that the explicit
        # identity coding is removed so that the resolved one may be announced
        if content_encoding:
            if not content_encoding.strip().lower() == "identity":
                return None
            del headers["content-encoding"]

        # the compression of the payload requires the chunked framing, so an
        # older front-end (that has no such framing) is never compressed
        if connection.parser.version < netius.common.HTTP_11:
            return None

        # a payload that is either not going to exist or that must be preserved
        # as is cannot be compressed, this covers the informational, the empty
        # and the partial status codes plus the HEAD method
        code = int(parser.code_s)
        if code < 200 or code in http.EMPTY_CODES or code == 206:
            return None
        method = connection.parser.method
        if method and method.upper() == "HEAD":
            return None

        # the no-transform cache directive explicitly forbids the changing of
        # the coding of the payload, the same applies to the partial payloads
        # that are identified by the presence of the content range header
        cache_control = self._prx_header(headers, "cache-control") or ""
        if "no-transform" in cache_control.lower():
            return None
        if "content-range" in headers:
            return None

        # the media type must be one for which the compression provides a
        # relevant gain, otherwise processor time would just be wasted
        if not self.is_compressible(self._prx_header(headers, "content-type")):
            return None

        # the payload must be large enough to pay for the framing overhead and
        # small enough to keep the (synchronous) cost of the compression
        # bounded, an undeclared length is handled by the deferred decision
        if parser.content_l > self.compress_max:
            return None
        if parser.content_l >= 0 and parser.content_l < self.compress_min:
            return None

        # from this point on the representation depends on the codings that
        # are accepted by the client, so the vary header must be announced
        # even in case no compression ends up being performed
        encodings = connection.parser.get_encodings()
        connection.encodings_a = encodings

        # resolves the content coding from the ones that are both enabled in
        # the server and accepted by the client (server preference order)
        return self._prx_codec(encodings)

    def _prx_header(self, headers, name):
        """
        Obtains a single (string) value for the requested header, as a
        repeated header is stored as a sequence of values by the parser
        and the last definition is the one that prevails.

        :type headers: Dictionary
        :param headers: The map of headers from which the value is going
        to be retrieved.
        :type name: String
        :param name: The (lower cased) name of the header to retrieve.
        :rtype: String
        :return: The single value of the requested header or an invalid
        value in case it's not defined.
        """

        value = headers.get(name, None)
        if isinstance(value, (list, tuple)):
            value = value[-1] if value else None
        return value

    def _prx_decodable(self, content_encoding):
        return content_encoding.strip().lower() in netius.clients.http.DECODINGS

    def _prx_codec(self, encodings):
        """
        Resolves the content coding to be used in the compression of a
        response from the codings that are both enabled in the server and
        accepted by the client, respecting the server preference order.

        :type encodings: List
        :param encodings: The sequence of content codings accepted by the
        client, ordered by descending preference.
        :rtype: Dictionary
        :return: The codec of the resolved content coding or an invalid
        value in case no common coding exists.
        """

        for name in self.compress_encodings:
            if not name in encodings:
                continue
            codec = http.CODECS.get(name, None)
            if not codec:
                continue
            return codec
        return None

    def _prx_compress(self, connection, codec):
        connection.dynamic = False
        connection.set_encoding(codec["encoding"])
        connection.encoding_c = codec["name"]

    def _prx_hold(
        self, connection, parser, headers, codec, version_s, code_s, status_s
    ):
        """
        Holds the response of a back-end that streams the payload with no
        declared length, so that the decision on the compression is only
        taken once enough of the payload has been received.

        The response is released either by `_on_prx_partial` (as soon as
        the minimum size is crossed), by `_on_prx_message` (below the
        minimum size, with the exact length) or by the flush deadline.

        :type connection: Connection
        :param connection: The front-end connection (or stream) that the
        response is going to be sent through.
        :type parser: HTTPParser
        :param parser: The parser of the back-end response.
        :type headers: Dictionary
        :param headers: The headers of the back-end response.
        :type codec: Dictionary
        :param codec: The codec to be used in case the minimum size for
        the compression ends up being crossed.
        :type version_s: String
        :param version_s: The HTTP version of the back-end response.
        :type code_s: String
        :param code_s: The status code of the back-end response.
        :type status_s: String
        :param status_s: The status message of the back-end response.
        """

        # applies the headers while the back-end connection is still around,
        # note that the encoding related ones are re-applied at release time
        # as the encoding is only resolved then (the connection is plain here)
        with connection.ctx_request():
            self._apply_headers(connection.parser, connection, parser, headers)

        buffer = dict(
            headers=headers,
            version=version_s,
            code=int(code_s),
            code_s=status_s,
            codec=codec,
            data=[],
            length=0,
        )
        connection.encoding_b = buffer

        def release():
            # only releases the response that has armed this deadline, as
            # the deadline of a previous response of the same (keep alive)
            # connection may still be pending
            if not connection.encoding_b is buffer:
                return
            self._prx_release(connection)

        # schedules the flush deadline so that a back-end that trickles the
        # payload does not hold the front-end response indefinitely
        self.delay(release, timeout=self.compress_timeout)

    def _prx_release(self, connection, codec=None, length=None):
        """
        Releases a response that is being held for the deferred encoding
        decision, sending both the headers and the payload received so far
        to the front-end connection.

        :type connection: Connection
        :param connection: The front-end connection (or stream) that is
        holding the response to be released.
        :type codec: Dictionary
        :param codec: The codec to be used in the compression of the
        payload, if unset the payload is forwarded byte-identical.
        :type length: int
        :param length: The exact length of the payload, only available in
        case the complete response has already been received.
        """

        # retrieves the structure that holds the deferred response returning
        # immediately in case there's none (the response has been released)
        buffer = hasattr(connection, "encoding_b") and connection.encoding_b
        if not buffer:
            return
        connection.encoding_b = None

        # in case a codec is provided the connection is set to compress the
        # payload, otherwise it's forwarded byte-identical announcing the
        # exact length whenever the complete payload is already known, note
        # that the header names have already been normalized (upper case)
        headers = buffer["headers"]
        if codec:
            self._prx_compress(connection, codec)
        elif length == None:
            connection.set_chunked()
        else:
            connection.set_plain()
            headers["Content-Length"] = str(length)

        # re-applies the encoding related headers now that the encoding has
        # been resolved and then sends them to the front-end connection, the
        # request context is applied so that the proper encoding is used
        with connection.ctx_request():
            self._apply_connection(connection, headers)
        connection.send_header(
            headers=headers,
            version=buffer["version"],
            code=buffer["code"],
            code_s=buffer["code_s"],
        )

        # sends the payload that has been held so far using the encoding
        # that has just been resolved for the connection
        for data in buffer["data"]:
            connection.send_part(data, final=False, callback=self._prx_throttle)

    def _raw_throttle(self, connection):
        if connection == None:
            return
        if not connection.is_restored():
            return

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c:
            return
        if not tunnel_c.renable == False:
            return

        tunnel_c.enable_read()
        self.reads((tunnel_c.socket,), state=False)

    def _on_prx_headers(self, client, parser, headers):
        # retrieves the owner of the parser as the client connection
        # and then retrieves all the other HTTP specific values
        _connection = parser.owner
        code_s = parser.code_s
        status_s = parser.status_s
        version_s = parser.version_s

        # creates a new dictionary from the provided one, so that no overlap
        # in values occurs (would destroy the original data)
        headers = dict(headers)

        # resolves the client connection into the proper proxy connection
        # to be used to send the headers (and status line) to the client
        connection = self.conn_map[_connection]

        # determines if the automatic encoding mode is enabled, under this mode
        # the payload of the back-end is never decoded (only the identity ones
        # are re-encoded) and so the content encoding is always preserved
        is_auto = self.is_auto()

        # in dynamic mode the body is forwarded byte-identical, so we must
        # preserve `content-encoding` so the client knows how to decode it,
        # without dynamic mode the proxy may re-encode and the header is
        # popped (default behaviour)
        if self.dynamic or is_auto:
            content_encoding = self._prx_header(headers, "content-encoding")
        else:
            content_encoding = self._prx_header(headers, "content-encoding")
            headers.pop("content-encoding", None)
            # in case the back-end used a coding that cannot be decoded the
            # payload has to be forwarded byte-identical, otherwise the coding
            # announced to the client would not match the payload sent to it
            if content_encoding and not self._prx_decodable(content_encoding):
                headers["content-encoding"] = content_encoding
                connection.dynamic = True

        # obtains the transfer encoding value from the headers, this is required
        # for the proper handling of the content length
        transfer_encoding = headers.pop("transfer-encoding", None)

        # under the automatic mode the response is submitted to the complete
        # set of eligibility gates, resolving the content coding to be applied
        # to it, this must run before any of the length related operations as
        # it defines the per response dynamic (no re-encoding) state
        codec = (
            self._prx_encoding(connection, parser, headers, content_encoding)
            if is_auto
            else None
        )

        # in case the back-end streams the payload with no declared length the
        # decision is deferred until enough of it has been received, holding
        # both the headers and the initial payload in the connection
        if codec and parser.content_l == -1 and self.compress_buffer:
            return self._prx_hold(
                connection, parser, headers, codec, version_s, code_s, status_s
            )

        # in case a content coding has been resolved the connection is set to
        # compress the payload of the response, disabling the pass-through
        if codec:
            self._prx_compress(connection, codec)

        # if either the proxy connection or the back-end one is compressed
        # the length values of the connection are considered unreliable and
        # some extra operation must be defined, note that in case the dynamic
        # (no re-encoding) support is enabled the length is always reliable
        unreliable_length = (
            _connection.current > http.CHUNKED_ENCODING
            or connection.current > http.CHUNKED_ENCODING
            or parser.content_l == -1
        )
        unreliable_length &= not connection.is_dynamic()

        # in case the content length is unreliable some of the headers defined
        # must be removed so that no extra connection error occurs, as the size
        # of the content from one end point to the other may change
        if unreliable_length:
            if "content-length" in headers:
                del headers["content-length"]
            if "accept-ranges" in headers:
                del headers["accept-ranges"]

        # in case the length of the data is not reliable and the current connection
        # is plain encoded a proper set of operation must be properly handled including
        # the forcing of the chunked encoding or the connection drop at the end of the
        # message strategies
        if unreliable_length and connection.current < http.CHUNKED_ENCODING:
            if parser.version < netius.common.HTTP_11:
                connection.parser.keep_alive = False
            else:
                connection.set_encoding(http.CHUNKED_ENCODING)

        # tries to use the content encoding value to determine the minimum encoding
        # that allows the content encoding to be kept (compatibility support), this
        # heuristic is only applied in case the dynamic option is enabled
        content_encoding_c = http.ENCODING_MAP.get(content_encoding, connection.current)
        content_encoding_t = http.ENCODING_MAP.get(
            transfer_encoding, connection.current
        )
        target_encoding = max(content_encoding_c, content_encoding_t)
        if connection.is_dynamic() and target_encoding > connection.current:
            connection.set_encoding(target_encoding)

        # applies the headers meaning that the headers are going to be
        # processed so that they represent the proper proxy operation
        # that is going to be done with the passing of the data, note
        # that the connection request context is applied so that the
        # proper encoding is used in the connection header application
        with connection.ctx_request():
            self._apply_headers(connection.parser, connection, parser, headers)

        # runs the send headers operation that will start the transmission
        # of the headers for the requested proxy operation, the concrete
        # semantics of the transmission should dependent on the version of
        # the protocol that is going to be used in the transmission
        connection.send_header(
            headers=headers, version=version_s, code=int(code_s), code_s=status_s
        )

    def _on_prx_message(self, client, parser, message):
        # retrieves the back-end connection from the provided parser this
        # is going to be used for the reverse connection resolution process
        _connection = parser.owner

        # sets the current client connection as not waiting and then retrieves
        # the requester connection associated with the client (back-end)
        # connection in order to be used in the current processing
        _connection.waiting = False
        connection = self.conn_map[_connection]

        # in case the encoding decision is still deferred the response has
        # ended below the minimum size for the compression, so it's released
        # as identity announcing the exact length of the payload
        buffer = hasattr(connection, "encoding_b") and connection.encoding_b
        if buffer:
            self._prx_release(connection, length=buffer["length"])

        # creates the clojure function that will be used to close the
        # current client connection and that may or may not close the
        # corresponding back-end connection (as defined in specification)
        def close(connection):
            connection.close(flush=True)

        # verifies that the connection is meant to be kept alive, the
        # connection is meant to be kept alive when both the client and
        # the final (back-end) server respond with the keep alive flag
        keep_alive = parser.keep_alive and connection.parser.keep_alive

        # defines the proper callback function to be called at the end
        # of the flushing of the connection according to the result of
        # the keep alive evaluation (as defined in specification)
        if keep_alive:
            callback = None
        else:
            callback = close

        # runs the final flush operation in the connection making sure that
        # every data that is pending is properly flushed, this is especially
        # important for chunked or compressed connections
        connection.flush_s(callback=callback)

    def _on_prx_partial(self, client, parser, data):
        # retrieves the owner of the proxy parser as the proxy connection
        # and then uses the connection to decode the data to obtain the raw
        # value of it, this is required as gzip compression may exist, note
        # that under the automatic mode the payload is never decoded as only
        # the identity encoded ones are eligible for re-encoding
        _connection = parser.owner
        data = data if self.dynamic or self.is_auto() else _connection.raw_data(data)

        # retrieves the peer connection and the structure that may be holding
        # the response while the encoding decision is deferred
        connection = self.conn_map[_connection]
        buffer = hasattr(connection, "encoding_b") and connection.encoding_b

        # tries to send the new data chunk back to the peer connection using
        # the currently defined encoding (as expected), note that additional
        # throttling operations may apply, taking into account both the data
        # pending in the front-end and the one being held
        pending = buffer["length"] if buffer else 0
        should_throttle = self.throttle and _connection.is_throttleable()
        should_disable = should_throttle and (
            connection.is_exhausted() or pending > self.max_pending
        )
        if should_disable:
            _connection.disable_read()

        # in case the decision is still deferred the data is held until either
        # the minimum size for the compression is crossed (the compression is
        # committed) or the response ends below it (forwarded as identity)
        if buffer:
            buffer["data"].append(data)
            buffer["length"] += len(data)
            if buffer["length"] >= self.compress_min:
                self._prx_release(connection, codec=buffer["codec"])
            return

        connection.send_part(data, final=False, callback=self._prx_throttle)

    def _on_prx_connect(self, client, _connection):
        _connection.waiting = False

    def _on_prx_acquire(self, client, _connection):
        _connection.waiting = False

    def _on_prx_close(self, client, _connection):
        """
        Handles the closing of a back-end proxy connection.

        The `_connection` parameter may be either a Connection object
        (old Base architecture) or an `HTTPProtocol` instance (new
        Agent/Protocol architecture via Container compat layer),
        so attribute access on it must not assume a specific type.

        :type client: HTTPClient
        :param client: The HTTP client that owns the connection.
        :type _connection: Connection/HTTPProtocol
        :param _connection: The back-end connection or protocol
        that has been closed.
        """

        # retrieves the reference to the parent class value
        # so that it can be used for class level operations
        cls = self.__class__

        # retrieves the front-end connection associated with
        # the back-end to be used for the operations in case
        # no connection is retrieved returns the control flow
        # to the caller method immediately (nothing done)
        connection = self.conn_map.get(_connection, None)
        if not connection:
            self.debug(
                "Backend close callback for unmapped connection '%s'",
                _connection.id,
            )
            return

        # in case the connection is under the waiting state
        # the forbidden response is set to the client otherwise
        # the front-end connection is closed immediately, note
        # that `_connection` may be either a `Connection` or a
        # `Protocol` instance
        if _connection.waiting:
            connection.send_response(
                data=cls.build_data(
                    "Forbidden",
                    url=(
                        _connection.error_url
                        if hasattr(_connection, "error_url")
                        else None
                    ),
                ),
                headers=dict(connection="close"),
                code=403,
                code_s="Forbidden",
                apply=True,
                callback=self._prx_close,
            )
        else:
            connection.close(flush=True)

        # removes the waiting state from the connection and
        # the removes the back-end to front-end connection
        # relation for the current proxy connection
        _connection.waiting = False
        del self.conn_map[_connection]

    def _on_prx_error(self, client, _connection, error):
        """
        Handles an error in the back-end proxy connection. The
        `_connection` parameter may be either a `Connection` object
        or an `HTTPProtocol` instance depending on the architecture.

        :type client: HTTPClient
        :param client: The HTTP client that owns the connection.
        :type _connection: Connection/HTTPProtocol
        :param _connection: The back-end connection or protocol
        that encountered the error.
        :type error: Exception
        :param error: The exception that triggered the error.
        """

        # retrieves the reference to the parent class value
        # so that it can be used for class level operations
        cls = self.__class__

        # retrieves the front-end connection associated with
        # the proxy connection, this value is going to be
        # if sending the message to the final client
        connection = self.conn_map.get(_connection, None)
        if not connection:
            return

        # constructs the message string that is going to be
        # sent as part of the response from the proxy indicating
        # the unexpected error, then in case the connection is
        # still under the (initial) waiting state sends the same
        # message to the final client connection (indicating error)
        # note that the recovery from the error (disconnect should
        # be handled by the error manager, and that should imply
        # a closing operation on the original/proxy connection)
        error_m = str(error) or "Unknown proxy relay error"
        if _connection.waiting:
            connection.send_response(
                data=cls.build_text(error_m),
                headers=dict(connection="close"),
                code=500,
                code_s="Internal Error",
                apply=True,
            )

        # sets the connection as not waiting, so that no more
        # messages are sent as part of the closing chain
        _connection.waiting = False

    def _on_raw_connect(self, client, _connection):
        connection = self.conn_map[_connection]

        # retrieves the optional response and data values that may have
        # been associated with the tunnel connection, the response is
        # sent to the front-end to acknowledge the tunnel and the data
        # is forwarded to the back-end (eg: the original upgrade request)
        response = hasattr(_connection, "tunnel_r") and _connection.tunnel_r
        data = hasattr(_connection, "tunnel_d") and _connection.tunnel_d

        # in case a response tuple is defined sends the proper acknowledge
        # response to the front-end connection (eg: CONNECT method), note
        # that for transparent upgrades no response is sent as the back-end
        # one is the one that should flow back to the front-end
        if response:
            code, code_s = response
            connection.send_response(code=code, code_s=code_s, apply=True)

        # in case there's data to be sent to the back-end forwards it as
        # soon as the connection is established, this is required so that
        # the back-end may reply with the proper switching protocols
        # response that is going to flow back through the raw tunnel, the
        # reference is unset afterwards as it's no longer required (avoids
        # retaining the request buffer for the lifetime of the tunnel)
        if data:
            _connection.send(data)
            _connection.tunnel_d = None

    def _on_raw_data(self, client, _connection, data):
        connection = self.conn_map[_connection]
        should_throttle = self.throttle and _connection.is_throttleable()
        should_disable = should_throttle and connection.is_exhausted()
        if should_disable:
            _connection.disable_read()
        connection.send(data, callback=self._raw_throttle)

    def _on_raw_close(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.close(flush=True)
        del self.conn_map[_connection]

    def _apply_headers(self, parser, connection, parser_prx, headers, upper=True):
        if upper:
            self._headers_upper(headers)
        self._apply_via(parser_prx, headers)
        self._apply_all(parser_prx, connection, headers, replace=True)

    def _apply_accept(self, headers):
        """
        Applies the accept encoding header of the request that is going
        to be sent to the back-end.

        Under the automatic mode the proxy is the compression authority
        for the edge, so the back-end is asked for the identity coding
        keeping the payload eligible for compression, unless the
        forwarding of the client codings is explicitly requested.

        :type headers: Dictionary
        :param headers: The headers of the request that is going to be
        sent to the back-end, changed in place.
        """

        if not self.is_auto():
            return
        if self.compress_forward_accept:
            return
        headers["accept-encoding"] = "identity"

    def _apply_via(self, parser_prx, headers):
        # retrieves the various elements of the parser that are going
        # to be used for the creation of the via string value, and
        # processes some of them to take them into the normal form
        connection = parser_prx.owner
        version_s = parser_prx.version_s
        version_s = version_s.split("/", 1)[1]

        # unpacks the current connection's address so that the host
        # value is possible to be retrieved (as expected)
        host, _port = connection.address

        # retrieves the server value from the current headers, as it
        # is going to be used for the creation of the partial via
        # value (the technology part of the string)
        server = headers.get("Server", None)

        # creates the via string value taking into account if the server
        # part of the string exists or not (different template)
        if server:
            via_s = "%s %s (%s)" % (version_s, host, server)
        else:
            via_s = "%s %s" % (version_s, host)

        # tries to retrieve the current via string (may already exits)
        # and appends the created string to the base string or creates
        # a new one (as defined in the HTTP specification)
        via = headers.get("Via", "")
        if via:
            via += ", "
        via += via_s
        headers["Via"] = via
