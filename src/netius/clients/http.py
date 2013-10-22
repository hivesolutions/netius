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

BASE_HEADERS = {
    "user-agent" : "%s/%s" % (netius.NAME, netius.VERSION)
}
""" The map containing the complete set of headers
that are meant to be applied to all the requests """

class HTTPConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.HTTPParser(self, type = netius.common.RESPONSE)
        self.version = "HTTP/1.1"
        self.method = "GET"
        self.url = None
        self.ssl = False
        self.host = None
        self.port = None
        self.path = None
        self.headers = {}
        self.data = None

        self.parser.bind("on_data", self.on_data)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_chunk", self.on_chunk)

    def set_http(
        self,
        version = "HTTP/1.1",
        method = "GET",
        url = None,
        host = None,
        port = None,
        path = None,
        ssl = False,
        parsed = None
    ):
        self.method = method.upper()
        self.version = version
        self.url = url
        self.host = host
        self.port = port
        self.path = path
        self.ssl = ssl
        self.parsed = parsed

    def set_headers(self, headers):
        self.headers = headers

    def set_data(self, data):
        self.data = data

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self, self.parser)

    def on_headers(self):
        self.owner.on_headers_http(self, self.parser)

    def on_chunk(self, range):
        self.owner.on_chunk_http(self, self.parser, range)

class HTTPClient(netius.Client):
    """
    Simple test of an http client, supports a series of basic
    operations and makes use of the http parser from netius.
    """

    def get(self, url, headers = {}):
        return self.method("GET", url, headers = headers)

    def method(self, method, url, headers = {}, data = None, version = "HTTP/1.1"):
        parsed = urlparse.urlparse(url)
        ssl = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path

        connection = self.acquire_c(host, port, ssl = ssl)
        connection.set_http(
            version = version,
            method = method,
            url = url,
            host = host,
            port = port,
            path = path,
            ssl = ssl,
            parsed = parsed
        )
        connection.set_headers(headers)
        connection.set_data(data)
        return connection

    def on_connect(self, connection):
        netius.Client.on_connect(self, connection)
        self.trigger("connect", self, connection)

    def on_acquire(self, connection):
        netius.Client.on_acquire(self, connection)
        self.trigger("acquire", self, connection)
        self._send_request(connection)

    def on_data(self, connection, data):
        netius.Client.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.Client.on_connection_d(self, connection)
        self.trigger("close", self, connection)
        self.remove_c(connection)

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(self, socket, address, ssl = ssl)

    def on_data_http(self, connection, parser):
        message = parser.get_message()
        self.trigger("message", self, parser, message)
        self.release_c(connection)

    def on_headers_http(self, connection, parser):
        headers = parser.headers
        self.trigger("headers", self, parser, headers)

    def on_chunk_http(self, connection, parser, range):
        self.trigger("chunk", self, parser, range)

    def _send_request(self, connection):
        method = connection.method
        path = connection.path
        version = connection.version
        headers = connection.headers
        data = connection.data
        parsed = connection.parsed

        if parsed.query: path += "?" + parsed.query

        self._apply_base(headers)
        self._apply_dynamic(headers, connection)

        buffer = []
        buffer.append("%s %s %s\r\n" % (method, path, version))
        for key, value in headers.items():
            key = netius.common.header_up(key)
            buffer.append("%s: %s\r\n" % (key, value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        connection.send(buffer_data)
        data and connection.send(data)

    def _apply_base(self, headers):
        for key, value in BASE_HEADERS.items():
            if key in headers: continue
            headers[key] = value

    def _apply_dynamic(self, headers, connection):
        host = connection.host
        port = connection.port
        data = connection.data

        if port == 80: host_s = host
        else: host_s = "%s:%d" % (host, port)

        if not "connection" in headers:
            headers["connection"] = "keep-alive"
        if not "content-length" in headers:
            headers["content-length"] = len(data) if data else 0
        if not "host" in headers:
            headers["host"] = host_s

if __name__ == "__main__":
    def on_message(client, parser, message):
        message = message or "[empty message]"
        print parser.code_s + " " + parser.status_s
        print message; client.close()

    http_client = HTTPClient()
    http_client.get("http://www.flickr.com/")
    http_client.bind("message", on_message)
