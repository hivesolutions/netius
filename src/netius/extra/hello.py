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

import netius.servers

class HelloServer(netius.servers.HTTP2Server):
    """
    Simple Hello (World) HTTP server meant to be used for benchmarks
    and other operations that require a simple in-memory HTTP server.

    Most of the implementation on the server is done in the upper
    layers from which this server class inherits.

    Performance should always be considered critical when changing
    or adding new features to this server implementation.
    """

    def __init__(self, message = "Hello World", *args, **kwargs):
        netius.servers.HTTP2Server.__init__(self, *args, **kwargs)
        self.message = message

    def on_serve(self):
        netius.servers.HTTP2Server.on_serve(self)
        if self.env: self.message = self.get_env("MESSAGE", self.message, cast = str)
        self.info("Serving '%s' as welcome message ..." % self.message)

    def on_data_http(self, connection, parser):
        netius.servers.HTTP2Server.on_data_http(
            self, connection, parser
        )

        callback = self._hello_keep if parser.keep_alive else self._hello_close
        connection_s = "keep-alive" if parser.keep_alive else "close"
        headers = {
            "Connection" : connection_s,
            "Content-Type" : "text/plain"
        }

        connection.send_response(
            data = self.message,
            headers = headers,
            code = 200,
            code_s = "OK",
            apply = True,
            callback = callback
        )

    def _hello_close(self, connection):
        self.delay(connection.close)

    def _hello_keep(self, connection):
        pass

if __name__ == "__main__":
    import logging
    server = HelloServer(level = logging.INFO)
    server.serve(env = True)
else:
    __path__ = []
