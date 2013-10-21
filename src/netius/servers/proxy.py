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

    def on_data_http(self, connection, parser):
        http.HTTPServer.on_data_http(self, connection, parser)

        def on_message(client, parser, message):
            status = parser.status
            version_s = parser.version_s
            headers = parser.headers

            print "on message"

            if "connection" in headers: del headers["connection"]

            buffer = []
            buffer.append("%s %s\r\n" % (version_s, status))
            for key, value in headers.items():
                buffer.append("%s: %s\r\n" % (key, value))
            buffer.append("\r\n")

            # joins the header strings list as the data string that contains
            # the headers and then sends the value through the connection
            data = "".join(buffer)
            connection.send(data)

            connection.send(message)

            client.close()

        method = parser.method.upper()  #@todo por equanto esta a ser ignorado
        path = parser.path_s

        http_client = netius.clients.HTTPClient()
        http_client.method(method, path, headers = parser.headers)
        http_client.bind("message", on_message)

if __name__ == "__main__":
    server = ProxyServer()
    server.serve(host = "0.0.0.0", port = 8080)
