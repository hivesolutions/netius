#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import re

import netius.common
import netius.servers

class ForwardProxyServer(netius.servers.ProxyServer):

    def __init__(self, config = "proxy.json", rules = {}, *args, **kwargs):
        netius.servers.ProxyServer.__init__(self, *args, **kwargs)
        self.load_config(path = config, rules = rules)
        self.compile()

    def on_headers(self, connection, parser):
        netius.servers.ProxyServer.on_headers(self, connection, parser)

        method = parser.method.upper()
        path = parser.path_s
        version_s = parser.version_s
        headers = parser.headers

        rejected = False
        for rule in self.rules.values():
            rejected = rule.match(path)
            if rejected: break

        if rejected:
            connection.send_response(
                data = "This connection is not allowed",
                headers = dict(
                    connection = "close"
                ),
                version = version_s,
                code = 403,
                code_s = "Forbidden",
                apply = True,
                callback = self._prx_close
            )
            return

        if method == "CONNECT":
            host, port = path.split(":")
            port = int(port)
            _connection = self.raw_client.connect(host, port)
            _connection.max_pending = self.max_pending
            _connection.min_pending = self.min_pending
            connection.tunnel_c = _connection
            self.conn_map[_connection] = connection
        else:
            proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
            proxy_c = proxy_c or None
            connection.proxy_c = None
            if proxy_c in self.conn_map: del self.conn_map[proxy_c]

            encoding = headers.get("transfer-encoding", None)
            is_chunked = encoding == "chunked"
            encoding = netius.common.CHUNKED_ENCODING if is_chunked else\
                netius.common.PLAIN_ENCODING

            _connection = self.http_client.method(
                method,
                path,
                headers = headers,
                encoding = encoding,
                encodings = None,
                safe = True,
                connection = proxy_c
            )

            self.debug("Setting connection as waiting, proxy connection loading ...")

            _connection.waiting = True
            _connection.max_pending = self.max_pending
            _connection.min_pending = self.min_pending
            connection.proxy_c = _connection
            self.conn_map[_connection] = connection

    def compile(self):
        for key, rule in self.rules.items():
            self.rules[key] = re.compile(rule)

if __name__ == "__main__":
    import logging
    rules = dict(
        facebook = ".*facebook.com.*"
    )
    server = ForwardProxyServer(
        rules = rules,
        level = logging.INFO
    )
    server.serve(env = True)
else:
    __path__ = []
