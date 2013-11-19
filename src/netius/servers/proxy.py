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

import re

import http

import netius.common
import netius.clients

class ProxyServer(http.HTTPServer):

    def __init__(self, rules = {}, *args, **kwargs):
        http.HTTPServer.__init__(self, *args, **kwargs)
        self.rules = rules
        self.conn_map = {}

        self.http_client = netius.clients.HTTPClient(
            thread = False,
            *args,
            **kwargs
        )
        self.http_client.bind("headers", self._on_prx_headers)
        self.http_client.bind("message", self._on_prx_message)
        self.http_client.bind("partial", self._on_prx_partial)
        self.http_client.bind("chunk", self._on_prx_chunk)
        self.http_client.bind("acquire", self._on_prx_acquire)
        self.http_client.bind("close", self._on_prx_close)
        self.http_client.bind("error", self._on_prx_error)

        self.raw_client = netius.clients.RawClient(
            thread = False,
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

        self.compile()

    def start(self):
        self.http_client.load()
        self.raw_client.load()
        self.container.start()

    def stop(self):
        self.container.stop()

    def compile(self):
        for key, rule in self.rules.iteritems():
            self.rules[key] = re.compile(rule)

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.send(data)
        else: connection.parse(data)

    def on_connection_d(self, connection):
        http.HTTPServer.on_connection_d(self, connection)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.close()
        if hasattr(connection, "proxy_c"): connection.proxy_c.close()

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)

        method = parser.method.upper()
        path = parser.path_s
        version_s = parser.version_s

        rejected = False
        for rule in self.rules.itervalues():
            rejected = rule.match(path)
            if rejected: break

        if rejected:
            connection.send_response(
                data = "This connection is not allowed",
                version = version_s,
                code = 403,
                code_s = "Forbidden",
                callback = self._prx_close
            )
            return

        if method == "CONNECT":
            host, port = path.split(":")
            port = int(port)
            _connection = self.raw_client.connect(host, port)
            connection.tunnel_c = _connection
            self.conn_map[_connection] = connection
        else:
            _connection = self.http_client.method(
                method,
                path,
                headers = parser.headers
            )
            _connection.used = False
            connection.proxy_c = _connection
            self.conn_map[_connection] = connection

    def _prx_close(self, connection):
        connection.close()

    def _prx_keep(self, connection):
        pass

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
        _connection = parser.owner
        is_chunked = parser.chunked

        _connection.used = False

        if not is_chunked: return

        connection = self.conn_map[_connection]
        connection.send("0\r\n\r\n", callback = self._prx_keep)

    def _on_prx_partial(self, client, parser, data):
        _connection = parser.owner
        is_chunked = parser.chunked

        if is_chunked: return

        connection = self.conn_map[_connection]
        connection.send(data)

    def _on_prx_chunk(self, client, parser, range):
        _connection = parser.owner
        connection = self.conn_map[_connection]

        start, end = range
        data = parser.message[start:end]
        data_s = "".join(data)
        data_l = len(data_s)
        header = "%x\r\n" % data_l
        chunk = header + data_s + "\r\n"
        connection.send(chunk)

    def _on_prx_acquire(self, client, _connection):
        _connection.used = True

    def _on_prx_close(self, client, _connection):
        connection = self.conn_map[_connection]
        if _connection.used: connection.close(flush = True)
        del self.conn_map[_connection]

    def _on_prx_error(self, client, _connection, error):
        error_m = str(error) or "Unknown proxy relay error"
        connection = self.conn_map[_connection]
        connection.send_response(
            data = error_m,
            code = 500,
            code_s = "Internal Error",
            callback = self._prx_close
        )

    def _on_raw_connect(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.send_response(
            code = 200,
            code_s = "Connection established"
        )

    def _on_raw_data(self, client, _connection, data):
        connection = self.conn_map[_connection]
        connection.send(data)

    def _on_raw_close(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.close(flush = True)
        del self.conn_map[_connection]

if __name__ == "__main__":
    import logging
    rules = dict(
        facebook = ".*facebook.com.*"
    )
    server = ProxyServer(rules = rules, level = logging.INFO)
    server.serve(env = True)
