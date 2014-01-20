#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import http

import netius.common
import netius.clients

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

class ProxyServer(http.HTTPServer):

    def __init__(self, throttle = True, max_pending = MAX_PENDING, *args, **kwargs):
        http.HTTPServer.__init__(
            self,
            receive_buffer_c = int(max_pending * BUFFER_RATIO),
            send_buffer_c = int(max_pending * BUFFER_RATIO),
            *args,
            **kwargs
        )
        self.throttle = throttle
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
        # loads both of the clients so that the internal structures
        # are initialized and ready to create remote connection
        self.http_client.load()
        self.raw_client.load()

        # starts the container this should trigger the start of the
        # event loop in the container and the proper listening of all
        # the connections in the current environment
        self.container.start(self)

    def stop(self):
        self.container.stop()

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
        if self.throttle: self.info("Throttling connections in the proxy ...")
        else: self.info("Not throttling connections in the proxy ...")

    def _throttle(self, _connection):
        if _connection.pending_s > self.min_pending: return
        connection = self.conn_map[_connection]
        if not connection.renable == False: return
        connection.enable_read()
        self.reads((connection.socket,), state = False)

    def _prx_close(self, connection):
        connection.close()

    def _prx_keep(self, connection):
        pass

    def _prx_throttle(self, connection):
        if connection.pending_s > self.min_pending: return

        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        if not proxy_c: return
        if not proxy_c.renable == False: return

        proxy_c.enable_read()
        self.raw_client.reads((proxy_c.socket,), state = False)

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

        # resolves the client connection into the proper proxy connection
        # to be used to send the headers (and status line) to the client
        connection = self.conn_map[_connection]

        # creates a buffer list that will hold the complete set of
        # lines that compose both the status lines and the headers
        # then appends the start line and the various header lines
        # to it so that it contains all of them
        buffer = []
        buffer.append("%s %s %s\r\n" % (version_s, code_s, status_s))
        for key, value in headers.iteritems():
            key = netius.common.header_up(key)
            buffer.append("%s: %s\r\n" % (key, value))
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
        # corresponding back-end connection (as define in specification)
        def close(connection): connection.close()

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
        data_s = "".join(data)
        data_l = len(data_s)
        header = "%x\r\n" % data_l
        chunk = header + data_s + "\r\n"

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
        error_m = str(error) or "Unknown proxy relay error"
        connection = self.conn_map.get(_connection, None)
        if not connection: return

        if not _connection.waiting: return

        connection.send_response(
            data = error_m,
            headers = dict(
                connection = "close"
            ),
            code = 500,
            code_s = "Internal Error",
            apply = True,
            callback = self._prx_close
        )

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
