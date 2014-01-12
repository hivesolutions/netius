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

import sys

import netius

import http

class WSGIServer(http.HTTPServer):
    """
    Base class for the creation of a wsgi compliant server
    the server should be initialized with the "target" app
    object as reference and a mount point.
    """

    def __init__(self, app, mount = "", *args, **kwargs):
        http.HTTPServer.__init__(self, *args, **kwargs)
        self.app = app
        self.mount = mount
        self.mount_l = len(mount)

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)

        # clojure method to be used to close the current connection in
        # case that's required by the current connection headers, the
        # closing of the connection is delayed so that no invalid file
        # descriptor problem occurs for the connections in operation
        def close(connection):
            self.delay(connection.close)

        # method created as a clojure that handles the starting of
        # response as defined in the wsgi standards
        def start_response(status, headers):
            return self._start_response(connection, status, headers)

        # retrieves the path for the current request and then retrieves
        # the query string part for it also, after that computes the
        # path info value as the substring of the path without the mount
        path = parser.get_path()
        query = parser.get_query()
        path_info = path[self.mount_l:]

        # initializes the environment map (structure) with all the cgi based
        # variables that should enable the application to handle the request
        # and respond to it in accordance
        environ = dict(
            REQUEST_METHOD = parser.method.upper(),
            SCRIPT_NAME = self.mount,
            PATH_INFO = path_info,
            QUERY_STRING = query,
            CONTENT_TYPE = parser.headers.get("content-type", ""),
            CONTENT_LENGTH = "" if parser.content_l == -1 else parser.content_l,
            SERVER_NAME = self.host,
            SERVER_PORT = self.port,
            SERVER_PROTOCOL = parser.version_s
        )

        # updates the environment map with all the structures referring
        # to the wsgi specifications note that the message is retrieved
        # as a buffer to be able to handle the file specific operations
        environ["wsgi.version"] = (1, 0)
        environ["wsgi.url_scheme"] = "https" if connection.ssl else "http"
        environ["wsgi.input"] = parser.get_message_b()
        environ["wsgi.errors"] = sys.stderr
        environ["wsgi.multithread"] = True
        environ["wsgi.multiprocess"] = True
        environ["wsgi.run_once"] = False
        environ["wsgi.server_name"] = netius.NAME
        environ["wsgi.server_version"] = netius.VERSION

        # iterates over all the header values that have been received
        # to set them in the environment map to be used by the wsgi
        # infra-structure, not that their name is capitalized as defined
        # in the standard specification
        for key, value in parser.headers.iteritems():
            key = "HTTP_" + key.replace("-", "_").upper()
            environ[key] = value

        # runs the app logic with the provided environment map and start
        # response clojure and then iterates over the complete set of values
        # in the returned iterator to send the messages to the other end
        sequence = self.app(environ, start_response)
        for value in sequence: connection.send(value)

        # in case the connection is not meant to be kept alive must
        # must set the callback of the flush operation to the close
        # function so that the connection is closed
        if parser.keep_alive: callback = None
        else: callback = close

        # runs the flush operation in the connection setting the proper
        # callback method for it so that the connection state is defined
        # in the proper way (closed or kept untouched)
        connection.flush(callback = callback)

    def _start_response(self, connection, status, headers):
        # retrieves the parser object from the connection and uses
        # it to retrieve the string version of the http version
        parser = connection.parser
        version_s = parser.version_s

        # adds an extra space to the status line and then
        # splits it into the status message and the code
        status_c, _status_m = (status + " ").split(" ", 1)
        status_c = int(status_c)

        # converts the provided list of header tuples into a key
        # values based map so that it may be used more easily
        headers = dict(headers)

        # tries to retrieve the content length value from the headers
        # in case they exist and if the value of them is zero the plain
        # encoding is set in order to avoid extra problems while using
        # chunked encoding with zero length based messages
        length = headers.get("Content-Length", -1)
        length = 0 if status_c in (204, 304,) else length
        if length == 0: connection.set_encoding(http.PLAIN_ENCODING)

        # verifies if the current connection is using a chunked based
        # stream as this will affect some of the decisions that are
        # going to be taken as part of response header creation
        is_chunked = connection.is_chunked()

        # checks if the provided headers map contains the definition
        # of the content length in case it does not unsets the keep
        # alive setting in the parser because the keep alive setting
        # requires the content length to be defined or the target
        # encoding type to be chunked
        has_length = not length == -1
        if not has_length: parser.keep_alive = is_chunked

        # applies the base (static) headers to the headers map and then
        # applies the parser based values to the headers map, these
        # values should be dynamic and based in the current state
        # finally applies the connection related headers to the current
        # map of headers so that the proper values are filtered and added
        self._apply_base(headers)
        self._apply_parser(parser, headers)
        self._apply_connection(connection, headers)

        # creates the list that will hold the various header string and
        # that is going to be used as buffer and then generates the various
        # lines for the headers and sets them in the buffer list
        buffer = []
        buffer.append("%s %s\r\n" % (version_s, status))
        for key, value in headers.iteritems():
            buffer.append("%s: %s\r\n" % (key, value))
        buffer.append("\r\n")

        # joins the header strings list as the data string that contains
        # the headers and then sends the value through the connection
        data = "".join(buffer)
        connection.send_plain(data)

if __name__ == "__main__":
    import logging

    def app(environ, start_response):
        status = "200 OK"
        contents = "Hello World"
        content_l = len(contents)
        headers = (
            ("Content-Length", content_l),
            ("Content-type", "text/plain"),
            ("Connection", "keep-alive")
        )
        start_response(status, headers)
        return (contents,)

    server = WSGIServer(app = app, level = logging.INFO)
    server.serve(env = True)
