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

class ProxyServer(http.HTTPServer):

    def __init__(self, rules = {}, name = None, handler = None, *args, **kwargs):
        http.HTTPServer.__init__(
            self,
            name = name,
            handler = handler,
            *args,
            **kwargs
        )
        self.rules = rules
        self.clients = []
        self.conn_map = {}

        self.http_client = netius.clients.HTTPClient()
        self.http_client.bind("headers", self._on_prx_headers)
        self.http_client.bind("message", self._on_prx_message)
        self.http_client.bind("chunk", self._on_prx_chunk)
        self.http_client.bind("close", self._on_prx_close)

    def on_data(self, connection, data):
        netius.Server.on_data(self, connection, data)

        if hasattr(connection, "tunnel"): connection.tunnel_c.send(data)
        else: connection.parse(data)

    def on_connection_d(self, connection):
        netius.Server.on_connection_d(self, connection)
        if hasattr(connection, "tunnel"): connection.tunnel.close()

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)

        method = parser.method.upper()
        path = parser.path_s
        version_s = parser.version_s

        import re
        rule = re.compile(".*facebook.com.*")
        rejected = rule.match(path)

        if rejected:
            connection.send(
                "%s 403 Forbidden\r\n\r\nThis connection is not allowed" % version_s,
                callback = self._prx_close
            )
            return

        if method == "CONNECT":
            def on_connect(client, _connection):
                connection.tunnel_c = _connection
                connection.send("%s 200 Connection established\r\n\r\n" % version_s)

            def on_data(client, _connection, data):
                connection.send(data)

            def on_close(client, _connection):
                connection.close()

            def on_stop(client):
                if client in self.clients: self.clients.remove(client)

            host, port = path.split(":")
            port = int(port)
            client = netius.clients.RawClient()
            client.connect(host, port)
            client.bind("connect", on_connect)
            client.bind("data", on_data)
            client.bind("close", on_close)
            client.bind("stop", on_stop)
            connection.tunnel = client
            self.clients.append(client)
        else:
            _connection = self.http_client.method(method, path, headers = parser.headers)
            self.conn_map[_connection] = connection

    def _prx_close(self, connection):
        connection.close()

    def _prx_keep(self, connection):
        pass

    def _on_prx_headers(self, client, parser, headers):
        _connection = parser.owner
        code_s = parser.code_s
        status_s = parser.status_s
        version_s = parser.version_s

        connection = self.conn_map[_connection]

        buffer = []
        buffer.append("%s %s %s\r\n" % (version_s, code_s, status_s))
        for key, value in headers.items():
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

        connection = self.conn_map[_connection]

        if is_chunked: connection.send("0\r\n\r\n", callback = self._prx_keep)
        else: connection.send(message, callback = self._prx_keep)

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

    def _on_prx_close(self, client, _connection):
        pass
        #connection = self.conn_map[_connection]
        #connection.close()

if __name__ == "__main__":
    server = ProxyServer()
    server.serve(host = "0.0.0.0", port = 8080)
