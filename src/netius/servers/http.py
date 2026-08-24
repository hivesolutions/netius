#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

"""netius.servers.http

Base HTTP/1.x server built on the Netius stream infra-structure. Wraps the
common HTTP parser to read requests and provides the utilities for building
and sending responses, including the management of the various transfer
encodings (eg: plain, chunked, gzip and deflate). Connections track their
own encoding state and optional gzip stream, and a base set of headers is
applied to every response. Meant to be used as a foundation for concrete
HTTP based servers.
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import zlib
import base64
import datetime
import traceback
import contextlib

import netius.common

from netius.common import (
    LINE_LIMIT,
    HEADERS_LIMIT,
    HEADERS_COUNT,
    PLAIN_ENCODING,
    CHUNKED_ENCODING,
    GZIP_ENCODING,
    DEFLATE_ENCODING,
    AUTO_ENCODING,
)

Z_PARTIAL_FLUSH = 1
""" The zlib constant value representing the partial flush
of the current zlib stream, this value has to be defined
locally as it is not defines under the zlib module """

GZIP_LEVEL = 6
""" The default compression level to be used for the gzip
and deflate encodings, this is the same value used by the
zlib module and provides a reasonable balance between the
compression ratio and the CPU usage """

COMPRESS_FLUSH = 16384
""" The amount of raw data (in bytes) that is accumulated in the
compressor before a partial flush is performed, avoiding one flush
per payload chunk which would degrade the compression ratio, set it
to zero to flush every chunk (required for latency sensitive streams
that are served under an explicit compressed encoding) """

REQUESTS_LIMIT = 1000
""" The maximum number of requests that may be served by a single
connection, once this value is reached the connection stops being
a persistent one, avoiding it from being held open forever, set it
to zero to remove the bound (not recommended) """

EMPTY_CODES = (204, 304)
""" The set of HTTP status codes that according to the HTTP
specification must not include a message body in the response
(No Content and Not Modified), used to decide when to omit
the content length header and body from the response """

COMPRESS_MIN = 1024
""" The minimum size (in bytes) of a payload for the compression
of it to be considered, smaller payloads would most likely grow
in size once the framing overhead is taken into account """

COMPRESS_MAX = 5242880
""" The maximum size (in bytes) of a payload for the compression
of it to be considered, this should ensure proper resource usage
avoiding extreme high levels of processor usage for large payloads """

COMPRESS_TYPES = [
    "text/",
    "+json",
    "+xml",
    "application/json",
    "application/javascript",
    "application/x-javascript",
    "application/xml",
    "application/wasm",
    "image/x-icon",
]
""" The sequence of media types considered to be compressible, the
values ending with a slash are matched as a prefix (eg: text/) and
the ones starting with a plus as a structured syntax suffix (eg:
+json), the remaining ones are matched exactly """

COMPRESS_DENY = (
    "application/gzip",
    "application/zip",
    "application/zstd",
    "application/x-7z-compressed",
    "application/x-bzip2",
    "application/x-gzip",
    "application/x-rar-compressed",
    "application/x-xz",
    "text/event-stream",
)
""" The sequence of media types that must never be compressed, either
because they are already stored in a compressed format or because they
are latency sensitive streams (eg: server sent events), this takes
priority over the allowed types (safety net for extended type lists) """

COMPRESS_ENCODINGS = ["gzip", "deflate"]
""" The sequence of content codings to be used in the compression
of the responses, defined in descending order of preference so that
the first coding also accepted by the client is the one used """

ENCODING_MAP = dict(
    plain=PLAIN_ENCODING,
    chunked=CHUNKED_ENCODING,
    gzip=GZIP_ENCODING,
    deflate=DEFLATE_ENCODING,
    auto=AUTO_ENCODING,
)
""" The map associating the various types of encoding with
the corresponding integer value for each of them this is used
in the initial construction of the server """

CODECS = dict()
""" The registry that associates the name of each of the supported
content codings with the information required to build a compressor
for it, this is the structure that drives the negotiation """


def register_codec(name, wbits, encoding, factory=zlib.compressobj):
    """
    Registers a new content coding in the codec registry so that it
    becomes eligible for the encoding negotiation, note that the name
    is also added to the sequence of codings that the wildcard value
    of the accept encoding header expands into.

    :type name: String
    :param name: The name of the content coding as it's going to be
    used in the `Content-Encoding` header (eg: gzip).
    :type wbits: int
    :param wbits: The window bits value to be used in the construction
    of the compressor, controls the container of the stream.
    :type encoding: int
    :param encoding: The value of the encoding ladder that is going to
    be used whenever this coding is selected.
    :type factory: Function
    :param factory: The factory method to be used in the construction
    of the compressor object for the coding.
    """

    CODECS[name] = dict(name=name, wbits=wbits, encoding=encoding, factory=factory)
    if not name in netius.common.CODINGS:
        netius.common.CODINGS.append(name)


register_codec("gzip", zlib.MAX_WBITS | 16, GZIP_ENCODING)
register_codec("deflate", -zlib.MAX_WBITS, DEFLATE_ENCODING)


class HTTPConnection(netius.Connection):

    def __init__(self, encoding=PLAIN_ENCODING, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.encoding = encoding
        self.current = self.base_encoding()
        self.encoding_c = None
        self.encodings_a = None
        self.dynamic = None
        self.parser = None
        self.legacy = True
        self.requests = 0
        self.gzip_m = dict()
        self.gzip_l = dict()

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open():
            return
        self.parser = netius.common.HTTPParser(
            self,
            type=netius.common.REQUEST,
            store=True,
            line_limit=self.owner.line_limit,
            headers_limit=self.owner.headers_limit,
            headers_count=self.owner.headers_count,
        )
        self.parser.bind("on_data", self.on_data)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed():
            return
        if self.parser:
            self.parser.destroy()
        if self.gzip_m:
            self._close_gzip(safe=True)

    def info_dict(self, full=False):
        info = netius.Connection.info_dict(self, full=full)
        info.update(
            encoding=self.encoding, current=self.current, encoding_c=self.encoding_c
        )
        if full:
            info.update(parser=self.parser.info_dict())
        return info

    def flush(self, stream=None, callback=None):
        encoding = self.encoding_w()

        if encoding == DEFLATE_ENCODING:
            self._flush_gzip(stream=stream, callback=callback)
        elif encoding == GZIP_ENCODING:
            self._flush_gzip(stream=stream, callback=callback)
        elif encoding == CHUNKED_ENCODING:
            self._flush_chunked(stream=stream, callback=callback)
        elif encoding == PLAIN_ENCODING:
            self._flush_plain(stream=stream, callback=callback)

        self.set_base()

        self.owner.on_flush_http(
            self.connection_ctx, self.parser_ctx, encoding=encoding
        )

    def flush_s(self, stream=None, callback=None):
        return self.flush(stream=stream, callback=callback)

    def send_base(self, data, stream=None, final=True, delay=True, callback=None):
        data = netius.legacy.bytes(data) if data else data
        encoding = self.encoding_w()

        if encoding == PLAIN_ENCODING:
            return self.send_plain(
                data, stream=stream, final=final, delay=delay, callback=callback
            )
        elif encoding == CHUNKED_ENCODING:
            return self.send_chunked(
                data, stream=stream, final=final, delay=delay, callback=callback
            )
        elif encoding == GZIP_ENCODING:
            return self.send_gzip(
                data, stream=stream, final=final, delay=delay, callback=callback
            )
        elif encoding == DEFLATE_ENCODING:
            return self.send_gzip(
                data, stream=stream, final=final, delay=delay, callback=callback
            )

    def send_plain(self, data, stream=None, final=True, delay=True, callback=None):
        return self.send(data, delay=delay, callback=callback)

    def send_chunked(self, data, stream=None, final=True, delay=True, callback=None):
        # in case there's no valid data to be sent uses the plain
        # send method to send the empty string and returns immediately
        # to the caller method, to avoid any problems
        if not data:
            return self.send_plain(
                data, stream=stream, final=final, delay=delay, callback=callback
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
            buffer_s, stream=stream, final=final, delay=delay, callback=callback
        )

    def send_gzip(
        self, data, stream=None, final=True, delay=True, callback=None, level=None
    ):
        # verifies if the provided data buffer is valid and in
        # in case it's not propagates the sending to the upper
        # layer (chunked sending) for proper processing
        if not data:
            return self.send_chunked(
                data, stream=stream, final=final, delay=delay, callback=callback
            )

        # tries to retrieve the gzip object for the current stream
        # in case it's a new connection one will be created with the
        # appropriate compression level (as expected)
        level = self.owner.compress_level if level == None else level
        gzip = self._get_gzip(stream, level=level)

        # compresses the provided data string and accumulates the amount
        # of raw data fed to the compressor since the last flush, so that
        # the partial flush is only performed once a reasonable amount of
        # data is pending, otherwise one back-end chunk would force one
        # flush degrading the compression ratio
        data_c = gzip.compress(data)
        self.gzip_l[stream] = self.gzip_l.get(stream, 0) + len(data)
        if self.gzip_l[stream] >= self.owner.compress_flush:
            data_c += gzip.flush(Z_PARTIAL_FLUSH)
            self.gzip_l[stream] = 0

        # sends the compressed data to the client endpoint setting
        # the correct callback values as requested
        return self.send_chunked(
            data_c, stream=stream, final=final, delay=delay, callback=callback
        )

    def send_response(
        self,
        data=None,
        headers=None,
        version=None,
        code=200,
        code_s=None,
        apply=False,
        stream=None,
        final=True,
        flush=True,
        delay=True,
        callback=None,
    ):
        # retrieves the various parts that define the response
        # and runs a series of normalization processes to retrieve
        # the relevant information of the data to be sent to client
        data = data or b""
        data = netius.legacy.bytes(data)
        headers = headers or dict()
        data_l = len(data) if data else 0
        is_empty = code in EMPTY_CODES and data_l == 0

        # in case the response is an informational or a no content one it may
        # never carry a payload nor announce a length for it, as the message
        # is terminated by the first empty line after the headers section
        if code < 200 or code == 204:
            data = b""
            data_l = 0
            is_empty = True
            if "content-length" in headers:
                del headers["content-length"]

        # runs a series of verifications taking into account the type
        # of the method defined in the current request, for instance if
        # the current request is a HEAD one then no data is sent (as expected)
        if self.parser_ctx.method and self.parser_ctx.method.upper() == "HEAD":
            data = b""

        # verifies if the content length header is currently present
        # in the provided headers and in case it's not inserts it
        if not "content-length" in headers and not is_empty:
            headers["content-length"] = str(data_l)

        # in case the apply flag is set the apply all operation is performed
        # so that a series of headers are applied to the current context
        # (things like the name of the server connection, etc)
        if apply:
            self.owner._apply_all(self.parser, self, headers)

        # sends the initial headers data (including status line), this should
        # trigger the initial data sent to the peer/client
        count = self.send_header(
            headers=headers, version=version, code=code, code_s=code_s, stream=stream
        )

        # sends the part/payload information (data) to the client and optionally
        # flushes the current internal buffers to enforce sending of the value
        count += self.send_part(
            data,
            stream=stream,
            final=final,
            flush=flush,
            delay=delay,
            callback=callback,
        )
        return count

    def send_header(
        self,
        headers=None,
        version=None,
        code=200,
        code_s=None,
        stream=None,
        final=False,
        delay=True,
        callback=None,
    ):
        # retrieves the various parts that define the response
        # and runs a series of normalization processes to retrieve
        # the relevant information of the data to be sent to client
        headers = headers or dict()
        version = version or "HTTP/1.1"
        code_s = code_s or netius.common.CODE_STRINGS.get(code, None)

        # creates the buffer list that is going to hold the complete set of
        # lines for the headers and then appends the complete set of headers
        # according to the previous construction
        buffer = []
        buffer.append("%s %d %s\r\n" % (version, code, code_s))
        for key, value in netius.legacy.iteritems(headers):
            key = netius.common.header_up(key)
            if not isinstance(value, list):
                value = (value,)
            for _value in value:
                buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        # ensures that no carriage return or line feed has been injected into
        # any of the header values, each of the lines accounts for exactly one
        # of these characters so any extra one splits the response
        if not buffer_data.count("\r") == len(buffer) or not buffer_data.count(
            "\n"
        ) == len(buffer):
            raise netius.GeneratorError("Invalid header value")

        # sends the buffer data to the connection peer so that it gets notified
        # about the headers for the current communication/message
        count = self.send_plain(
            buffer_data, stream=stream, delay=delay, callback=callback
        )

        # "notifies" the owner of the connection that the headers have been
        # sent all the HTTP header information should be present
        self.owner.on_send_http(
            self.connection_ctx,
            self.parser_ctx,
            headers=headers,
            version=version,
            code=code,
            code_s=code_s,
        )

        # returns the final number of bytes that have been sent during the current
        # operation of sending headers to the other peer
        return count

    def send_part(
        self, data, stream=None, final=True, flush=False, delay=True, callback=None
    ):
        if flush:
            count = self.send_base(data)
            self.flush(callback=callback)
        else:
            count = self.send_base(data, delay=delay, callback=callback)
        return count

    def parse(self, data):
        try:
            return self.parser.parse(data)
        except netius.ParserError as error:
            self.send_response(code=error.code, apply=True)

    def resolve_encoding(self, parser):
        # in case the "target" encoding is the plain one nothing
        # is required to be done as this is allowed by any kind
        # of HTTP compliant connection (returns immediately)
        if self.encoding == PLAIN_ENCODING:
            self.current = PLAIN_ENCODING

        # if the target encoding is chunked must verify if the
        # type of HTTP connection in question is 1.1 or above
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

        # if the target encoding is the automatic one the effective
        # encoding is only resolved once the payload is known, so only
        # the codings accepted by the client are recorded, note that the
        # per response state is reset at the boundary of each response
        elif self.encoding == AUTO_ENCODING:
            self.encodings_a = parser.get_encodings()

    def base_encoding(self):
        """
        Resolves the base value of the encoding ladder for the connection,
        this is the value that the current encoding is taken back to at the
        boundaries of each response.

        Note that the automatic encoding is a target and not a valid rung
        of the ladder, so it's resolved into the plain encoding instead.

        :rtype: int
        :return: The base encoding value for the current connection.
        """

        if self.encoding == AUTO_ENCODING:
            return PLAIN_ENCODING
        return self.encoding

    def encoding_w(self):
        """
        Resolves the encoding that is effectively going to be used in the
        wire for the payload of the current response, taking into account
        the per response dynamic (no re-encoding) state and falling back
        to the server wide one whenever it has not been resolved.

        :rtype: int
        :return: The encoding to be used in the sending of the payload.
        """

        if self.is_dynamic():
            return min(self.current, CHUNKED_ENCODING)
        return self.current

    def encoding_name(self):
        """
        Obtains the name of the content coding that is going to be applied
        to the payload of the current response, an invalid value is returned
        in case no compression is going to be performed.

        :rtype: String
        :return: The name of the content coding in use (eg: gzip).
        """

        encoding = self.encoding_w()
        if encoding <= CHUNKED_ENCODING:
            return None
        if self.encoding_c:
            return self.encoding_c
        return "deflate" if encoding == DEFLATE_ENCODING else "gzip"

    def set_encoding(self, encoding):
        self.current = encoding

    def set_base(self):
        self.current = self.base_encoding()
        self.encoding_c = None
        self.encodings_a = None
        self.dynamic = None

    def set_uncompressed(self):
        if self.current >= CHUNKED_ENCODING:
            self.current = CHUNKED_ENCODING
        else:
            self.current = PLAIN_ENCODING

    def set_plain(self):
        self.set_encoding(PLAIN_ENCODING)

    def set_chunked(self):
        self.set_encoding(CHUNKED_ENCODING)

    def set_gzip(self):
        self.set_encoding(GZIP_ENCODING)

    def set_deflate(self):
        self.set_encoding(DEFLATE_ENCODING)

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

    def is_dynamic(self):
        if self.dynamic == None:
            return self.owner.dynamic
        return self.dynamic

    def is_flushed(self):
        return self.current > PLAIN_ENCODING

    def is_measurable(self, strict=True):
        encoding = self.encoding_w()
        if encoding > CHUNKED_ENCODING:
            return False
        if strict and encoding > PLAIN_ENCODING:
            return False
        return True

    def on_data(self):
        # increments the number of requests that have been served by the
        # current connection and in case the bound has been reached the
        # connection stops being a persistent one (gets closed afterwards)
        self.requests += 1
        if self.owner.requests_limit and self.requests >= self.owner.requests_limit:
            self.parser.keep_alive = False

        self.owner.on_data_http(self.connection_ctx, self.parser_ctx)

    @contextlib.contextmanager
    def ctx_request(self, args=None, kwargs=None):
        yield

    @property
    def connection_ctx(self):
        return self

    @property
    def parser_ctx(self):
        return self.parser

    def _flush_plain(self, stream=None, callback=None):
        if not callback:
            return
        self.send_plain(b"", stream=stream, callback=callback)

    def _flush_chunked(self, stream=None, callback=None):
        self.send_plain(b"0\r\n\r\n", stream=stream, callback=callback)

    def _flush_gzip(self, stream=None, callback=None):
        # tries to retrieve a possible gzip object for the current
        # stream, note that no gzip object is going to be created
        # in case there's none defined for the current stream
        gzip = self._get_gzip(stream, ensure=False)

        # in case the gzip structure has not been initialized
        # (no data sent) no need to run the flushing of the
        # gzip data, so only the chunked part is flushed
        if not gzip:
            self._flush_chunked(stream=stream, callback=callback)
            return

        # flushes the internal zlib buffers to be able to retrieve
        # the data pending to be sent to the client and then sends
        # it using the chunked encoding strategy
        data_c = gzip.flush(zlib.Z_FINISH)
        self.send_chunked(data_c, stream=stream, final=False)

        # resets the gzip values to the original ones so that new
        # requests will starts the information from the beginning
        self._unset_gzip(stream)

        # runs the flush operation for the underlying chunked encoding
        # layer so that the client is correctly notified about the
        # end of the current request (normal operation)
        self._flush_chunked(stream=stream, callback=callback)

    def _get_gzip(self, stream, level=GZIP_LEVEL, ensure=True):
        # tries to retrieve the proper gzip object for the requested
        # stream and in case there's one or if the ensure flag is set
        # the retrieved value is returned to the caller method
        gzip = self.gzip_m.get(stream, None)
        if gzip or not ensure:
            return gzip

        # in case this is the first sending a new compress object is
        # created with the requested compress level, resolving both the
        # factory and the window bits from the codec registry using the
        # name of the content coding currently in use
        codec = CODECS.get(self.encoding_name(), CODECS["gzip"])
        gzip = codec["factory"](level, zlib.DEFLATED, codec["wbits"])

        # updates the gzip objects map with the gzip object that has
        # just been created for the target stream
        self.gzip_m[stream] = gzip
        return gzip

    def _set_gzip(self, stream, gzip):
        self.gzip_m[stream] = gzip

    def _unset_gzip(self, stream):
        if stream in self.gzip_m:
            del self.gzip_m[stream]
        if stream in self.gzip_l:
            del self.gzip_l[stream]

    def _close_gzip(self, safe=True):
        # in case the gzip object is not defined returns the control
        # to the caller method immediately (nothing to be done)
        if not self.gzip_m:
            return

        # saves the current gzip object map locally (releasing reference)
        # and then recreates a new empty dictionary on the other object
        gzip_m = self.gzip_m
        self.gzip_m = dict()
        self.gzip_l = dict()

        # iterates over the complete set of gzip object to run the flush
        # operation over each of them, as expected for proper and final
        # memory release, note that an exception may be raised in the case
        # of a duplicated flush operation
        for gzip in gzip_m.values():
            try:
                # runs the flush operation for the the final finish stage
                # (note that an exception may be raised)
                gzip.flush(zlib.Z_FINISH)
            except Exception:
                # in case the safe flag is not set re-raises the exception
                # to the caller stack (as expected by the callers)
                if not safe:
                    raise


class HTTPServer(netius.StreamServer):
    """
    Base class for serving of the HTTP protocol, should contain
    the basic utilities for handling an HTTP request including
    headers and read of data.
    """

    BASE_HEADERS = {"Server": netius.IDENTIFIER}
    """ The map containing the complete set of headers
    that are meant to be applied to all the responses """

    def __init__(
        self,
        encoding="plain",
        common_log=None,
        compress_min=COMPRESS_MIN,
        compress_max=COMPRESS_MAX,
        compress_types=COMPRESS_TYPES,
        compress_encodings=COMPRESS_ENCODINGS,
        compress_level=GZIP_LEVEL,
        compress_flush=COMPRESS_FLUSH,
        compress_vary=True,
        line_limit=LINE_LIMIT,
        headers_limit=HEADERS_LIMIT,
        headers_count=HEADERS_COUNT,
        requests_limit=REQUESTS_LIMIT,
        *args,
        **kwargs
    ):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.encoding_s = encoding
        self.encoding = ENCODING_MAP.get(encoding, PLAIN_ENCODING)
        self.common_log = common_log
        self.compress_min = compress_min
        self.compress_max = compress_max
        self.compress_types = compress_types
        self.compress_encodings = compress_encodings
        self.compress_level = compress_level
        self.compress_flush = compress_flush
        self.compress_vary = compress_vary
        self.line_limit = line_limit
        self.headers_limit = headers_limit
        self.headers_count = headers_count
        self.requests_limit = requests_limit
        self.dynamic = False
        self.common_file = None

    @classmethod
    def build_data(
        cls,
        text,
        url=None,
        trace=False,
        style=True,
        style_urls=[],
        encode=True,
        encoding="utf-8",
    ):
        if url:
            return cls.build_iframe(
                text, url, style=style, encode=encode, encoding=encoding
            )
        else:
            return cls.build_text(
                text, trace=trace, style=style, encode=encode, encoding=encoding
            )

    @classmethod
    def build_text(
        cls, text, trace=False, style=True, style_urls=[], encode=True, encoding="utf-8"
    ):
        data = "".join(
            cls._gen_text(text, trace=trace, style=style, style_urls=style_urls)
        )
        if encode:
            data = netius.legacy.bytes(data, encoding=encoding, force=True)
        return data

    @classmethod
    def build_iframe(
        cls, text, url, style=True, style_urls=[], encode=True, encoding="utf-8"
    ):
        data = "".join(cls._gen_iframe(text, url, style=style, style_urls=style_urls))
        if encode:
            data = netius.legacy.bytes(data, encoding=encoding, force=True)
        return data

    @classmethod
    def _gen_text(cls, text, trace=False, style=True, style_urls=[]):
        for value in cls._gen_header(text, style=style, style_urls=style_urls):
            yield value

        yield "<body>"
        yield "<h1>%s</h1>" % text
        if trace:
            lines = traceback.format_exc().splitlines()
            yield "<hr/>"
            yield '<div class="traceback">'
            for line in lines:
                yield "<div>%s</div>" % line
            yield "</div>"
        yield "<hr/>"
        yield "<span>"
        yield netius.IDENTIFIER
        yield "</span>"
        yield "</body>"

        for value in cls._gen_footer():
            yield value

    @classmethod
    def _gen_iframe(cls, text, url, style=True, style_urls=[]):
        for value in cls._gen_header(text, style=style, style_urls=style_urls):
            yield value

        yield "<body>"
        yield '<iframe src="%s"></iframe>' % url
        yield "</body>"

        for value in cls._gen_footer():
            yield value

    @classmethod
    def _gen_header(cls, title, meta=True, style=True, style_urls=[]):
        yield "<!DOCTYPE html>"
        yield "<html>"
        yield "<head>"
        if meta:
            yield '<meta charset="utf-8" />'
            yield '<meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1, minimum-scale=1, maximum-scale=1" />'
        yield "<title>%s</title>" % title
        if style:
            for value in cls._gen_style():
                yield value
            for style_url in style_urls:
                yield '<link rel="stylesheet" type="text/css" href="%s" />' % style_url
        yield "</head>"

    @classmethod
    def _gen_footer(cls):
        yield "</html>"

    @classmethod
    def _gen_style(cls):
        yield netius.common.BASE_STYLE

    def cleanup(self):
        netius.StreamServer.cleanup(self)

        if self.common_file:
            self.common_file.close()

    def info_dict(self, full=False):
        info = netius.StreamServer.info_dict(self, full=full)
        info.update(encoding_s=self.encoding_s)
        return info

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.StreamServer.on_serve(self)
        if self.env:
            self.encoding_s = self.get_env("ENCODING", self.encoding_s)
        if self.env:
            self.common_log = self.get_env("COMMON_LOG", self.common_log)
        if self.env:
            self.compress_min = self.get_env(
                "COMPRESS_MIN", self.compress_min, cast=int
            )
        if self.env:
            self.compress_max = self.get_env(
                "COMPRESS_MAX",
                self.get_env("COMPRESSED_LIMIT", self.compress_max, cast=int),
                cast=int,
            )
        if self.env:
            self.compress_types = self.get_env(
                "COMPRESS_TYPES", self.compress_types, cast=list
            )
        if self.env:
            self.compress_encodings = self.get_env(
                "COMPRESS_ENCODINGS", self.compress_encodings, cast=list
            )
        if self.env:
            self.compress_level = self.get_env(
                "COMPRESS_LEVEL", self.compress_level, cast=int
            )
        if self.env:
            self.compress_flush = self.get_env(
                "COMPRESS_FLUSH", self.compress_flush, cast=int
            )
        if self.env:
            self.compress_vary = self.get_env(
                "COMPRESS_VARY", self.compress_vary, cast=bool
            )
        if self.env:
            self.line_limit = self.get_env("LINE_LIMIT", self.line_limit, cast=int)
        if self.env:
            self.headers_limit = self.get_env(
                "HEADERS_LIMIT", self.headers_limit, cast=int
            )
        if self.env:
            self.headers_count = self.get_env(
                "HEADERS_COUNT", self.headers_count, cast=int
            )
        if self.env:
            self.requests_limit = self.get_env(
                "REQUESTS_LIMIT", self.requests_limit, cast=int
            )
        if self.common_log:
            self.common_file = open(self.common_log, "wb+")
        self.encoding = ENCODING_MAP.get(self.encoding_s, PLAIN_ENCODING)
        self.info("Starting HTTP server with '%s' encoding ...", self.encoding_s)
        if self.is_auto():
            self.info(
                "Compressing responses between %d and %d bytes ...",
                self.compress_min,
                self.compress_max,
            )
        if self.common_log:
            self.info("Logging with Common Log Format to '%s' ...", self.common_log)

    def build_connection(self, socket, address, ssl=False):
        return HTTPConnection(
            owner=self, socket=socket, address=address, ssl=ssl, encoding=self.encoding
        )

    def on_data_http(self, connection, parser):
        is_debug = self.is_debug()
        if is_debug:
            self._log_request(connection, parser)
        connection.resolve_encoding(parser)

    def on_send_http(
        self, connection, parser, headers=None, version=None, code=200, code_s=None
    ):
        if self.common_file:
            self._log_request(
                connection,
                parser,
                headers=headers,
                version=version,
                code=code,
                code_s=code_s,
                output=self._write_common,
                mode="common",
            )

    def on_flush_http(self, connection, parser, encoding=None):
        connection.debug(
            "Connection '%s' %s from '%s' flushed",
            connection.id,
            connection.address,
            self.name,
        )

    def is_auto(self):
        return self.encoding == AUTO_ENCODING

    def is_compressible(self, content_type):
        """
        Determines if a payload of the provided media type is considered
        to be compressible, meaning that compressing it is expected to
        provide a relevant gain in the size of the payload.

        :type content_type: String
        :param content_type: The value of the content type header of the
        payload that is going to be verified (parameters allowed).
        :rtype: bool
        :return: If the provided media type is considered compressible.
        """

        # normalizes the media type by removing the possible parameters
        # (eg: charset) from it and lower casing the remaining value,
        # an unset media type is never considered compressible
        if not content_type:
            return False
        content_type = content_type.split(";", 1)[0].strip().lower()
        if not content_type:
            return False

        # verifies if the media type has been explicitly denied, this is
        # the case for the formats that are already compressed and that
        # would only waste processor time (takes precedence)
        if content_type in COMPRESS_DENY:
            return False

        # matches the media type against the complete set of the allowed
        # ones, supporting both the prefix (eg: text/) and the structured
        # syntax suffix (eg: +json) notations plus the exact match
        for value in self.compress_types:
            if value.endswith("/") and content_type.startswith(value):
                return True
            if value.startswith("+") and content_type.endswith(value):
                return True
            if content_type == value:
                return True

        return False

    def authorize(self, connection, parser, auth=None, **kwargs):
        # determines the proper authorization method to be used
        # taking into account either the provided method or the
        # default one in case none is provided
        auth = auth or netius.PasswdAuth
        if hasattr(auth, "auth"):
            auth_method = auth.auth
        else:
            auth_method = auth.auth_i
        if hasattr(auth, "is_simple"):
            is_simple = auth.is_simple()
        else:
            is_simple = auth.is_simple_i()

        # constructs a dictionary that contains extra information
        # about the current connection/request that may be used
        # to further determine if the request is authorized
        kwargs = dict(
            connection=connection,
            parser=parser,
            host=connection.address[0],
            port=connection.address[1],
            headers=parser.headers,
        )

        # in case the current authentication method is considered
        # simples (no "classic" username and password) the named
        # arguments dictionary is provided as the only input
        if is_simple:
            return auth_method(**kwargs)

        # retrieves the authorization tuple (username and password)
        # using the current parser and verifies if at least one of
        # them is defined in case it's not returns an invalid result
        username, password = self._authorization(parser)
        if not username and not password:
            return False

        # uses the provided username and password to run the authentication
        # process using the method associated with the authorization structure
        return auth_method(username, password, **kwargs)

    def _apply_all(
        self, parser, connection, headers, upper=True, normalize=False, replace=False
    ):
        if upper:
            self._headers_upper(headers)
        if normalize:
            self._headers_normalize(headers)
        self._apply_base(headers, replace=replace)
        self._apply_parser(parser, headers, replace=replace)
        self._apply_connection(connection, headers)

    def _apply_base(self, headers, replace=False):
        cls = self.__class__
        for key, value in netius.legacy.iteritems(cls.BASE_HEADERS):
            if not replace and key in headers:
                continue
            headers[key] = value

    def _apply_parser(self, parser, headers, replace=False):
        if not replace and "Connection" in headers:
            return
        if parser.keep_alive:
            headers["Connection"] = "keep-alive"
        else:
            headers["Connection"] = "close"

    def _apply_connection(self, connection, headers, strict=True):
        # a payload that already carries a coding must not be encoded once
        # again, as the coding announced for it would no longer describe the
        # complete set of transformations applied to the payload
        content_encoding = headers.get("Content-Encoding", None)
        if isinstance(content_encoding, (list, tuple)):
            content_encoding = ", ".join(content_encoding)
        if content_encoding and not content_encoding.strip().lower() == "identity":
            connection.set_uncompressed()

        # resolves the encoding that is effectively going to be used in
        # the wire, so that the announced encoding is the one applied to
        # the payload and never the (unclamped) target one
        encoding = connection.encoding_w()
        is_chunked = encoding > PLAIN_ENCODING
        is_compressed = encoding > CHUNKED_ENCODING
        is_measurable = connection.is_measurable(strict=strict)
        has_length = "Content-Length" in headers
        has_ranges = "Accept-Ranges" in headers
        has_encoding = "Content-Encoding" in headers

        if is_chunked:
            headers["Transfer-Encoding"] = "chunked"
        if is_compressed and not has_encoding:
            headers["Content-Encoding"] = connection.encoding_name()
            self._apply_weak(headers, "Etag")

        if not is_measurable and has_length:
            del headers["Content-Length"]
        if is_compressed and has_ranges:
            del headers["Accept-Ranges"]

        # in case the response was eligible for compression the payload
        # depends on the codings accepted by the client, so the proper
        # vary header must be announced (even if no compression was done)
        if self.compress_vary and not connection.encodings_a == None:
            self._apply_vary(headers, "Accept-Encoding")

    def _apply_weak(self, headers, name):
        # retrieves the currently defined entity tag normalizing it into a
        # single string, as repeated headers are stored as a sequence
        etag = headers.get(name, None)
        if isinstance(etag, (list, tuple)):
            etag = etag[-1] if etag else None
        if not etag:
            return

        # a payload that has been encoded by the server is no longer the
        # octet sequence that a strong entity tag identifies, so the tag
        # must be weakened as defined by RFC 9110
        etag = etag.strip()
        if etag.startswith("W/"):
            return
        headers[name] = "W/" + etag

    def _apply_vary(self, headers, value):
        # retrieves the currently defined vary value normalizing it into
        # a single string, as repeated headers are stored as a sequence
        vary = headers.get("Vary", "")
        if isinstance(vary, (list, tuple)):
            vary = ", ".join(vary)

        # verifies if the field name is already part of the vary value
        # and if that's the case returns immediately (nothing to be done)
        tokens = [token.strip().lower() for token in vary.split(",")]
        if value.lower() in tokens:
            return

        # appends the field name to the base value or creates a new one
        # in case no vary header was defined by the back-end
        if vary:
            vary += ", "
        vary += value
        headers["Vary"] = vary

    def _headers_upper(self, headers):
        for key, value in netius.legacy.items(headers):
            key_u = netius.common.header_up(key)
            del headers[key]
            headers[key_u] = value

    def _headers_normalize(self, headers):
        for key, value in netius.legacy.items(headers):
            if not type(value) in (list, tuple):
                continue
            headers[key] = ";".join(value)

    def _authorization(self, parser):
        # retrieves the headers from the parser structure and uses
        # them to retrieve the authorization header value returning
        # an invalid value in case no header is defined
        headers = parser.headers
        authorization = headers.get("authorization", None)
        if not authorization:
            return None, None

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

    def _write_common(self, message, encoding="utf-8"):
        message = netius.legacy.bytes(message, encoding=encoding, force=True)
        self.common_file.write(message + b"\n")
        self.common_file.flush()

    def _log_request(self, connection, parser, *args, **kwargs):
        mode = kwargs.pop("mode", "basic")
        method = getattr(self, "_log_request_" + mode)
        return method(connection, parser, *args, **kwargs)

    def _log_request_basic(self, connection, parser, output=None):
        # runs the defaulting operation on the logger output
        # method so that the default logger output is used instead
        output = output or connection.debug

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
        output(message)

    def _log_request_common(
        self,
        connection,
        parser,
        headers=None,
        version=None,
        code=200,
        code_s=None,
        size_s=None,
        username="frank",
        output=None,
    ):
        # runs the defaulting operation on the logger output
        # method so that the default logger output is used instead
        output = output or connection.debug

        # unpacks the various values that are going to be part of
        # the log message to be printed in the debug, these values
        # should come from either the connection or the parser
        is_tuple = type(connection.address) in (list, tuple)
        ip_address = connection.address[0] if is_tuple else connection.address
        method = parser.method.upper()
        path = parser.get_path()
        version_s = parser.version_s

        # creates some composite values taking into account the various
        # parameters that have bean provided
        date_s = datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
        size_s = size_s or headers.get("Content-Length", "-1")

        # creates the complete message in the "Common Log Format" and then
        # prints a debug message with that same contents
        message = '%s %s %s [%s] "%s %s %s" %d %s' % (
            ip_address,
            "-",
            username,
            date_s,
            method,
            path,
            version_s,
            code,
            size_s,
        )
        output(message)
