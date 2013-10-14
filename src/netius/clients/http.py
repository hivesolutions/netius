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

import urlparse

import netius.common

class HTTPConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.HTTPParser(type = netius.common.RESPONSE)
        self.version = "HTTP/1.0"
        self.method = "GET"
        self.url = None
        self.ssl = False
        self.host = None
        self.port = None
        self.path = None

        self.parser.bind("on_data", self.on_data)

    def set_http(
        self,
        version = "HTTP/1.0",
        method = "GET",
        url = None,
        host = None,
        port = None,
        path = None,
        ssl = False
    ):
        self.method = method.upper()
        self.version = version
        self.url = url
        self.host = host
        self.port = port
        self.path = path
        self.ssl = ssl

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self.parser)

class HTTPClient(netius.Client):
    """
    Simple test of an http client, supports a series of basic
    operations and makes use of the http parser from netius.
    """

    def get(self, url):
        parsed = urlparse.urlparse(url)
        ssl = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path

        connection = self.connect(host, port, ssl = ssl)
        connection.set_http(
            version = "HTTP/1.0",
            method = "GET",
            url = url,
            host = host,
            port = port,
            path = path,
            ssl = ssl
        )

    def on_connect(self, connection):
        netius.Client.on_connect(self, connection)

        method = connection.method
        path = connection.path
        version = connection.version

        connection.send("%s %s %s\r\n\r\n" % (method, path, version))

    def on_data(self, connection, data):
        netius.Client.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.Client.on_connection_d(self, connection)

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(self, socket, address, ssl = ssl)

    def on_data_http(self, parser):
        print parser.get_message()

if __name__ == "__main__":
    http_client = HTTPClient()
    http_client.get("https://localhost:9090/")
    http_client.start()
