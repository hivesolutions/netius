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

class WSGIServer(http.HTTPServer):

    def __init__(self, app, name = None, handler = None, *args, **kwargs):
        http.HTTPServer.__init__(
            self,
            name = name,
            handler = handler,
            *args,
            **kwargs
        )
        self.app = app

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)

        def start_response(status, headers):
            return self._start_response(connection, status, headers)

        environ = dict(
            REQUEST_METHOD = parser.method.upper(),
            SCRIPT_NAME = "",
            PATH_INFO = parser.path_s,
            QUERY_STRING = "",
            CONTENT_TYPE = parser.headers.get("content-type", None),
            CONTENT_LENGTH =  None if parser.content_l == -1 else parser.content_l,
        )
        for key, value in parser.headers.items():
            key = "HTTP_" + key.upper()
            environ[key] = value

        sequence = self.app(environ, start_response)
        for value in sequence: connection.send(value)

    def _start_response(self, connection, status, headers):
        connection.send("HTTP/1.1 %s\r\n" % status)
        for key, value in headers:
            connection.send("%s: %s\r\n" % (key, value))
        connection.send("\r\n")

def application(environ, start_response):
    headers = [
        ("Content-Type", "text/plain"),
        ("Content-Length", "12")
    ]
    start_response("200 OK", headers)
    yield "Hello World\n"

if __name__ == "__main__":
    server = WSGIServer(application)
    server.serve()
