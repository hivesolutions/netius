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

import zlib
import base64

import netius.common

BASE_HEADERS = {
    "user-agent" : netius.IDENTIFIER
}
""" The map containing the complete set of headers
that are meant to be applied to all the requests """

class HTTPConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.version = "HTTP/1.1"
        self.method = "GET"
        self.encodings = "gzip, deflate"
        self.url = None
        self.ssl = False
        self.parsed = False
        self.host = None
        self.port = None
        self.path = None
        self.headers = {}
        self.data = None

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.HTTPParser(self, type = netius.common.RESPONSE)
        self.parser.bind("on_data", self.on_data)
        self.parser.bind("on_partial", self.on_partial)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_chunk", self.on_chunk)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()

    def info_dict(self, full = False):
        info = netius.Connection.info_dict(self, full = full)
        info.update(
            version = self.version,
            method = self.method,
            encoding = self.encodings,
            url = self.url,
            parsed = self.parsed,
            host = self.host,
            port = self.port,
            path = self.path,
            headers = self.headers
        )
        if full: info.update(
            parser = self.parser.info_dict()
        )
        return info

    def set_http(
        self,
        version = "HTTP/1.1",
        method = "GET",
        url = None,
        base = None,
        host = None,
        port = None,
        path = None,
        ssl = False,
        parsed = None
    ):
        self.version = version
        self.method = method.upper()
        self.url = url
        self.base = base
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
        for key, value in headers.items():
            key = netius.common.header_up(key)
            if not type(value) == list: value = (value,)
            for _value in value: buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        self.send(buffer_data, force = True)
        data and self.send(data, force = True)

    def set_encodings(self, encodings):
        self.encodings = encodings

    def set_headers(self, headers, normalize = True):
        self.headers = headers
        if normalize: self.normalize_headers()

    def set_data(self, data):
        self.data = data

    def normalize_headers(self):
        for key, value in netius.legacy.eager(self.headers.items()):
            del self.headers[key]
            key = netius.common.header_down(key)
            self.headers[key] = value

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        message = self.parser.get_message()
        self.trigger("message", self, self.parser, message)
        self.owner.on_data_http(self, self.parser)
        self.parser.clear()

    def on_partial(self, data):
        self.trigger("partial", self, self.parser, data)
        self.owner.on_partial_http(self, self.parser, data)

    def on_headers(self):
        self.trigger("headers", self, self.parser)
        self.owner.on_headers_http(self, self.parser)

    def on_chunk(self, range):
        self.trigger("chunk", self, self.parser, range)
        self.owner.on_chunk_http(self, self.parser, range)

    def _apply_base(self, headers, replace = False):
        for key, value in BASE_HEADERS.items():
            if not replace and key in headers: continue
            headers[key] = value

    def _apply_dynamic(self, headers):
        host = self.host
        port = self.port
        data = self.data

        if port in (80, 443): host_s = host
        else: host_s = "%s:%d" % (host, port)

        if not "connection" in headers:
            headers["connection"] = "keep-alive"
        if not "content-length" in headers:
            headers["content-length"] = len(data) if data else 0
        if not "host" in headers:
            headers["host"] = host_s
        if not "accept-encoding" in headers and self.encodings:
            headers["accept-encoding"] = self.encodings

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
        on_data = None,
        on_result = None,
        **kwargs
    ):
        http_client = cls.get_client_s(
            thread = True,
            daemon = daemon,
            **kwargs
        ) if async else HTTPClient(
            thread = False,
            auto_close = True,
            **kwargs
        )

        return http_client.method(
            method,
            url,
            params = params,
            headers = headers,
            data = data,
            version = version,
            connection = connection,
            async = async,
            callback = callback,
            on_headers = on_headers,
            on_data = on_data,
            on_result = on_result
        )

    @classmethod
    def to_response(cls, map):
        return netius.common.HTTPResponse(**map)

    @classmethod
    def decode_gzip(cls, data):
        if not data: return data
        return zlib.decompress(data, zlib.MAX_WBITS | 16)

    @classmethod
    def decode_deflate(cls, data):
        if not data: return data
        try: return zlib.decompress(data)
        except: return zlib.decompress(data, -zlib.MAX_WBITS)

    @classmethod
    def set_request(cls, parser, buffer, request = None):
        if request == None: request = dict()
        headers = parser.get_headers()
        data = b"".join(buffer)
        encoding = headers.get("Content-Encoding", None)
        decoder = getattr(cls, "decode_%s" % encoding) if encoding else None
        if decoder and data: data = decoder(data)
        request["code"] = parser.code
        request["status"] = parser.status
        request["headers"] = headers
        request["data"] = data
        return request

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
        params = None,
        headers = None,
        data = None,
        version = "HTTP/1.1",
        encodings = "gzip, deflate",
        connection = None,
        async = True,
        callback = None,
        on_headers = None,
        on_data = None,
        on_result = None
    ):
        # extracts the reference to the upper class element associated
        # with the current instance, to be used for operations
        cls = self.__class__

        # runs the defaulting operation on the provided parameters so that
        # new instances are created for both occasions as expected, this
        # avoids the typical problem with re-usage of default attributes
        params = params or dict()
        headers = headers or dict()

        # creates the message that is going to be used in the logging of
        # the current method request for debugging purposes, this may be
        # useful for a full record traceability of the request
        message = "%s %s %s" % (method, url, version)
        self.debug(message)

        # stores the initial version of the url in a fallback variable so
        # that it may latter be used for the storage of that information
        # in the associated connection (used in callbacks)
        base = url

        # encodes the provided parameters into the query string and then
        # adds these parameters to the end of the provided url, these
        # values are commonly named get parameters
        query = netius.legacy.urlencode(params)
        if query: url = url + "?" + query

        # parses the provided url and retrieves the various parts of the
        # url that are going to be used in the creation of the connection
        # takes into account some default values in case their are not part
        # of the provided url (eg: port and the scheme)
        parsed = netius.legacy.urlparse(url)
        ssl = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path or "/"
        username = parsed.username
        password = parsed.password

        # in case both the username and the password values are defined the
        # authorization header must be created and added to the default set
        # of headers that are going to be included in the request
        if username and password:
            payload = "%s:%s" % (username, password)
            payload = netius.legacy.bytes(payload)
            authorization = base64.b64encode(payload)
            authorization = netius.legacy.str(authorization)
            headers["authorization"] = "Basic %s" % authorization

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
            base = base,
            host = host,
            port = port,
            path = path,
            ssl = ssl,
            parsed = parsed
        )
        connection.set_encodings(encodings)
        connection.set_headers(headers)
        connection.set_data(data)

        # runs the sending of the initial request, even though the
        # connection may not be open yet, if that's the case this
        # initial data will be queued for latter delivery (on connect)
        connection.send_request()

        # verifies if the current request to be done should create
        # a request structure representing it, this is the case when
        # the request is synchronous and no handled is defined and
        # when then on result callback is defined, this callback receives
        # this request structure as the result, and it contains the
        # complete set of contents of the http request (easy usage)
        has_request = not async and not on_data and not callback
        has_request = has_request or on_result
        if has_request:

            # creates both the buffer list and the request structure so that
            # they may be used for the correct construction of the request
            # structure that is going to be send in the callback
            buffer = []
            request = dict(code = None, data = None)

            def on_partial(connection, parser, data):
                buffer.append(data)

            def on_message(connection, parser, message):
                cls.set_request(parser, buffer, request = request)
                if on_result: on_result(connection, parser, request)

            # sets the proper callback references so that the newly created
            # clojure based methods are called for the current connection
            # under the desired events, for the construction of the request
            on_data = on_partial
            callback = on_message

        # defines the proper return result value taking into account if
        # this is a synchronous or asynchronous request, one uses the
        # connection as the result and the other the request structure
        if async: result = connection
        elif has_request: result = request
        else: result = None

        # registers for the proper event handlers according to the
        # provided parameters, note that these are considered to be
        # the lower level infra-structure of the event handling
        if on_headers: connection.bind("headers", on_headers)
        if on_data: connection.bind("partial", on_data)
        if callback: connection.bind("message", callback)

        # in case the current request is not meant to be handled as
        # asynchronous tries to start the current event loop (blocking
        # the current workflow) then returns the proper value to the
        # caller method (taking into account if it is sync or async)
        not async and self.start()
        return result

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)
        self.trigger("connect", self, connection)

    def on_acquire(self, connection):
        netius.StreamClient.on_acquire(self, connection)
        self.trigger("acquire", self, connection)
        connection.ensure_write()

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
    buffer = []

    def on_headers(client, parser, headers):
        print(parser.code_s + " " + parser.status_s)

    def on_partial(client, parser, data):
        data = data
        data and buffer.append(data)

    def on_message(client, parser, message):
        request = HTTPClient.set_request(parser, buffer)
        print(request["headers"])
        print(request["data"] or b"[empty data]")
        client.close()

    def on_close(client, connection):
        client.close()

    client = HTTPClient()
    client.get("https://www.flickr.com/")
    client.bind("headers", on_headers)
    client.bind("partial", on_partial)
    client.bind("message", on_message)
    client.bind("close", on_close)
