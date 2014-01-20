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

import netius.servers

class ReverseProxyServer(netius.servers.ProxyServer):

    def __init__(self, config = "proxy.json", hosts = {}, *args, **kwargs):
        netius.servers.ProxyServer.__init__(self, *args, **kwargs)
        self.load_config(path = config, hosts = hosts)

    def on_data_http(self, connection, parser):
        netius.servers.ProxyServer.on_data_http(self, connection, parser)

        prefix = None
        method = parser.method.upper()
        path = parser.path_s
        headers = parser.headers
        version_s = parser.version_s

        host = headers.get("host", None)
        for _host, _prefix in self.hosts.iteritems():
            if not _host == host: continue
            prefix = _prefix
            url = prefix + path
            break

        if not prefix:
            self.debug("No valid proxy endpoint found for '%s'" % host)
            connection.send_response(
                data = "No valid proxy endpoint found",
                headers = dict(
                    connection = "close"
                ),
                version = version_s,
                code = 404,
                code_s = "Not Found",
                apply = True,
                callback = self._prx_close
            )
            return

        # verifies if the current connection contains already contains
        # a proxy connection if that's the case that must be unset from the
        # connection and from the connection map internal structures at
        # least until the http client returns from the method call
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        proxy_c = proxy_c or None
        connection.proxy_c = None
        if proxy_c in self.conn_map: del self.conn_map[proxy_c]

        # calls the proper (http) method in the client this should acquire
        # a new connection and starts the process of sending the request
        # to the associated http server (request handling)
        _connection = self.http_client.method(
            method,
            url,
            headers = parser.headers,
            data = parser.get_message(),
            version = version_s,
            connection = proxy_c
        )

        # prints a debug message about the connection becoming a waiting
        # connection meaning that the connection with the client host has
        # not been yet established (no data has been  received)
        self.debug("Setting connection as waiting, proxy connection loading ...")

        # sets the current http back-end client connection as waiting and then
        # maps it as the proxy connection in the connection and also creates
        # the reverse mapping using the connection map of the current server
        _connection.waiting = True
        connection.proxy_c = _connection
        self.conn_map[_connection] = connection

if __name__ == "__main__":
    import logging
    hosts = {
        "host.com" : "http://localhost"
    }
    server = ReverseProxyServer(
        hosts = hosts,
        level = logging.INFO
    )
    server.serve(env = True)
