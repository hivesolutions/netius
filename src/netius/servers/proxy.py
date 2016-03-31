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

import netius.common
import netius.clients

from . import http

BUFFER_RATIO = 1.5
""" The ration for the calculus of the internal socket
buffer size from the maximum pending buffer size """

MIN_RATIO = 0.8
""" The ration for the calculus of the minimum pending
value this is going to be used to re-enable the operation
and start the filling of the buffer again """

MAX_PENDING = 65536
""" The size in bytes considered to be the maximum
allowed in the sending buffer, this maximum value
avoids the starvation of the producer to consumer
relation that could cause memory problems """

class ProxyConnection(http.HTTPConnection):

    def open(self, *args, **kwargs):
        http.HTTPConnection.open(self, *args, **kwargs)
        self.parser.store = False
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_partial", self.on_partial)
        self.parser.bind("on_chunk", self.on_chunk)

    def on_headers(self):
        self.owner.on_headers(self, self.parser)

    def on_partial(self, data):
        self.owner.on_partial(self, self.parser, data)

    def on_chunk(self, range):
        self.owner.on_chunk(self, self.parser, range)

class ProxyServer(http.HTTPServer):

    def __init__(
        self,
        throttle = True,
        trust_origin = False,
        max_pending = MAX_PENDING,
        *args,
        **kwargs
    ):
        http.HTTPServer.__init__(
            self,
            receive_buffer_c = int(max_pending * BUFFER_RATIO),
            send_buffer_c = int(max_pending * BUFFER_RATIO),
            *args,
            **kwargs
        )
        self.throttle = throttle
        self.trust_origin = trust_origin
        self.max_pending = max_pending
        self.min_pending = int(max_pending * MIN_RATIO)
        self.conn_map = {}

        self.http_client = netius.clients.HTTPClient(
            thread = False,
            auto_release = False,
            receive_buffer = max_pending,
            send_buffer = max_pending,
            *args,
            **kwargs
        )
        self.http_client.bind("headers", self._on_prx_headers)
        self.http_client.bind("message", self._on_prx_message)
        self.http_client.bind("partial", self._on_prx_partial)
        self.http_client.bind("chunk", self._on_prx_chunk)
        self.http_client.bind("connect", self._on_prx_connect)
        self.http_client.bind("acquire", self._on_prx_acquire)
        self.http_client.bind("close", self._on_prx_close)
        self.http_client.bind("error", self._on_prx_error)

        self.raw_client = netius.clients.RawClient(
            thread = False,
            receive_buffer = int(max_pending * BUFFER_RATIO),
            send_buffer = int(max_pending * BUFFER_RATIO),
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
        if not self.container: return
        self.container.stop()

    def cleanup(self):
        http.HTTPServer.cleanup(self)
        self.container = None
        self.http_client.destroy()
        self.raw_client.destroy()

    def info_dict(self, full = False):
        info = http.HTTPServer.info_dict(self, full = full)
        info.update(
            throttle = self.throttle,
            max_pending = self.max_pending,
            min_pending = self.min_pending,
            http_client = self.http_client.info_dict(full = full),
            raw_client = self.raw_client.info_dict(full = full)
        )
        return info

    def connections_dict(self, full = False, parent = False):
        if parent: return http.HTTPServer.connections_dict(self, full = full)
        return self.container.connections_dict(full = full)

    def connection_dict(self, id, full = False):
        return self.container.connection_dict(id, full = full)

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)

        # tries to retrieve the reference to the tunnel connection
        # currently set in the connection in case it does not exists
        # (initial handshake or http client proxy) runs the parse
        # step on the data and then returns immediately
        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c: connection.parse(data); return

        # verifies that the current size of the pending buffer is greater
        # than the maximum size for the pending buffer the read operations
        # if that the case the read operations must be disabled
        should_disable = self.throttle and tunnel_c.pending_s > self.max_pending
        if should_disable: connection.disable_read()

        # performs the sending operation on the data but uses the throttle
        # callback so that the connection read operations may be resumed if
        # the buffer has reached certain (minimum) levels
        tunnel_c.send(data, callback = self._throttle)

    def on_connection_d(self, connection):
        http.HTTPServer.on_connection_d(self, connection)

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c

        if tunnel_c: tunnel_c.close()
        if proxy_c: proxy_c.close()

        setattr(connection, "tunnel_c", None)
        setattr(connection, "proxy_c", None)

    def on_serve(self):
        http.HTTPServer.on_serve(self)
        if self.env: self.throttle = self.get_env("THROTTLE", self.throttle, cast = bool)
        if self.env: self.trust_origin = self.get_env("TRUST_ORIGIN", self.trust_origin, cast = bool)
        if self.throttle: self.info("Throttling connections in the proxy ...")
        else: self.info("Not throttling connections in the proxy ...")
        if self.trust_origin: self.info("Origin is considered \"trustable\" by proxy")

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)
        if not parser.chunked: return

        proxy_c = connection.proxy_c

        should_disable = self.throttle and proxy_c.pending_s > self.max_pending
        if should_disable: connection.disable_read()
        proxy_c.send(b"0\r\n\r\n", force = True, callback = self._throttle)

    def on_headers(self, connection, parser):
        pass

    def on_partial(self, connection, parser, data):
        if parser.chunked: return

        proxy_c = connection.proxy_c

        should_disable = self.throttle and proxy_c.pending_s > self.max_pending
        if should_disable: connection.disable_read()
        proxy_c.send(data, force = True, callback = self._throttle)

    def on_chunk(self, connection, parser, range):
        if not parser.chunked: return

        start, end = range
        data = parser.message[start:end]
        data_s = b"".join(data)
        data_l = len(data_s)
        header = netius.legacy.bytes("%x\r\n" % data_l)
        chunk = header + data_s + b"\r\n"

        proxy_c = connection.proxy_c

        should_disable = self.throttle and proxy_c.pending_s > self.max_pending
        if should_disable: connection.disable_read()
        proxy_c.send(chunk, force = True, callback = self._throttle)

    def new_connection(self, socket, address, ssl = False):
        return ProxyConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding
        )

    def _throttle(self, _connection):
        if _connection.pending_s > self.min_pending: return
        connection = self.conn_map[_connection]
        if not connection.renable == False: return
        connection.enable_read()
        self.reads((connection.socket,), state = False)

    def _prx_close(self, connection):
        connection.close(flush = True)

    def _prx_keep(self, connection):
        pass

    def _prx_throttle(self, connection):
        if connection.pending_s > self.min_pending: return

        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        if not proxy_c: return
        if not proxy_c.renable == False: return

        proxy_c.enable_read()
        self.http_client.reads((proxy_c.socket,), state = False)

    def _raw_throttle(self, connection):
        if connection.pending_s > self.min_pending: return

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c: return
        if not tunnel_c.renable == False: return

        tunnel_c.enable_read()
        self.raw_client.reads((tunnel_c.socket,), state = False)

    def _on_prx_headers(self, client, parser, headers):
        # retrieves the owner of the parser as the client connection
        # and then retrieves all the other http specific values
        _connection = parser.owner
        code_s = parser.code_s
        status_s = parser.status_s
        version_s = parser.version_s

        # applies the headers meaning that the headers are going to be
        # processed so that they represent the proper proxy operation
        # that is going to be done with the passing of the data
        self._apply_headers(parser, headers)

        # resolves the client connection into the proper proxy connection
        # to be used to send the headers (and status line) to the client
        connection = self.conn_map[_connection]

        # creates a buffer list that will hold the complete set of
        # lines that compose both the status lines and the headers
        # then appends the start line and the various header lines
        # to it so that it contains all of them
        buffer = []
        buffer.append("%s %s %s\r\n" % (version_s, code_s, status_s))
        for key, value in headers.items():
            key = netius.common.header_up(key)
            if not type(value) == list: value = (value,)
            for _value in value: buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")

        # joins the header strings list as the data string that contains
        # the headers and then sends the value through the connection
        data = "".join(buffer)
        connection.send(data)

    def _on_prx_message(self, client, parser, message):
        # retrieves the back-end connection from the provided parser and
        # then evaluates if that connection is of type chunked
        _connection = parser.owner
        is_chunked = parser.chunked

        # sets the current client connection as not waiting and then retrieves
        # the requester connection associated with the client (back-end)
        # connection in order to be used in the current processing
        _connection.waiting = False
        connection = self.conn_map[_connection]

        # creates the clojure function that will be used to close the
        # current client connection and that may or may not close the
        # corresponding back-end connection (as defined in specification)
        def close(connection): connection.close(flush = True)

        # verifies that the connection is meant to be kept alive, the
        # connection is meant to be kept alive when both the client and
        # the final (back-end) server respond with the keep alive flag
        keep_alive = parser.keep_alive and connection.parser.keep_alive

        # defines the proper callback function to be called at the end
        # of the flushing of the connection according to the result of
        # the keep alive evaluation (as defined in specification)
        if keep_alive: callback = None
        else: callback = close

        # verifies if the current connection is of type chunked an in case
        # it is must first send the final (close) chunk and then call the
        # proper callback otherwise in case it's a plain connection the
        # callback is immediately called in case it's defined
        if is_chunked: connection.send("0\r\n\r\n", callback = callback)
        elif callback: connection.send("", callback = callback)

    def _on_prx_partial(self, client, parser, data):
        _connection = parser.owner
        is_chunked = parser.chunked

        if is_chunked: return

        connection = self.conn_map[_connection]
        should_disable = self.throttle and connection.pending_s > self.max_pending
        if should_disable: _connection.disable_read()
        connection.send(data, callback = self._prx_throttle)

    def _on_prx_chunk(self, client, parser, range):
        _connection = parser.owner
        connection = self.conn_map[_connection]

        start, end = range
        data = parser.message[start:end]
        data_s = b"".join(data)
        data_l = len(data_s)
        header = netius.legacy.bytes("%x\r\n" % data_l)
        chunk = header + data_s + b"\r\n"

        should_disable = self.throttle and connection.pending_s > self.max_pending
        if should_disable: _connection.disable_read()
        connection.send(chunk, callback = self._prx_throttle)

    def _on_prx_connect(self, client, _connection):
        _connection.waiting = False

    def _on_prx_acquire(self, client, _connection):
        _connection.waiting = False

    def _on_prx_close(self, client, _connection):
        # retrieves the front-end connection associated with
        # the back-end to be used for the operations in case
        # no connection is retrieved returns the control flow
        # to the caller method immediately (nothing done)
        connection = self.conn_map.get(_connection, None)
        if not connection: return

        # in case the connection is under the waiting state
        # the forbidden response is set to the client otherwise
        # the front-end connection is closed immediately
        if _connection.waiting: connection.send_response(
            data = "Forbidden",
            headers = dict(
                connection = "close"
            ),
            code = 403,
            code_s = "Forbidden",
            apply = True,
            callback = self._prx_close
        )
        else: connection.close(flush = True)

        # removes the waiting state from the connection and
        # the removes the back-end to front-end connection
        # relation for the current proxy connection
        _connection.waiting = False
        del self.conn_map[_connection]

    def _on_prx_error(self, client, _connection, error):
        # retrieves the front-end connection associated with
        # the proxy connection, this value is going to be
        # if sending the message to the final client
        connection = self.conn_map.get(_connection, None)
        if not connection: return

        # constructs the message string that is going to be
        # sent as part of the response from the proxy indicating
        # the unexpected error, then in case the connection is
        # still under the (initial) waiting state sends the same
        # message to the final client connection (indicating error)
        # note that the recovery from the error (disconnect should
        # be handled by the error manager, and that should imply
        # a closing operation on the original/proxy connection)
        error_m = str(error) or "Unknown proxy relay error"
        if _connection.waiting: connection.send_response(
            data = error_m,
            headers = dict(
                connection = "close"
            ),
            code = 500,
            code_s = "Internal Error",
            apply = True
        )

        # sets the connection as not waiting, so that no more
        # messages are sent as part of the closing chain
        _connection.waiting = False

    def _on_raw_connect(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.send_response(
            code = 200,
            code_s = "Connection established",
            apply = True
        )

    def _on_raw_data(self, client, _connection, data):
        connection = self.conn_map[_connection]
        should_disable = self.throttle and connection.pending_s > self.max_pending
        if should_disable: _connection.disable_read()
        connection.send(data, callback = self._raw_throttle)

    def _on_raw_close(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.close(flush = True)
        del self.conn_map[_connection]

    def _apply_headers(self, parser, headers, upper = True):
        if upper: self._headers_upper(headers)
        self._apply_via(parser, headers)
        self._apply_base(headers, replace = True)

    def _apply_via(self, parser, headers):
        # retrieves the various elements of the parser that are going
        # to be used for the creation of the via string value, and
        # processes some of them to take them into the normal form
        connection = parser.owner
        version_s = parser.version_s
        version_s = version_s.split("/", 1)[1]

        # unpacks the current connectiont's address so that the host
        # value is possible to be retrieved (as expected)
        host, _port = connection.address

        # retrieves the server value from the current headers, as it
        # is going to be used for the creation of the partial via
        # value (the technology part of the string)
        server = headers.get("Server", None)

        # creates the via string value taking into account if the server
        # part of the string exists or not (different template)
        if server: via_s = "%s %s (%s)" % (version_s, host, server)
        else: via_s = "%s %s" % (version_s, host)

        # tries to retrieve the current via string (may already exits)
        # and appends the created string to the base string or creates
        # a new one (as defined in the http specification)
        via = headers.get("Via", "")
        if via: via += ", "
        via += via_s
        headers["Via"] = via
