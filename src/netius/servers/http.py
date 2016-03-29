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
    "Server" : netius.IDENTIFIER
}
""" The map containing the complete set of headers
that are meant to be applied to all the responses """

PLAIN_ENCODING = 1
""" Plain text encoding that does not transform the
data from its based format, should be used only as
a fallback method because of performance issues """

CHUNKED_ENCODING = 2
""" Chunked based encoding that allows the sending of
the data as a series of length based parts """

GZIP_ENCODING = 3
""" The gzip based encoding used to compress data, this
kind of encoding will always used chunked encoding so
that the content may be send in parts """

DEFLATE_ENCODING = 4
""" The deflate based encoding used to compress data, this
kind of encoding will always used chunked encoding so
that the content may be send in parts """

Z_PARTIAL_FLUSH = 1
""" The zlib constant value representing the partial flush
of the current zlib stream, this value has to be defined
locally as it is not defines under the zlib module """

ENCODING_MAP = dict(
    plain = 1,
    chunked = 2,
    gzip = 3,
    deflate = 4
)
""" The map associating the various types of encoding with
the corresponding integer value for each of them this is used
in the initial construction of the server """

class HTTPConnection(netius.Connection):

    def __init__(self, encoding = PLAIN_ENCODING, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.encoding = encoding
        self.current = encoding
        self.gzip = None

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        self.parser.bind("on_data", self.on_data)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()
        if self.gzip: self._close_gzip(safe = True)

    def send(self, data, delay = False, callback = None):
        data = netius.legacy.bytes(data) if data else data
        if self.current == PLAIN_ENCODING:
            self.send_plain(
                data,
                delay = delay,
                callback = callback
            )
        elif self.current == CHUNKED_ENCODING:
            self.send_chunked(
                data,
                delay = delay,
                callback = callback
            )
        elif self.current == GZIP_ENCODING:
            self.send_gzip(
                data,
                delay = delay,
                callback = callback
            )
        elif self.current == DEFLATE_ENCODING:
            self.send_gzip(
                data,
                delay = delay,
                callback = callback
            )

    def info_dict(self, full = False):
        info = netius.Connection.info_dict(self, full = full)
        info.update(
            encoding = self.encoding,
            current = self.current
        )
        if full: info.update(
            parser = self.parser.info_dict()
        )
        return info

    def flush(self, callback = None):
        if self.current == DEFLATE_ENCODING:
            self._flush_gzip(callback = callback)
        elif self.current == GZIP_ENCODING:
            self._flush_gzip(callback = callback)
        elif self.current == CHUNKED_ENCODING:
            self._flush_chunked(callback = callback)
        elif self.current == PLAIN_ENCODING:
            self._flush_plain(callback = callback)

        self.current = self.encoding

    def send_plain(self, data, delay = False, callback = None):
        netius.Connection.send(
            self,
            data,
            delay = delay,
            callback = callback
        )

    def send_chunked(self, data, delay = False, callback = None):
        # in case there's no valid data to be sent uses the plain
        # send method to send the empty string and returns immediately
        # to the caller method, to avoid any problems
        if not data: self.send_plain(
            data,
            delay = delay,
            callback = callback
        ); return

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
        self.send_plain(buffer_s, delay = delay, callback = callback)

    def send_gzip(self, data, delay = False, callback = None, level = 6):
        # verifies if the provided data buffer is valid and in
        # in case it's not propagates the sending to the upper
        # layer (chunked sending) for proper processing
        if not data: self.send_chunked(
            data,
            delay = delay,
            callback = callback
        ); return

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
        self.send_chunked(data_c, delay = delay, callback = callback)

    def send_response(
        self,
        data = None,
        headers = None,
        version = "HTTP/1.1",
        code = 200,
        code_s = None,
        apply = False,
        flush = True,
        callback = None
    ):
        data = data or ""
        headers = headers or dict()
        code_s = code_s or netius.common.CODE_STRINGS.get(code, None)
        data_l = len(data) if data else 0
        is_empty = code in (204, 304) and data_l == 0

        # verifies if the content length header is currently present
        # in the provided headers and in case it's not inserts it
        if not "content-length" in headers and not is_empty:
            headers["content-length"] = data_l

        # in case the apply flag is set the apply all operation is performed
        # so that a series of headers are applied to the current context
        # (things like the name of the server connection, etc)
        if apply: self.owner._apply_all(self.parser, self, headers)

        buffer = []
        buffer.append("%s %d %s\r\n" % (version, code, code_s))
        for key, value in headers.items():
            key = netius.common.header_up(key)
            if not type(value) == list: value = (value,)
            for _value in value: buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        self.send_plain(buffer_data)
        if flush: self.send(data); self.flush(callback = callback)
        else: self.send(data, callback = callback)

    def parse(self, data):
        return self.parser.parse(data)

    def resolve_encoding(self, parser):
        # in case the "target" encoding is the plain one nothing
        # is required to be done as this is allowed by any kind
        # of http compliant connection (returns immediately)
        if self.encoding == PLAIN_ENCODING:
            self.current = PLAIN_ENCODING

        # if the target encoding is chunked must verify if the
        # type of http connection in question is 1.1 or above
        # otherwise must down-grade the encoding to plain
        elif self.encoding == CHUNKED_ENCODING:
            if parser.version < netius.common.HTTP_11:
                self.current = PLAIN_ENCODING
            else:
                self.current = CHUNKED_ENCODING

        # if the target encoding is the compressed gzip style the
        # current request must be verified have the version larger
        # than the 1.1 and the gzip encoding must be accepted
        elif self.encoding == GZIP_ENCODING:
            if parser.version < netius.common.HTTP_11:
                self.current = PLAIN_ENCODING
            elif not "gzip" in parser.get_encodings():
                self.current = CHUNKED_ENCODING
            else:
                self.current = GZIP_ENCODING

        # if the target encoding is the compressed deflate style the
        # current request must be verified have the version larger
        # than the 1.1 and the deflate encoding must be accepted
        elif self.encoding == DEFLATE_ENCODING:
            if parser.version < netius.common.HTTP_11:
                self.current = PLAIN_ENCODING
            elif not "deflate" in parser.get_encodings():
                self.current = CHUNKED_ENCODING
            else:
                self.current = DEFLATE_ENCODING

    def set_encoding(self, encoding):
        self.current = encoding

    def set_chunked(self):
        self.current = CHUNKED_ENCODING

    def set_gzip(self):
        self.current = GZIP_ENCODING

    def set_deflate(self):
        self.current = DEFLATE_ENCODING

    def is_chunked(self):
        return self.current > PLAIN_ENCODING

    def is_gzip(self):
        return self.current == GZIP_ENCODING

    def is_deflate(self):
        return self.current == DEFLATE_ENCODING

    def is_compressed(self):
        return self.current > CHUNKED_ENCODING

    def on_data(self):
        self.owner.on_data_http(self, self.parser)

    def _flush_plain(self, callback = None):
        if not callback: return
        self.send_plain("", callback = callback)

    def _flush_chunked(self, callback = None):
        self.send_plain("0\r\n\r\n", callback = callback)

    def _flush_gzip(self, callback = None):
        # in case the gzip structure has not been initialized
        # (no data sent) no need to run the flushing of the
        # gzip data, so only the chunked part is flushed
        if not self.gzip:
            self._flush_chunked(callback = callback)
            return

        # flushes the internal zlib buffers to be able to retrieve
        # the data pending to be sent to the client and then sends
        # it using the chunked encoding strategy
        data_c = self.gzip.flush(zlib.Z_FINISH)
        self.send_chunked(data_c)

        # resets the gzip values to the original ones so that new
        # requests will starts the information from the beginning
        self.gzip = None

        # runs the flush operation for the underlying chunked encoding
        # layer so that the client is correctly notified about the
        # end of the current request (normal operation)
        self._flush_chunked(callback = callback)

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

class HTTPServer(netius.StreamServer):
    """
    Base class for serving of the http protocol, should contain
    the basic utilities for handling an http request including
    headers and read of data.
    """

    def __init__(self, encoding = "plain", *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.encoding_s = encoding

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.StreamServer.on_serve(self)
        if self.env: self.encoding_s = self.get_env("ENCODING", self.encoding_s)
        self.encoding = ENCODING_MAP.get(self.encoding_s, PLAIN_ENCODING)
        self.info("Starting HTTP server with '%s' encoding ..." % self.encoding_s)

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding
        )

    def on_data_http(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_request(connection, parser)
        connection.resolve_encoding(parser)

    def authorize(self, connection, parser, auth = None, **kwargs):
        # determines the proper authorization method to be used
        # taking into account either the provided method or the
        # default one in case none is provided
        auth = auth or netius.PasswdAuth
        if hasattr(auth, "auth"): auth_method = auth.auth
        else: auth_method = auth.auth_i
        if hasattr(auth, "is_simple"): is_simple = auth.is_simple()
        else: is_simple = auth.is_simple_i()

        # constructs a dictionary that contains extra information
        # about the current connection/request that may be used
        # to further determine if the request is authorized
        kwargs = dict(
            connection = connection,
            parser = parser,
            host = connection.address[0],
            port = connection.address[1],
            headers = parser.headers
        )

        # in case the current authentication method is considered
        # simples (no "classic" username and password) the named
        # arguments dictionary is provided as the only input
        if is_simple: return auth_method(**kwargs)

        # retrieves the authorization tuple (username and password)
        # using the current parser and verifies if at least one of
        # them is defined in case it's not returns an invalid result
        username, password = self._authorization(parser)
        if not username and not password: return False

        # uses the provided username and password to run the authentication
        # process using the method associated with the authorization structure
        return auth_method(username, password, **kwargs)

    def _apply_all(self, parser, connection, headers, upper = True):
        if upper: self._headers_upper(headers)
        self._apply_base(headers)
        self._apply_parser(parser, headers)
        self._apply_connection(connection, headers)

    def _apply_base(self, headers, replace = False):
        for key, value in BASE_HEADERS.items():
            if not replace and key in headers: continue
            headers[key] = value

    def _apply_parser(self, parser, headers):
        if "Connection" in headers: return
        if parser.keep_alive: headers["Connection"] = "keep-alive"
        else: headers["Connection"] = "close"

    def _apply_connection(self, connection, headers):
        is_chunked = connection.is_chunked()
        is_gzip = connection.is_gzip()
        is_deflate = connection.is_deflate()

        if is_chunked:
            headers["Transfer-Encoding"] = "chunked"
            if "Content-Length" in headers: del headers["Content-Length"]

        if is_gzip: headers["Content-Encoding"] = "gzip"

        if is_deflate: headers["Content-Encoding"] = "deflate"

    def _headers_upper(self, headers):
        for key, value in headers.items():
            key_u = netius.common.header_up(key)
            del headers[key]
            headers[key_u] = value

    def _authorization(self, parser):
        # retrieves the headers from the parser structure and uses
        # them to retrieve the authorization header value returning
        # an invalid value in case no header is defined
        headers = parser.headers
        authorization = headers.get("authorization", None)
        if not authorization: return None, None

        # splits the authorization token between the realm and the
        # token value (decoding it afterwards) and then unpacks the
        # token into the username and password components (for validation)
        _realm, token = authorization.split(" ", 1)
        token = base64.b64decode(token)
        token = netius.legacy.str(token)
        username, password = token.split(":", 1)

        # retrieves the "final" packed result containing both the username
        # and the password associated with the authorization
        return username, password

    def _log_request(self, connection, parser):
        # unpacks the various values that are going to be part of
        # the log message to be printed in the debug
        is_tuple = type(connection.address) in (list, tuple)
        ip_address = connection.address[0] if is_tuple else connection.address
        method = parser.method.upper()
        path = parser.get_path()
        version_s = parser.version_s

        # creates the message from the complete set of components
        # that are part of the current message and then prints a
        # debug message with the contents of it
        message = "%s %s %s @ %s" % (method, path, version_s, ip_address)
        self.debug(message)
