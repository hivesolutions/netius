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
            connection.send_response(
                data = "No valid proxy endpoint found",
                version = version_s,
                code = 404,
                code_s = "Not Found",
                callback = self._prx_close
            )
            return

        _connection = self.http_client.method(
            method,
            url,
            headers = parser.headers,
            data = parser.get_message()
        )
        _connection.used = False
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
