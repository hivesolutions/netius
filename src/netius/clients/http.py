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

import time
import zlib
import base64

import netius.common

from netius.common import PLAIN_ENCODING, CHUNKED_ENCODING,\
    GZIP_ENCODING, DEFLATE_ENCODING

Z_PARTIAL_FLUSH = 1
""" The zlib constant value representing the partial flush
of the current zlib stream, this value has to be defined
locally as it is not defines under the zlib module """

BASE_HEADERS = {
    "user-agent" : netius.IDENTIFIER
}
""" The map containing the complete set of headers
that are meant to be applied to all the requests """

class HTTPConnection(netius.Connection):

    def __init__(self, encoding = PLAIN_ENCODING, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.encoding = encoding
        self.current = encoding
        self.gzip = None
        self.gzip_c = None
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
        if self.gzip: self._close_gzip(safe = True)
        if self.gzip_c: self.gzip_c = None

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

    def flush(self, force = False, callback = None):
        if self.current == DEFLATE_ENCODING:
            self._flush_gzip(force = force, callback = callback)
        elif self.current == GZIP_ENCODING:
            self._flush_gzip(force = force, callback = callback)
        elif self.current == CHUNKED_ENCODING:
            self._flush_chunked(force = force, callback = callback)
        elif self.current == PLAIN_ENCODING:
            self._flush_plain(force = force, callback = callback)

        self.current = self.encoding

    def send_base(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        force = False,
        callback = None
    ):
        data = netius.legacy.bytes(data) if data else data
        if self.current == PLAIN_ENCODING:
            return self.send_plain(
                data,
                stream = stream,
                final = final,
                delay = delay,
                force = force,
                callback = callback
            )
        elif self.current == CHUNKED_ENCODING:
            return self.send_chunked(
                data,
                stream = stream,
                final = final,
                delay = delay,
                force = force,
                callback = callback
            )
        elif self.current == GZIP_ENCODING:
            return self.send_gzip(
                data,
                stream = stream,
                final = final,
                delay = delay,
                force = force,
                callback = callback
            )
        elif self.current == DEFLATE_ENCODING:
            return self.send_gzip(
                data,
                stream = stream,
                final = final,
                delay = delay,
                force = force,
                callback = callback
            )

    def send_plain(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        force = False,
        callback = None
    ):
        return self.send(
            data,
            delay = delay,
            force = force,
            callback = callback
        )

    def send_chunked(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        force = False,
        callback = None
    ):
        # in case there's no valid data to be sent uses the plain
        # send method to send the empty string and returns immediately
        # to the caller method, to avoid any problems
        if not data: return self.send_plain(
            data,
            stream = stream,
            final = final,
            delay = delay,
            force = force,
            callback = callback
        )

        # creates the new list that is going to be used to store
        # the various parts of the chunk and then calculates the
        # size (in bytes) of the data that is going to be sent
        buffer = []
        size = len(data)

        # creates the various parts of the chunk with the size
        # of the data that is going to be sent and then adds
        # each of the parts to the chunk buffer list
        buffer.append(netius.legacy.bytes("%x\r\n" % size))
        buffer.append(data)
        buffer.append(netius.legacy.bytes("\r\n"))

        # joins the buffer containing the chunk parts and then
        # sends it to the connection using the plain method
        buffer_s = b"".join(buffer)
        return self.send_plain(
            buffer_s,
            stream = stream,
            final = final,
            delay = delay,
            force = force,
            callback = callback
        )

    def send_gzip(
        self,
        data,
        stream = None,
        final = True,
        delay = True,
        force = False,
        callback = None,
        level = 6
    ):
        # verifies if the provided data buffer is valid and in
        # in case it's not propagates the sending to the upper
        # layer (chunked sending) for proper processing
        if not data: return self.send_chunked(
            data,
            stream = stream,
            final = final,
            delay = delay,
            force = force,
            callback = callback
        )

        # "calculates" if the current sending of gzip data is
        # the first one by verifying if the gzip object is set
        is_first = self.gzip == None

        # in case this is the first sending a new compress object
        # is created with the requested compress level, notice that
        # the special deflate case is handled differently
        if is_first:
            is_deflate = self.is_deflate()
            wbits = -zlib.MAX_WBITS if is_deflate else zlib.MAX_WBITS | 16
            self.gzip = zlib.compressobj(level, zlib.DEFLATED, wbits)

        # compresses the provided data string and removes the
        # initial data contents of the compressed data because
        # they are not part of the gzip specification, notice
        # that in case the resulting of the compress operation
        # is not valid a sync flush operation is performed
        data_c = self.gzip.compress(data)
        if not data_c: data_c = self.gzip.flush(Z_PARTIAL_FLUSH)

        # sends the compressed data to the client endpoint setting
        # the correct callback values as requested
        return self.send_chunked(
            data_c,
            stream = stream,
            final = final,
            delay = delay,
            force = force,
            callback = callback
        )

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
        parsed = None,
        safe = False
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
        self.safe = safe

    def send_request(self):
        method = self.method
        path = self.path
        version = self.version
        headers = self.headers
        data = self.data
        parsed = self.parsed
        safe = self.safe

        if parsed.query: path += "?" + parsed.query

        headers = dict(headers)
        self._apply_base(headers)
        self._apply_dynamic(headers)
        self._apply_connection(headers)
        if safe: self._headers_normalize(headers)

        buffer = []
        buffer.append("%s %s %s\r\n" % (method, path, version))
        for key, value in headers.items():
            key = netius.common.header_up(key)
            if not type(value) == list: value = (value,)
            for _value in value:
                _value = netius.legacy.ascii(_value)
                buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        count = self.send_plain(buffer_data, force = True)
        if not data: return count

        count += self.send_base(data, force = True)
        return count

    def set_encoding(self, encoding):
        self.current = encoding

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

    def raw_data(self, data):
        """
        Tries to obtain the raw version of the provided data, taking
        into account the possible content encoding present for compression
        or any other kind of operation.

        :type data: String
        :param data: The data to be converted back to its original
        raw value (probably through decompression).
        :rtype: String
        :return: The final raw value for the provided data.
        """

        encoding = self.parser.headers.get("content-encoding", None)
        if not encoding: return data
        if not self.gzip_c:
            is_deflate = encoding == "deflate"
            wbits = zlib.MAX_WBITS if is_deflate else zlib.MAX_WBITS | 16
            self.gzip_c = zlib.decompressobj(wbits)
        return self.gzip_c.decompress(data)

    def is_plain(self):
        return self.current == PLAIN_ENCODING

    def is_chunked(self):
        return self.current > PLAIN_ENCODING

    def is_gzip(self):
        return self.current == GZIP_ENCODING

    def is_deflate(self):
        return self.current == DEFLATE_ENCODING

    def is_compressed(self):
        return self.current > CHUNKED_ENCODING

    def is_uncompressed(self):
        return not self.is_compressed()

    def is_flushed(self):
        return self.current > PLAIN_ENCODING

    def is_measurable(self, strict = True):
        if self.is_compressed(): return False
        if strict and self.is_chunked(): return False
        return True

    def on_data(self):
        message = self.parser.get_message()
        self.trigger("message", self, self.parser, message)
        self.owner.on_data_http(self, self.parser)
        self.parser.clear()
        self.gzip_c = None

    def on_partial(self, data):
        self.trigger("partial", self, self.parser, data)
        self.owner.on_partial_http(self, self.parser, data)

    def on_headers(self):
        self.trigger("headers", self, self.parser)
        self.owner.on_headers_http(self, self.parser)

    def on_chunk(self, range):
        self.trigger("chunk", self, self.parser, range)
        self.owner.on_chunk_http(self, self.parser, range)

    def _flush_plain(self, force = False, callback = None):
        if not callback: return
        self.send_plain(b"", force = force, callback = callback)

    def _flush_chunked(self, force = False, callback = None):
        self.send_plain(b"0\r\n\r\n", force = force, callback = callback)

    def _flush_gzip(self, force = False, callback = None):
        # in case the gzip structure has not been initialized
        # (no data sent) no need to run the flushing of the
        # gzip data, so only the chunked part is flushed
        if not self.gzip:
            self._flush_chunked(force = force, callback = callback)
            return

        # flushes the internal zlib buffers to be able to retrieve
        # the data pending to be sent to the client and then sends
        # it using the chunked encoding strategy
        data_c = self.gzip.flush(zlib.Z_FINISH)
        self.send_chunked(data_c, force = force, final = False)

        # resets the gzip values to the original ones so that new
        # requests will starts the information from the beginning
        self.gzip = None

        # runs the flush operation for the underlying chunked encoding
        # layer so that the client is correctly notified about the
        # end of the current request (normal operation)
        self._flush_chunked(force = force, callback = callback)

    def _close_gzip(self, safe = True):
        # in case the gzip object is not defined returns the control
        # to the caller method immediately (nothing to be done)
        if not self.gzip: return

        try:
            # runs the flush operation for the the final finish stage
            # (note that an exception may be raised) and then unsets
            # the gzip object (meaning no more interaction)
            self.gzip.flush(zlib.Z_FINISH)
            self.gzip = None
        except:
            # in case the safe flag is not set re-raises the exception
            # to the caller stack (as expected by the callers)
            if not safe: raise

    def _apply_base(self, headers, replace = False):
        for key, value in BASE_HEADERS.items():
            if not replace and key in headers: continue
            headers[key] = value

    def _apply_dynamic(self, headers):
        host = self.host
        port = self.port
        data = self.data
        is_plain = self.is_plain()

        length = len(data) if data else 0

        if port in (80, 443): host_s = host
        else: host_s = "%s:%d" % (host, port)

        if not "connection" in headers:
            headers["connection"] = "keep-alive"
        if not "host" in headers:
            headers["host"] = host_s
        if not "content-length" in headers and is_plain:
            headers["content-length"] = str(length)
        if not "accept-encoding" in headers and self.encodings:
            headers["accept-encoding"] = self.encodings

    def _apply_connection(self, headers, strict = True):
        is_chunked = self.is_chunked()
        is_gzip = self.is_gzip()
        is_deflate = self.is_deflate()
        is_compressed = self.is_compressed()
        is_measurable = self.is_measurable(strict = strict)
        has_length = "content-length" in headers
        has_ranges = "accept-ranges" in headers

        if "transfer-encoding" in headers: del headers["transfer-encoding"]
        if "content-encoding" in headers: del headers["content-encoding"]

        if is_chunked: headers["transfer-encoding"] = "chunked"

        if is_gzip: headers["content-encoding"] = "gzip"

        if is_deflate: headers["content-encoding"] = "deflate"

        if not is_measurable and has_length: del headers["content-length"]
        if is_compressed and has_ranges: del headers["accept-ranges"]

    def _headers_normalize(self, headers):
        for key, value in headers.items():
            if not type(value) in (list, tuple): continue
            headers[key] = ";".join(value)

class HTTPClient(netius.StreamClient):
    """
    Simple test of an http client, supports a series of basic
    operations and makes use of the http parser from netius.

    The current implementation supports the auto-release of the
    connection once the message has been received, this is optional
    and may be disabled with an argument in the constructor.
    """

    def __init__(
        self,
        auto_release = True,
        auto_close = False,
        auto_pause = False,
        *args,
        **kwargs
    ):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.auto_release = auto_release
        self.auto_close = auto_close
        self.auto_pause = auto_pause

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
        safe = False,
        connection = None,
        async = True,
        daemon = True,
        timeout = None,
        callback = None,
        on_close = None,
        on_headers = None,
        on_data = None,
        on_result = None,
        http_client = None,
        **kwargs
    ):
        if not http_client: http_client = cls.get_client_s(
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
            safe = safe,
            connection = connection,
            async = async,
            timeout = timeout,
            callback = callback,
            on_close = on_close,
            on_headers = on_headers,
            on_data = on_data,
            on_result = on_result
        )

    @classmethod
    def to_response(cls, map, raise_e = True):
        error = map.get("error", None)
        message = map.get("message", None)
        exception = map.get("exception", None)
        is_error = True if error and raise_e else False
        if not is_error: return netius.common.HTTPResponse(
            data = map.get("data", None),
            code = map.get("code", 500),
            status = map.get("status", None),
            headers = map.get("headers", None)
        )
        message = message or "Undefined error (%s)" % error
        if exception: raise exception
        raise netius.NetiusError(message)

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

    @classmethod
    def set_error(cls, error, message = None, request = None, force = False):
        if request == None: request = dict()
        if "error" in request and not force: return
        request["error"] = error
        request["message"] = message
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
        encoding = PLAIN_ENCODING,
        encodings = "gzip, deflate",
        safe = False,
        connection = None,
        async = True,
        timeout = None,
        callback = None,
        on_close = None,
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
        timeout = timeout or 60

        # runs the loading process, so that services like logging are
        # available right away and may be used immediately as expected
        # by the http method loader method, note that in case the loading
        # process as already been executed the logic is ignored, the
        # execution of the load is only applied to non async requests
        not async and self.load()

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
            parsed = parsed,
            safe = safe
        )
        connection.set_encoding(encoding)
        connection.set_encodings(encodings)
        connection.set_headers(headers)
        connection.set_data(data)

        # runs a series of unbind operation from the connection so that it
        # becomes "free" from any previous usage under different context
        connection.unbind("close")
        connection.unbind("headers")
        connection.unbind("partial")
        connection.unbind("message")

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
            # structure that is going to be send in the callback, then sets
            # the identifier (memory address) of the request in the connection
            buffer = []
            request = dict(code = None, data = None)
            connection._request = id(request)

            def on_finish(connection):
                connection._request = None
                if request["code"]: return
                cls.set_error(
                    "closed",
                    message = "Connection closed",
                    request = request
                )
                if self.auto_close: self.close()
                if self.auto_pause: self.pause()

            def on_partial(connection, parser, data):
                buffer.append(data)
                received = request.get("received", 0)
                request["received"] = received + len(data)
                request["last"] = time.time()

            def on_message(connection, parser, message):
                cls.set_request(parser, buffer, request = request)
                if on_result: on_result(connection, parser, request)

            # sets the proper callback references so that the newly created
            # clojure based methods are called for the current connection
            # under the desired events, for the construction of the request
            on_close = on_finish
            on_data = on_partial
            callback = on_message

        # creates the function that is going to be used to validate
        # the on connect timeout so that whenever the timeout for
        # the connection operation is exceeded an error is set int
        # the connection and the connection is properly closed
        def connect_timeout():
            if not connection.is_open(): return
            if connection.is_connected(): return
            has_request and cls.set_error(
                "timeout",
                message = "Timeout on connect",
                request = request
            )
            connection.close()
            if self.auto_close: self.close()
            if self.auto_pause: self.pause()

        # creates a function that is going to be used to validate
        # the receive operation of the connection (receive timeout)
        def receive_timeout():
            # runs the initial verification operations that will
            # try to validate if the requirements for proper request
            # validations are defined, if any of them is not the control
            # full is returned immediately avoiding re-schedule of handler
            if not has_request: return
            if not connection.is_open(): return
            if not connection._request == id(request): return
            if request["code"]: return

            # retrieves the current time and the time of the last data
            # receive operation and using that calculates the delta
            current = time.time()
            last = request.get("last", 0)
            delta = current - last

            # retrieves the amount of bytes that have been received so
            # far during the request handling this is going to be used
            # for logging purposes on the error information to be printed
            received = request.get("received", 0)

            # determines if the connection is considered valid, either
            # the connection is not "yet" connected of the time between
            # receive operations is valid, and if that's the case delays
            # the timeout verification according to the timeout value
            if not connection.is_connected() or delta < timeout:
                self.delay(receive_timeout, timeout = timeout)
                return

            # tries to determine the proper message that is going to be
            # set in the request error, this value should take into account
            # the current development mode flag value
            if self.is_devel(): message = "Timeout on receive (received %d bytes)" % received
            else: message = "Timeout on receive"

            # sets the error information in the request so that the
            # request handler is properly "notified" about the error
            cls.set_error(
                "timeout",
                message = message,
                request = request
            )

            # closes the connection (it's no longer considered valid)
            # and then verifies the various auto closing values
            connection.close()
            if self.auto_close: self.close()
            if self.auto_pause: self.pause()

        # defines the proper return result value taking into account if
        # this is a synchronous or asynchronous request, one uses the
        # connection as the result and the other the request structure
        if async: result = connection
        elif has_request: result = request
        else: result = None

        # registers for the proper event handlers according to the
        # provided parameters, note that these are considered to be
        # the lower level infra-structure of the event handling
        if on_close: connection.bind("close", on_close)
        if on_headers: connection.bind("headers", on_headers)
        if on_data: connection.bind("partial", on_data)
        if callback: connection.bind("message", callback)

        # runs the sending of the initial request, even though the
        # connection may not be open yet, if that's the case this
        # initial data will be queued for latter delivery (on connect)
        connection.send_request()

        # schedules a delay operation to run the timeout handlers for
        # both connect and receive operations (these are considered the
        # initial triggers for the such verifiers)
        self.delay(connect_timeout, timeout = timeout)
        self.delay(receive_timeout, timeout = timeout)

        # in case the current request is not meant to be handled as
        # asynchronous tries to start the current event loop (blocking
        # the current workflow) then returns the proper value to the
        # caller method (taking into account if it is sync or async)
        not async and not connection.is_closed() and self.start()
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

        # triggers the connection close event in the client and
        # then removes the connection from the connection pool
        self.trigger("close", self, connection)
        self.remove_c(connection)

        # verifies if the current client was created with the
        # auto close or pause flags and there are no more
        # connections left open if that's the case closes the
        # current client so that no more interaction exists as it's
        # no longer required (as defined by the specification)
        if self.connections: return
        if self.auto_close: self.close()
        if self.auto_pause: self.pause()

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
        if self.auto_pause: self.pause()

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
