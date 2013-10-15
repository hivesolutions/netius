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

BASE_HEADERS = dict(
    Server = "netium-wsgi/0.0.1"
)
""" The map containing the complete set of headers
that are meant to be applied to all the responses """

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

        def close(data):
            self.on_connection_d(connection)

        def start_response(status, headers):
            return self._start_response(connection, status, headers)

        environ = dict(
            REQUEST_METHOD = parser.method.upper(),
            SCRIPT_NAME = "",
            PATH_INFO = parser.path_s,
            QUERY_STRING = "",
            CONTENT_TYPE = parser.headers.get("content-type", None),
            CONTENT_LENGTH = None if parser.content_l == -1 else parser.content_l,
        )
        for key, value in parser.headers.items():
            key = "HTTP_" + key.upper()
            environ[key] = value

        sequence = self.app(environ, start_response)
        for value in sequence: connection.send(value)

        # in case the connection is not meant to be kept alive must
        # send an empty string with the callback for the closing of
        # the connection (connection close handle)
        if not parser.keep_alive: connection.send("", callback = close)

    def _apply_base(self, headers):
        for key, value in BASE_HEADERS.items():
            if key in headers: continue
            headers[key] = value

    def _apply_parser(self, parser, headers):
        if parser.keep_alive: headers["Connection"] = "Keep-Alive"

    def _start_response(self, connection, status, headers):
        parser = connection.parser
        version_s = parser.version_s
        headers = dict(headers)

        self._apply_base(headers)
        self._apply_parser(parser, headers)

        buffer = []
        buffer.append("%s %s\r\n" % (version_s, status))
        for key, value in headers.items():
            buffer.append("%s: %s\r\n" % (key, value))
        buffer.append("\r\n")

        data = "".join(buffer)
        connection.send(data)

def application(environ, start_response):
    message = "Hello World"
    message_l = len(message)
    headers = [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(message_l))
    ]
    start_response("200 OK", headers)
    yield message

if __name__ == "__main__":
    server = WSGIServer(application)
    server.serve()
