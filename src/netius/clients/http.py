#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import time
import zlib
import base64
import tempfile

import netius.common

from netius.common import PLAIN_ENCODING, CHUNKED_ENCODING,\
    GZIP_ENCODING, DEFLATE_ENCODING

Z_PARTIAL_FLUSH = 1
""" The zlib constant value representing the partial flush
of the current zlib stream, this value has to be defined
locally as it is not defines under the zlib module """

class HTTPProtocol(netius.StreamProtocol):
    """
    Implementation of the HTTP protocol to be used by a client
    of the HTTP implementation to send requests and receive
    responses.
    """

    BASE_HEADERS = {
        "user-agent" : netius.IDENTIFIER
    }
    """ The map containing the complete set of headers
    that are meant to be applied to all the requests """

    def __init__(
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
        request = False,
        asynchronous = True,
        timeout = None,
        use_file = False,
        callback = None,
        on_init = None,
        on_open = None,
        on_close = None,
        on_headers = None,
        on_data = None,
        on_result = None,
        *args,
        **kwargs
    ):
        netius.StreamProtocol.__init__(self, *args, **kwargs)
        self.parser = None
        self.set(
            method,
            url,
            params = params,
            headers = headers,
            data = data,
            version = version,
            encoding = encoding,
            encodings = encodings,
            safe = safe,
            request = request,
            asynchronous = asynchronous,
            timeout = timeout,
            use_file = use_file,
            callback = callback,
            on_init = on_init,
            on_open = on_open,
            on_close = on_close,
            on_headers = on_headers,
            on_data = on_data,
            on_result = on_result
        )

    @classmethod
    def key_g(cls, url):
        parsed = netius.legacy.urlparse(url)
        ssl = parsed.scheme == "https"
        host = parsed.hostname
        port = parsed.port or (443 if ssl else 80)
        return (host, port, ssl)

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
    def decode_zlib_file(
        cls,
        input,
        output,
        buffer_size = 16384,
        wbits = zlib.MAX_WBITS | 16
    ):
        decompressor = zlib.decompressobj(wbits)
        while True:
            data = input.read(buffer_size)
            if not data: break
            raw_data = decompressor.decompress(data)
            output.write(raw_data)
        raw_data = decompressor.flush()
        output.write(raw_data)
        return output

    @classmethod
    def decode_gzip_file(
        cls,
        input,
        output,
        buffer_size = 16384,
        wbits = zlib.MAX_WBITS | 16
    ):
        return cls.decode_zlib_file(
            input,
            output,
            buffer_size = buffer_size,
            wbits = wbits
        )

    @classmethod
    def decode_deflate_file(
        cls,
        input,
        output,
        buffer_size = 16384,
        wbits = -zlib.MAX_WBITS
    ):
        return cls.decode_zlib_file(
            input,
            output,
            buffer_size = buffer_size,
            wbits = wbits
        )

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
    def set_request_file(
        cls,
        parser,
        input,
        request = None,
        output = None,
        buffer_size = 16384
    ):
        # verifies if a request object has been passes to the current
        # method and if that's not the case creates a new one (as a map)
        if request == None: request = dict()

        # retrieves the complete set of headers and tries discover the
        # encoding of it and the associated decoder (if any)
        headers = parser.get_headers()
        encoding = headers.get("Content-Encoding", None)
        decoder = getattr(cls, "decode_%s_file" % encoding) if encoding else None

        # in case there's a decoder and an input (file) then runs the decoding
        # process setting the data as the resulting (decoded object)
        if decoder and input:
            if output == None: output = tempfile.NamedTemporaryFile(mode = "w+b")
            input.seek(0)
            try:
                data = decoder(
                    input,
                    output,
                    buffer_size = buffer_size
                )
            finally:
                input.close()

        # otherwise it's a simplified process (no decoding required) and the
        # data may be set directly as the input file
        else:
            data = input

        # seeks the data object to the initial position so that it
        # is set as ready to be read from a third party
        data.seek(0)

        # updates the structure of the request object/map so that it
        # contains a series of information on the request, including
        # the file contents (stored in a temporary file)
        request["code"] = parser.code
        request["status"] = parser.status
        request["headers"] = headers
        request["data"] = data

        # returns the request object that has just been populated
        # to the caller method so that it may be used to read the contents
        return request

    @classmethod
    def set_error(cls, error, message = None, request = None, force = False):
        if request == None: request = dict()
        if "error" in request and not force: return
        request["error"] = error
        request["message"] = message
        return request

    def open_c(self, *args, **kwargs):
        netius.StreamProtocol.open_c(self, *args, **kwargs)

        # creates a new HTTP parser instance and set the correct event
        # handlers so that the data parsing is properly handled
        self.parser = netius.common.HTTPParser(self, type = netius.common.RESPONSE)
        self.parser.bind("on_data", self._on_data)
        self.parser.bind("on_partial", self.on_partial)
        self.parser.bind("on_headers", self.on_headers)
        self.parser.bind("on_chunk", self.on_chunk)

    def close_c(self, *args, **kwargs):
        netius.StreamProtocol.close_c(self, *args, **kwargs)

        if self.parser: self.parser.destroy()
        if self.parsed: self.parsed = None
        if self.gzip: self._close_gzip(safe = True)
        if self.gzip_c: self.gzip_c = None

    def info_dict(self, full = False):
        info = netius.StreamProtocol.info_dict(self, full = full)
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

    def connection_made(self, transport):
        netius.StreamProtocol.connection_made(self, transport)

        # performs the run request operation that should trigger
        # the process of sending the request to the server
        self.run_request()

    def loop_set(self, loop):
        netius.StreamProtocol.loop_set(self, loop)
        self.set_dynamic()

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

    def set(
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
        request = False,
        asynchronous = True,
        timeout = None,
        use_file = False,
        callback = None,
        on_init = None,
        on_open = None,
        on_close = None,
        on_headers = None,
        on_data = None,
        on_result = None,
    ):
        cls = self.__class__

        self.method = method.upper()
        self.url = url
        self.params = params or {}
        self.headers = headers or {}
        self.data = data
        self.version = version
        self.encoding = encoding
        self.current = encoding
        self.encodings = encodings
        self.safe = safe
        self.asynchronous = asynchronous
        self.timeout = timeout or 60
        self.use_file = use_file
        self.parsed = False
        self.request = None
        self.ssl = False
        self.host = None
        self.port = None
        self.path = None
        self.gzip = None
        self.gzip_c = None

        # in case the provided data is a unicode string it's converted into
        # a raw set of bytes using the default encoding
        if netius.legacy.is_unicode(self.data):
            self.data = netius.legacy.bytes(data)

        # in case the data currently set is a plain byte stream wraps it
        # around an iterator to provide compatibility with generators
        if netius.legacy.is_bytes(self.data):
            self.data = iter((len(self.data), self.data))

        # in case the provided data responds to the typical file-like
        # object interface, then it's wrapped around a generator to
        # provided compatibility with the generators based interface
        if hasattr(self.data, "tell"):
            self.data = netius.common.file_iterator(self.data)

        # computes the unique re-usage key for the current protocol taking
        # into account its own state
        self.key = cls.key_g(self.url)

        # runs the unbind all operation to make sure that no handlers is
        # currently registered for operations
        self.unbind_all()

        # in case there's an HTTP parser already set for the protocol runs
        # the reset operation so that its state is guaranteed to be clean
        if self.parser: self.parser.clear()

        # tries to determine if the protocol response should be request
        # wrapped, meaning that a map based object is going to be populated
        # with the contents of the HTTP request/response
        wrap_request = request or (not asynchronous and not on_data and not callback)
        wrap_request = wrap_request or on_result

        # in case the wrap request flag is set (conditions for request usage
        # are met) the protocol is called to run the wrapping operation
        if wrap_request:
            _request, on_close, on_data, callback = self.wrap_request(
                use_file = use_file,
                callback = callback,
                on_close = on_close,
                on_data = on_data,
                on_result = on_result
            )

        # registers for the proper event handlers according to the
        # provided parameters, note that these are considered to be
        # the lower level infra-structure of the event handling
        if on_init: self.bind("loop_set", on_init)
        if on_open: self.bind("open", on_open)
        if on_close: self.bind("close", on_close)
        if on_headers: self.bind("headers", on_headers)
        if on_data: self.bind("partial", on_data)
        if callback: self.bind("message", callback)

        # sets the static part of the protocol internal (no loop is required)
        # so that the required initials fields are properly populated
        self.set_static()

        # returns the current instance with the proper modified state
        # according to the current changes
        return self

    def set_all(self):
        self.set_static()
        self.set_dynamic()

    def set_static(self):
        # creates the message that is going to be used in the logging of
        # the current method request for debugging purposes, this may be
        # useful for a full record traceability of the request
        message = "%s %s %s" % (self.method, self.url, self.version)
        self.debug(message)

        # stores the initial version of the url in a fallback variable so
        # that it may latter be used for the storage of that information
        # in the associated connection (used in callbacks)
        self.base = self.url

        # encodes the provided parameters into the query string and then
        # adds these parameters to the end of the provided url, these
        # values are commonly named get parameters
        query = netius.legacy.urlencode(self.params)
        if query: self.url = self.url + "?" + query

        # parses the provided url and retrieves the various parts of the
        # url that are going to be used in the creation of the connection
        # takes into account some default values in case their are not part
        # of the provided url (eg: port and the scheme)
        self.parsed = netius.legacy.urlparse(self.url)
        self.ssl = self.parsed.scheme == "https"
        self.host = self.parsed.hostname
        self.port = self.parsed.port or (443 if self.ssl else 80)
        self.path = self.parsed.path or "/"
        self.username = self.parsed.username
        self.password = self.parsed.password

        # in case both the username and the password values are defined the
        # authorization header must be created and added to the default set
        # of headers that are going to be included in the request
        if self.username and self.password:
            payload = "%s:%s" % (self.username, self.password)
            payload = netius.legacy.bytes(payload)
            authorization = base64.b64encode(payload)
            authorization = netius.legacy.str(authorization)
            self.headers["authorization"] = "Basic %s" % authorization

        # sets the complete set of information under the protocol instance so
        # that it may be latter used to send the request through the transport
        self.set_headers(self.headers)

    def set_dynamic(self):
        cls = self.__class__

        # creates the function that is going to be used to validate
        # the on connect timeout so that whenever the timeout for
        # the connection operation is exceeded an error is set int
        # the connection and the connection is properly closed
        def connect_timeout():
            if self.is_open(): return
            self.request and cls.set_error(
                "timeout",
                message = "Timeout on connect",
                request = self.request
            )
            self.close()

        # schedules a delay operation to run the timeout handler for
        # both connect operation (this is considered the initial
        # triggers for the such verifiers)
        self.delay(connect_timeout, timeout = self.timeout)

    def run_request(self):
        # retrieves the reference to the top level class to be used
        # for class level operations
        cls = self.__class__

        # saves the current request instance locally to be used latter
        # for request verification (integrity check)
        request = self.request

        # creates a function that is going to be used to validate
        # the receive operation of the connection (receive timeout)
        def receive_timeout():
            # runs the initial verification operations that will
            # try to validate if the requirements for proper request
            # validations are defined, if any of them is not the control
            # full is returned immediately avoiding re-schedule of handler
            if not self.request: return
            if not self.is_open(): return
            if self.request["code"]: return
            if not id(request) == id(self.request): return

            # retrieves the current time and the time of the last data
            # receive operation and using that calculates the delta
            current = time.time()
            last = self.request.get("last", 0)
            delta = current - last

            # retrieves the amount of bytes that have been received so
            # far during the request handling this is going to be used
            # for logging purposes on the error information to be printed
            received = self.request.get("received", 0)

            # determines if the protocol is considered valid, either
            # the connection is not "yet" connected, the time between
            # receive operations is valid or there's data still pending
            # to be sent to the server side, and if that's the case delays
            # the timeout verification according to the timeout value
            if not self.is_open() or delta < self.timeout or\
                not self.transport().get_write_buffer_size() == 0:
                self.delay(receive_timeout, timeout = self.timeout)
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
                request = self.request
            )

            # closes the protocol (it's no longer considered valid)
            # and then verifies the various auto closing values
            self.close()

        # sends the request effectively triggering a chain of event
        # that should end with the complete receiving of the response
        self.send_request(callback = lambda c: self.delay(
            receive_timeout, timeout = self.timeout
        ))

    def send_request(self, callback = None):
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
        for key, value in netius.legacy.iteritems(headers):
            key = netius.common.header_up(key)
            if not isinstance(value, list): value = (value,)
            for _value in value:
                _value = netius.legacy.ascii(_value)
                buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        if data: count = self.send_plain(buffer_data, force = True)
        else: count = self.send_plain(buffer_data, force = True, callback = callback)

        if not data: return count

        def send_part(transport = None):
            try:
                _data = next(data)
            except StopIteration:
                if hasattr(data, "close"): data.close()
                callback and callback(transport)
                return

            self.send_base(_data, force = True, callback = send_part)

        send_part()

        return count

    def wrap_request(
        self,
        use_file = False,
        callback = None,
        on_close = None,
        on_data = None,
        on_result = None
    ):
        """
        Wraps the current set of operations for the protocol so that
        a request object is going to be created and properly populated
        according to the multiple protocol events.

        This method should focus on wrapping the provided callback handlers
        with ones that change the request object state.

        :type use_file: bool
        :param use_file: If a filesystem based approach should be used
        for the storing of the request information.
        :type callback: Function
        :param callback: Callback function to be called when the message
        response has been completely received.
        :type on_close: Function
        :param on_close: Callback function to be called when the underlying
        protocol is closed.
        :type on_data: Function
        :param on_data: Function to be called whenever some data is received
        from the client side, notice that this data may be encoded (eg: gzip).
        :type on_result: Function
        :param on_result: Callback function to be called on the final result
        with the resulting request object.
        :rtype: Tuple
        :return: The tuple containing both the request dictionary object that
        is going to store the information for the request in the current protocol
        and the multiple changed callback methods.
        """

        # retrieves the reference to the parent class object
        # going to be used for class wide operations
        cls = self.__class__

        # saves the references to the previous callback method so that
        # they can be used from the current request based approach
        _on_close = on_close
        _on_data = on_data
        _callback = callback

        # creates both the buffer list and the request structure so that
        # they may be used for the correct construction of the request
        # structure that is going to be send in the callback, then sets
        # the identifier (memory address) of the request in the connection
        buffer = tempfile.NamedTemporaryFile(mode = "w+b") if use_file else []
        self.request = dict(code = None, data = None)

        def on_close(protocol):
            if _on_close: _on_close(protocol)
            protocol._request = None
            if self.request["code"]: return
            cls.set_error(
                "closed",
                message = "Connection closed",
                request = self.request
            )

        def on_data(protocol, parser, data):
            if _on_data: _on_data(protocol, parser, data)
            if use_file: buffer.write(data)
            else: buffer.append(data)
            received = self.request.get("received", 0)
            self.request["received"] = received + len(data)
            self.request["last"] = time.time()

        def callback(protocol, parser, message):
            if _callback: _callback(protocol, parser, message)
            if use_file: cls.set_request_file(parser, buffer, request = self.request)
            else: cls.set_request(parser, buffer, request = self.request)
            if on_result: on_result(protocol, parser, self.request)

        # returns the request object that is going to be properly
        # populated over the life-cycle of the protocol
        return self.request, on_close, on_data, callback

    def set_headers(self, headers, normalize = True):
        self.headers = headers
        if normalize: self.normalize_headers()

    def normalize_headers(self):
        for key, value in netius.legacy.items(self.headers):
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

    def on_data(self, data):
        netius.StreamProtocol.on_data(self, data)
        self.parser.parse(data)

    def _on_data(self):
        message = self.parser.get_message()
        self.trigger("message", self, self.parser, message)
        self.parser.clear()
        self.gzip_c = None

    def on_partial(self, data):
        self.trigger("partial", self, self.parser, data)

    def on_headers(self):
        self.trigger("headers", self, self.parser)

    def on_chunk(self, range):
        self.trigger("chunk", self, self.parser, range)

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
        cls = self.__class__
        for key, value in netius.legacy.iteritems(cls.BASE_HEADERS):
            if not replace and key in headers: continue
            headers[key] = value

    def _apply_dynamic(self, headers):
        host = self.host
        port = self.port
        data = self.data
        is_plain = self.is_plain()

        # determines the proper strategy for data payload length, taking into
        # account if there's a payload and if it exists if it's a byte stream
        # or instead an iterator/generator
        if not data: length = 0
        elif netius.legacy.is_bytes(data): length = len(data)
        else: length = next(data)

        # ensures that if the content encoding is plain the content length
        # for the payload is defined otherwise it would be impossible to the
        # server side to determine when the content sending is finished
        netius.verify(
            not is_plain or not length == -1,
            message = "The content length must be defined for plain HTTP encoding"
        )

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
        for key, value in netius.legacy.items(headers):
            if not type(value) in (list, tuple): continue
            headers[key] = ";".join(value)

class HTTPClient(netius.ClientAgent):
    """
    Simple test of an HTTP client, supports a series of basic
    operations and makes use of the HTTP parser from netius.

    The current implementation supports the auto-release of the
    connection once the message has been received, this is optional
    and may be disabled with an argument in the constructor.
    """

    protocol = HTTPProtocol

    def __init__(
        self,
        auto_release = True,
        *args,
        **kwargs
    ):
        netius.ClientAgent.__init__(self, *args, **kwargs)
        self.auto_release = auto_release
        self.available = dict()
        self._loop = None

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
        asynchronous = True,
        daemon = True,
        timeout = None,
        use_file = False,
        callback = None,
        on_init = None,
        on_open = None,
        on_close = None,
        on_headers = None,
        on_data = None,
        on_result = None,
        http_client = None,
        **kwargs
    ):
        # in case no HTTP client instance is provided tries to
        # retrieve a static global one (singleton) to be used
        # for the current request operation
        if not http_client:
            http_client = cls.get_client_s(
                daemon = daemon,
                **kwargs
            )

        # calls the underlying method on the current HTTP client
        # propagating most of the arguments, and retrieves the resulting
        # value to be propagated to the current method's caller
        result = http_client.method(
            method,
            url,
            params = params,
            headers = headers,
            data = data,
            version = version,
            safe = safe,
            asynchronous = asynchronous,
            timeout = timeout,
            use_file = use_file,
            callback = callback,
            on_init = on_init,
            on_open = on_open,
            on_close = on_close,
            on_headers = on_headers,
            on_data = on_data,
            on_result = on_result,
            **kwargs
        )

        # returns the "final" result to the caller method so that
        # it may be used/processed by it (as expected)
        return result

    @classmethod
    def to_response(cls, map, raise_e = True):
        """
        Simple utility method that takes the classic dictionary
        based request and converts it into a simple HTTP response
        object to be used in a more interactive way.

        :type map: Dictionary
        :param map: The dictionary backed request object that is
        going to be converted into a response.
        :type raise_e: bool
        :param raise_e: If an exception should be raised in case
        there's an error in the HTTP status field.
        :rtype: HTTPResponse
        :return: The normalized response value.
        """

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

    def cleanup(self):
        netius.ClientAgent.cleanup(self)

        # iterates over the complete set of protocol instances
        # to be re-used and closes them, then empties the map
        # of available instances (no more re-usage possible)
        for protocol in netius.legacy.values(self.available):
            protocol.close()
        self.available.clear()

        # in case a (static) event loop is defined closes it,
        # not allowing any further re-usage of it (as expected)
        self._close_loop()

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
        request = False,
        close = True,
        asynchronous = True,
        timeout = None,
        use_file = False,
        callback = None,
        on_init = None,
        on_open = None,
        on_close = None,
        on_headers = None,
        on_data = None,
        on_result = None,
        loop = None,
        **kwargs
    ):
        # extracts the reference to the upper class element associated
        # with the current instance, to be used for operations
        cls = self.__class__

        # tries to retrieve the unique key from the provided URL and then
        # uses it to try to retrieve a possible already available protocol,
        # for connection re-usage (avoids long establish connection times)
        # notice that the event loop is also re-used accordingly
        key = cls.protocol.key_g(url)
        protocol = self.available.pop(key, None)
        if protocol and (not protocol.is_open() or\
            protocol.transport().is_closing()): protocol = None
        if protocol: loop = loop or protocol.loop()

        # determines if the loop instance was provided by the user so
        # that latter on we can determine if it should be closed (garbage
        # collection or not)
        user_loop = True if loop else False

        # in case the current execution model is not asynchronous a new
        # loop context must exist otherwise it may collide with the global
        # event loop execution creating unwanted behaviour
        if not asynchronous: loop = loop or self._get_loop(**kwargs)

        # creates the new protocol instance that is going to be used to
        # handle this new request, a new protocol represents also a new
        # parser object as defined by structure
        callable = protocol.set if protocol else cls.protocol
        protocol = callable(
            method,
            url,
            params = params,
            headers = headers,
            data = data,
            version = version,
            encoding = encoding,
            encodings = encodings,
            safe = safe,
            request = request,
            asynchronous = asynchronous,
            timeout = timeout,
            use_file = use_file,
            callback = callback,
            on_init = on_init,
            on_open = on_open,
            on_close = on_close,
            on_headers = on_headers,
            on_data = on_data,
            on_result = on_result
        )

        # verifies if the current protocol is already open and if that's the
        # case calls the connection made directly, indicating that the connection
        # is already established (re-usage of protocol), notice that an extra
        # verification process is applied to verify is the associated transport
        # is already closing because if that's the case re-usage is not valid
        if protocol.is_open() and not protocol.transport().is_closing():
            protocol.connection_made(protocol.transport())

        # runs the global connect stream function on netius to initialize the
        # connection operation and maybe a new event loop (if that's required)
        else:
            loop = netius.connect_stream(
                lambda: protocol,
                protocol.host,
                protocol.port,
                ssl = protocol.ssl,
                loop = loop
            )

        # in case the asynchronous mode is enabled returns the loop and the protocol
        # immediately so that it can be properly used by the caller
        if asynchronous: return loop, protocol

        def on_message(protocol, parser, message):
            # in case the auto release (no connection re-usage) mode is
            # set the protocol is closed immediately
            if self.auto_release:
                protocol.close()

            # verifies if the current connection is meant to be kept alive
            # and if that's not the case closes it immediately, this way
            # the client is the responsible for triggering the disconnect
            # operation, avoiding problems with possible connection re-usage
            elif not parser.keep_alive:
                protocol.close()

            # otherwise the protocol is set in the available map and
            # the only the loop is stopped (unblocking the processor)
            else:
                self.available[protocol.key] = protocol
                netius.compat_loop(loop).stop()

        def on_close(protocol):
            # verifies if the protocol being closed is currently in
            # the pool of available protocols, so that decisions on
            # the stopping of the event loop may be made latter on
            from_pool = protocol.key in self.available

            # because the protocol was closed we must release it from
            # the available map (if it exits) and then unblock the current
            # event loop call (stop operation)
            self.available.pop(protocol.key, None)

            # in case the protocol that is being closed is not the one
            # in usage returns immediately (no need to stop the event
            # loop for a protocol from the available pool)
            if from_pool: return

            # tries to retrieve the loop compatible value and if it's
            # successful runs the stop operation on the loop
            netius.compat_loop(loop).stop()

        # binds the protocol message and finish events to the associated
        # function for proper handling of the synchronous request details
        protocol.bind("message", on_message)
        protocol.bind("close", on_close)

        # runs the loop until complete, this should be the main blocking
        # call into the event loop, notice that in case the loop that was
        # used is not the HTTP client's static loop and also not a user's
        # provided loop it's closed immediately (garbage collection)
        loop.run_forever()
        if not loop == self._loop and not user_loop: loop.close()

        # returns the final request object (that should be populated by this
        # time) to the called method, so that a simple interface is provided
        return protocol.request

    def _get_loop(self, **kwargs):
        if not self._loop: self._loop = netius.new_loop(**kwargs)
        return self._loop

    def _close_loop(self):
        if not self._loop: return
        self._loop.close()
        self._loop = None

if __name__ == "__main__":
    buffer = []

    def on_headers(protocol, parser):
        print(parser.code_s + " " + parser.status_s)

    def on_partial(protocol, parser, data):
        data = data
        data and buffer.append(data)

    def on_message(protocol, parser, message):
        request = HTTPProtocol.set_request(parser, buffer)
        print(request["headers"])
        print(request["data"] or b"[empty data]")
        protocol.close()

    def on_finish(protocol):
        netius.compat_loop(loop).stop()

    url = netius.conf("HTTP_URL", "https://www.flickr.com/")

    client = HTTPClient()
    loop, protocol = client.get(url)

    protocol.bind("headers", on_headers)
    protocol.bind("partial", on_partial)
    protocol.bind("message", on_message)
    protocol.bind("finish", on_finish)

    loop.run_forever()
    loop.close()
else:
    __path__ = []
