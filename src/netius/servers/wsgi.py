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

import sys

import netius

from . import http
from . import http2

SERVER_SOFTWARE = netius.IDENTIFIER
""" The server software string that is going to identify the
current service that is running on the host, the values should
include both the name and the version of it """

COMPRESSED_LIMIT = 5242880
""" The default maximum size value for the sending of compressed
content, this should ensure proper resource usage avoiding extreme
high levels of resource usage for compression of large files """

class WSGIServer(http2.HTTP2Server):
    """
    Base class for the creation of a wsgi compliant server
    the server should be initialized with the "target" app
    object as reference and a mount point.
    """

    def __init__(
        self,
        app,
        mount = "",
        decode = True,
        compressed_limit = COMPRESSED_LIMIT,
        *args,
        **kwargs
    ):
        http2.HTTP2Server.__init__(self, *args, **kwargs)
        self.app = app
        self.mount = mount
        self.mount_l = len(mount)
        self.decode = decode
        self.compressed_limit = compressed_limit

    def on_connection_d(self, connection):
        http2.HTTP2Server.on_connection_d(self, connection)

        # tries to run the releasing operation on the current connection
        # so that the proper destruction of objects is performed avoiding
        # leaving any extra memory leak (would create problems)
        self._release(connection)

        # runs the extra release queue operation for the connection so that
        # the (possible) associated queue is properly release (no leaks)
        self._release_queue(connection)

    def on_serve(self):
        http2.HTTP2Server.on_serve(self)
        if self.env: self.compressed_limit = self.get_env(
            "COMPRESSED_LIMIT", self.compressed_limit, cast = int
        )
        self.info(
            "Starting WSGI server with %d bytes limit on compression ..." %\
            self.compressed_limit
        )

    def on_data_http(self, connection, parser):
        http2.HTTP2Server.on_data_http(self, connection, parser)

        # retrieves the path for the current request and then retrieves
        # the query string part for it also, after that computes the
        # path info value as the substring of the path without the mount
        path = parser.get_path(normalize = True)
        query = parser.get_query()
        path_info = path[self.mount_l:]

        # verifies if the path and query values should be encoded and if
        # that's the case the decoding process should unquote the received
        # path and then convert it into a valid string representation, this
        # is especially relevant for the python 3 infra-structure, this is
        # a tricky process but is required for the wsgi compliance
        if self.decode: path_info = self._decode(path_info)

        # retrieves a possible forwarded protocol value from the request
        # headers and calculates the appropriate (final scheme value)
        # taking the proxy value into account
        forwarded_protocol = parser.headers.get("x-forwarded-proto", None)
        scheme = "https" if connection.ssl else "http"
        scheme = forwarded_protocol if forwarded_protocol else scheme

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
            SERVER_PORT = str(self.port),
            SERVER_PROTOCOL = parser.version_s,
            SERVER_SOFTWARE = SERVER_SOFTWARE,
            REMOTE_ADDR = connection.address[0]
        )

        # updates the environment map with all the structures referring
        # to the wsgi specifications note that the message is retrieved
        # as a buffer to be able to handle the file specific operations
        environ["wsgi.version"] = (1, 0)
        environ["wsgi.url_scheme"] = scheme
        environ["wsgi.input"] = parser.get_message_b(copy = True)
        environ["wsgi.errors"] = sys.stderr
        environ["wsgi.multithread"] = False
        environ["wsgi.multiprocess"] = False
        environ["wsgi.run_once"] = False
        environ["wsgi.server_name"] = netius.NAME
        environ["wsgi.server_version"] = netius.VERSION

        # iterates over all the header values that have been received
        # to set them in the environment map to be used by the wsgi
        # infra-structure, not that their name is capitalized as defined
        # in the standard specification
        for key, value in parser.headers.items():
            key = "HTTP_" + key.replace("-", "_").upper()
            if type(value) in (list, tuple): value = ";".join(value)
            environ[key] = value

        # verifies if the connection already has an iterator associated with
        # it, if that's the case the connection is already in use and the current
        # request processing must be delayed for future processing, this is
        # typically associated with http pipelining
        if hasattr(connection, "iterator") and connection.iterator:
            if not hasattr(connection, "queue"): connection.queue = []
            connection.queue.append(environ)
            return

        # calls the proper on environment callback so that the current request
        # is handled and processed (flush operation)
        self.on_environ(connection, environ)

    def on_environ(self, connection, environ):
        # method created as a clojure that handles the starting of
        # response as defined in the wsgi standards
        def start_response(status, headers):
            return self._start_response(connection, status, headers)

        # runs the app logic with the provided environment map and starts
        # response clojure and then iterates over the complete set of values
        # in the returned iterator to send the messages to the other end
        # note that the iterator and the environment map are set in the
        # connection for latter retrieval (required for processing/closing)
        sequence = self.app(environ, start_response)
        iterator = iter(sequence)
        connection.iterator = iterator
        connection.environ = environ

        # triggers the start of the connection iterator flushing operation
        # by calling the send part method for the current connection, this
        # should start reading data from the iterator and sending it to the
        # connection associated (recursive approach)
        self._send_part(connection)

    def _next_queue(self, connection):
        # verifies if the current connection already contains a reference to
        # the queue structure that handles the queueing/pipelining of requests
        # if it does not or the queue is empty returns immediately, as there's
        # nothing currently pending to be done/processed
        if not hasattr(connection, "queue"): return
        if not connection.queue: return

        # retrieves the current/first element in the connection queue to for
        # the processing and then runs the proper callback for the environ
        environ = connection.queue.pop(0)
        self.on_environ(connection, environ)

    def _start_response(self, connection, status, headers):
        # retrieves the parser object from the connection and uses
        # it to retrieve the string version of the http version
        parser = connection.parser
        version_s = parser.version_s

        # adds an extra space to the status line and then
        # splits it into the status message and the code
        status_c, status_m = (status + " ").split(" ", 1)
        status_c = int(status_c)
        status_m = status_m.strip()

        # converts the provided list of header tuples into a key
        # values based map so that it may be used more easily
        headers = dict(headers)

        # tries to retrieve the content length value from the headers
        # in case they exist and if the value of them is zero the plain
        # encoding is set in order to avoid extra problems while using
        # chunked encoding with zero length based messages
        length = headers.get("Content-Length", -1)
        length = int(length)
        length = 0 if status_c in (204, 304) else length
        if length == 0: connection.set_encoding(http.PLAIN_ENCODING)

        # verifies if the length value of the message payload overflow
        # the currently defined limit, if that's the case the connection
        # is set as uncompressed to avoid unnecessary encoding that would
        # consume a lot of resources (mostly processor)
        if length > self.compressed_limit: connection.set_uncompressed()

        # tries to determine if the accept ranges value is set and if
        # that's the case forces the uncompressed encoding to avoid possible
        # range missmatch due to re-encoding of the content
        ranges = headers.get("Accept-Ranges", None)
        if ranges == "bytes": connection.set_uncompressed()

        # determines if the content range header is set, meaning that
        # a partial chunk value is being sent if that's the case the
        # uncompressed encoding is forced to avoid re-encoding issues
        content_range = headers.get("Content-Range", None)
        if content_range: connection.set_uncompressed()

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

        # runs the send header operation on the connection, this operation
        # should serialize the various headers and send them through the
        # current connection according to the currently associated protocol
        connection.send_header(
            headers = headers,
            version = version_s,
            code = status_c,
            code_s = status_m
        )

    def _send_part(self, connection):
        # unsets the is final flag and invalidates the data object to the
        # original unset value, these are the default values
        is_final = False
        data = None

        # extracts both the iterator from the connection object so that
        # it may be used for the current set of operations
        iterator = connection.iterator

        # tries to retrieve data from the current iterator and in
        # case the stop iteration is received sets the is final flag
        # so that no more data is sent through the connection
        try: data = next(iterator)
        except StopIteration: is_final = True

        # verifies if the current value in iteration is a future element
        # and if that's the case creates the proper callback to be used
        # for the handling on the end of the iteration
        is_future = isinstance(data, netius.Future)
        if is_future:
            def on_partial(future, value):
                if not value: return
                connection.send_part(value)

            def on_done(future):
                data = future.result()
                exception = future.exception()
                if exception: connection.close()
                else: connection.send_part(data, callback = self._send_part)

            def on_ready():
                return connection.wready

            data.add_partial_callback(on_partial)
            data.add_done_callback(on_done)
            data.add_ready_callback(on_ready)
            return

        # ensures that the provided data is a byte sequence as expected
        # by the underlying server infra-structure
        if data: data = netius.legacy.bytes(data)

        # in case the final flag is set runs the flush operation in the
        # connection setting the proper callback method for it so that
        # the connection state is defined in the proper way (closed or
        # kept untouched) otherwise sends the retrieved data setting the
        # callback to the current method so that more that is sent
        if is_final: connection.flush(callback = self._final)
        else: connection.send_part(
            data,
            final = False,
            callback = self._send_part
        )

    def _final(self, connection):
        # retrieves the parser of the current connection and then determines
        # if the current connection is meant to be kept alive
        parser = connection.parser
        keep_alive = parser.keep_alive

        # in case the connection is not meant to be kept alive must
        # must call the proper underlying close operation (expected)
        if not keep_alive: self._close(connection); return

        # the map of environment must be destroyed properly, avoiding
        # any possible memory leak for the current handling and then the
        # queue of pipelined requests must be flushed/processed, this
        # allows the connection to be re-used for new/pending requests
        self._release(connection)
        self._next_queue(connection)

    def _close(self, connection):
        connection.close(flush = True)

    def _release(self, connection):
        self._release_iterator(connection)
        self._release_environ(connection)
        self._release_parser(connection)

    def _release_iterator(self, connection):
        # verifies if there's an iterator object currently defined
        # in the connection so that it may be close in case that's
        # required, this is mandatory to avoid any memory leak
        iterator = hasattr(connection, "iterator") and connection.iterator
        if not iterator: return

        # verifies if the close attributes is defined in the iterator
        # and if that's the case calls the close method in order to
        # avoid any memory leak caused by the generator
        has_close = hasattr(iterator, "close")
        if has_close: iterator.close()

        # unsets the iterator attribute in the connection object so that
        # it may no longer be used by any chunk of logic code
        connection.iterator = None

    def _release_environ(self, connection):
        # tries to retrieve the map of environment for the current
        # connection and in case it does not exists returns immediately
        environ = hasattr(connection, "environ") and connection.environ
        if not environ: return

        # retrieves the input stream (buffer) and closes it as there's
        # not going to be any further operation in it (avoids leak)
        input = environ["wsgi.input"]
        input.close()

        # removes the complete set of key to value associations in the
        # map and unsets the environ value in the current connection
        environ.clear()
        connection.environ = None

    def _release_parser(self, connection):
        # closes the current file objects in the parser, note that the
        # parser still remains active, this operation only clears the
        # current memory structures associated with the parser
        connection.parser.close()

    def _release_queue(self, connection):
        # tries to retrieve a possible defined queue for the provided
        # connection in case it does not exist returns immediately as
        # there's no queue element to be release/cleared
        queue = hasattr(connection, "queue") and connection.queue
        if not queue: return

        # iterates over the complete set of queue elements (environ
        # based maps) to clear their elements properly
        for environ in queue:
            # retrieves the reference to the input buffer file and
            # closes it (avoiding possible extra accesses and leaks)
            input = environ["wsgi.input"]
            input.close()

            # empties the map key references so that no more access
            # to the map is possible (avoids leaks)
            environ.clear()

        # removes the complete set of elements from the queue while
        # maintaining the original list reference/instance
        del queue[:]

    def _decode(self, value):
        """
        Decodes the provided quoted value, normalizing it according
        to both the pep 333 and the pep 333.

        Note that python 3 enforces the encapsulation of the string
        value around a latin 1 encoded unicode string.

        :type value: String
        :param value: The quoted value that should be normalized and
        decoded according to the wsgi 1.0/1.0.1 specifications.
        :rtype: String
        :return: The normalized version of the provided quoted value
        that is ready to be provided as part of the environ map.
        :see: http://python.org/dev/peps/pep-3333
        """

        value = netius.legacy.unquote(value)
        is_unicode = netius.legacy.is_unicode(value)
        value = value.encode("utf-8") if is_unicode else value
        value = netius.legacy.str(value)
        return value

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
        yield contents

    server = WSGIServer(app = app, level = logging.INFO)
    server.serve(env = True)
