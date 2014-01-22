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

import urllib
import urlparse

import netius.common

BASE_HEADERS = {
    "user-agent" : "%s/%s" % (netius.NAME, netius.VERSION)
}
""" The map containing the complete set of headers
that are meant to be applied to all the requests """

class HTTPConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
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
        self.parser.bind("on_partial", self.on_partial)
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

    def send_request(self):
        method = self.method
        path = self.path
        version = self.version
        headers = self.headers
        data = self.data
        parsed = self.parsed

        if parsed.query: path += "?" + parsed.query

        headers = dict(headers)
        self._apply_base(headers)
        self._apply_dynamic(headers)

        buffer = []
        buffer.append("%s %s %s\r\n" % (method, path, version))
        for key, value in headers.iteritems():
            key = netius.common.header_up(key)
            buffer.append("%s: %s\r\n" % (key, value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        self.send(buffer_data)
        data and self.send(data)

    def set_headers(self, headers):
        self.headers = headers

    def set_data(self, data):
        self.data = data

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self, self.parser)
        self.parser.clear()

    def on_partial(self, data):
        self.owner.on_partial_http(self, self.parser, data)

    def on_headers(self):
        self.owner.on_headers_http(self, self.parser)

    def on_chunk(self, range):
        self.owner.on_chunk_http(self, self.parser, range)

    def _apply_base(self, headers):
        for key, value in BASE_HEADERS.iteritems():
            if key in headers: continue
            headers[key] = value

    def _apply_dynamic(self, headers):
        host = self.host
        port = self.port
        data = self.data

        if port == 80: host_s = host
        else: host_s = "%s:%d" % (host, port)

        if not "connection" in headers:
            headers["connection"] = "keep-alive"
        if not "content-length" in headers:
            headers["content-length"] = len(data) if data else 0
        if not "host" in headers:
            headers["host"] = host_s

class HTTPClient(netius.StreamClient):
    """
    Simple test of an http client, supports a series of basic
    operations and makes use of the http parser from netius.

    The current implementation supports the auto-release of the
    connection once the message has been received, this is optional
    and may be disabled with an argument in the constructor.
    """

    def __init__(self, auto_release = True, auto_close = False, *args, **kwargs):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.auto_release = auto_release
        self.auto_close = auto_close

    @classmethod
    def get_s(
        cls,
        url,
        params = {},
        headers = {},
        **kwargs
    ):
        return cls.method_s(
            "GET",
            url,
            params = params,
            headers = headers,
            **kwargs
        )

    @classmethod
    def post_s(
        cls,
        url,
        params = {},
        headers = {},
        data = None,
        **kwargs
    ):
        return cls.method_s(
            "POST",
            url,
            params = params,
            headers = headers,
            data = data,
            **kwargs
        )

    @classmethod
    def put_s(
        cls,
        url,
        params = {},
        headers = {},
        data = None,
        **kwargs
    ):
        return cls.method_s(
            "PUT",
            url,
            params = params,
            headers = headers,
            data = data,
            **kwargs
        )

    @classmethod
    def delete_s(
        cls,
        url,
        params = {},
        headers = {},
        **kwargs
    ):
        return cls.method_s(
            "DELETE",
            url,
            params = params,
            headers = headers,
            **kwargs
        )


    @classmethod
    def method_s(
        cls,
        method,
        url,
        params = {},
        headers = {},
        data = None,
        version = "HTTP/1.1",
        connection = None,
        async = True,
        daemon = True,
        callback = None,
        on_headers = None,
        on_data = None
    ):
        http_client = async and cls.get_client_s(
            thread = True,
            daemon = daemon
        ) or HTTPClient(
            thread = False,
            auto_close = True
        )

        http_client.method(
            method,
            url,
            params = params,
            headers = headers,
            data = data,
            version = version,
            connection = connection
        )

        # in case the result in asynchronous no result should be
        # provided as the data should be retrieved by callback but
        # in case the current request is synchronous the proper result
        # object must be constructed and populated
        if async: result = None
        else:
            buffer = []
            result = dict(
                code = None,
                data = None
            )

        # in case the current request to be made in synchronous
        # and the on data and the message callbacks are not
        # defined must create the proper functions for the building
        # of the final result object (contains contents)
        if not async and not on_data and not callback:
            def on_partial(client, parser, data):
                buffer.append(data)

            def on_message(client, parser, message):
                result["code"] = parser.code
                result["status"] = parser.status
                result["data"] = "".join(buffer)

            on_data = on_partial
            callback = on_message

        if on_headers: http_client.bind("headers", on_headers)
        if on_data: http_client.bind("partial", on_data)
        if callback: http_client.bind("message", callback)

        not async and http_client.start()
        return result

    def get(
        self,
        url,
        params = {},
        headers = {},
        **kwargs
    ):
        return self.method(
            "GET",
            url,
            params = params,
            headers = headers,
            **kwargs
        )

    def post(
        self,
        url,
        params = {},
        headers = {},
        data = None,
        **kwargs
    ):
        return self.method(
            "POST",
            url,
            params = params,
            headers = headers,
            data = data,
            **kwargs
        )

    def put(
        self,
        url,
        params = {},
        headers = {},
        data = None,
        **kwargs
    ):
        return self.method(
            "PUT",
            url,
            params = params,
            headers = headers,
            data = data,
            **kwargs
        )

    def delete(
        self,
        url,
        params = {},
        headers = {},
        **kwargs
    ):
        return self.method(
            "DELETE",
            url,
            params = params,
            headers = headers,
            **kwargs
        )

    def method(
        self,
        method,
        url,
        params = {},
        headers = {},
        data = None,
        version = "HTTP/1.1",
        connection = None
    ):
        # creates the message that is going to be used in the logging of
        # the current method request for debugging purposes, this may be
        # useful for a full record traceability of the request
        message = "%s %s %s" % (method, url, version)
        self.debug(message)

        # encodes the provided parameters into the query string and then
        # adds these parameters to the end of the provided url, these
        # values are commonly named get parameters
        query = urllib.urlencode(params)
        if query: url = url + "?" + query

        # parses the provided url and retrieves the various parts of the
        # url that are going to be used in the creation of the connection
        # takes into account some default values in case their are not part
        # of the provided url (eg: port and the scheme)
        parsed = urlparse.urlparse(url)
        ssl = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path

        # in case there's a connection to be used must validate that the
        # connection is valid for the current context so that the host,
        # the port and the security of the connection is the same, in case
        # the connection is not valid closes it and sets it as unset
        if connection:
            address_valid = connection.address == (host, port)
            ssl_valid = connection.ssl == ssl
            is_valid = address_valid and ssl_valid
            if not is_valid: connection.close(); connection = None

        # in case there's going to be a re-usage of an already existing
        # connection the acquire operation must be performed so that it
        # becomes unblocked from the previous context (required for usage)
        connection and self.acquire(connection)

        # tries to retrieve the connection that is going to be used for
        # the performing of the request by either acquiring a connection
        # from the list of available connection or re-using the connection
        # that was passed to the method (and previously acquired)
        connection = connection or self.acquire_c(host, port, ssl = ssl)
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
        netius.StreamClient.on_connect(self, connection)
        self.trigger("connect", self, connection)

    def on_acquire(self, connection):
        netius.StreamClient.on_acquire(self, connection)
        self.trigger("acquire", self, connection)
        connection.send_request()

    def on_release(self, connection):
        netius.StreamClient.on_release(self, connection)
        self.trigger("release", self, connection)
        connection.parser.clear()

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.StreamClient.on_connection_d(self, connection)
        self.trigger("close", self, connection)
        self.remove_c(connection)

        # verifies if the current client was created with
        # the auto close flag and there are not more connections
        # left open if that's the case closes the current
        # client so that no more interaction exists as it's
        # no longer required (as defined by the specification)
        if not self.auto_close: return
        if self.connections: return
        self.close()

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def on_data_http(self, connection, parser):
        message = parser.get_message()
        self.trigger("message", self, parser, message)
        if self.auto_release: self.release_c(connection)
        if self.auto_close: self.close()

    def on_partial_http(self, connection, parser, data):
        self.trigger("partial", self, parser, data)

    def on_headers_http(self, connection, parser):
        headers = parser.headers
        self.trigger("headers", self, parser, headers)

    def on_chunk_http(self, connection, parser, range):
        self.trigger("chunk", self, parser, range)

if __name__ == "__main__":
    def on_headers(client, parser, headers):
        print parser.code_s + " " + parser.status_s

    def on_partial(client, parser, data):
        data = data or "[empty message]"
        print data

    def on_message(client, parser, message):
        client.close()

    def on_close(client, connection):
        client.close()

    http_client = HTTPClient()
    http_client.get("http://www.flickr.com/")
    http_client.bind("headers", on_headers)
    http_client.bind("partial", on_partial)
    http_client.bind("message", on_message)
    http_client.bind("close", on_close)
