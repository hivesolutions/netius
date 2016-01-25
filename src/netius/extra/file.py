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

import os
import datetime
import mimetypes

import netius.common
import netius.servers

BUFFER_SIZE = 4096
""" The size of the buffer that is going to be used when
sending the file to the client, this should not be neither
to big nor to small (as both situations would create problems) """

class FileServer(netius.servers.HTTPServer):
    """
    Simple implementation of a file server that is able to list files
    for directories taking into account the base path values.

    This is a synchronous implementation meaning that the server loop
    will block for the various i/o operations to be performed.

    Current implementation supports byte ranges so that partial retrieval
    of a file is possible.
    """

    def __init__(self, base_path = "", cors = False, cache = 0, *args, **kwargs):
        netius.servers.HTTPServer.__init__(self, *args, **kwargs)
        self.base_path = base_path
        self.cors = cors
        self.cache = 0

    def on_connection_d(self, connection):
        netius.servers.HTTPServer.on_connection_d(self, connection)

        file = hasattr(connection, "file") and connection.file
        if file: file.close()
        setattr(connection, "file", None)
        setattr(connection, "range", None)
        setattr(connection, "bytes_p", None)
        setattr(connection, "queue", None)

    def on_serve(self):
        netius.servers.HTTPServer.on_serve(self)
        if self.env: self.base_path = self.get_env("BASE_PATH", self.base_path)
        if self.env: self.cors = self.get_env("CORS", self.cors, cast = bool)
        if self.env: self.cache = self.get_env("CACHE", self.cache, cast = int)
        self.base_path = os.path.abspath(self.base_path)
        self.cache_d = datetime.timedelta(seconds = self.cache)
        self.info("Defining '%s' as the root of the file server ..." % (self.base_path or "."))
        if self.cors: self.info("Cross origin resource sharing is enabled")
        if self.cache: self.info("Resource cache set with %d seconds" % self.cache)

    def on_data_http(self, connection, parser):
        netius.servers.HTTPServer.on_data_http(self, connection, parser)

        # verifies if the current connection contains a reference to the
        # file object, in case it exists there's a file currently being
        # handled by the connection and so the current data processing
        # must be delayed until the file is processed (inserted in queue)
        if hasattr(connection, "file") and connection.file:
            if not hasattr(connection, "queue"): connection.queue = []
            state = parser.get_state()
            connection.queue.append(state)
            return

        try:
            # retrieves the requested path from the parser and the constructs
            # the correct file name/path to be used in the reading from the
            # current file system, so that it's possible to handle the data
            path = parser.get_path()
            path = netius.legacy.unquote(path)
            path = path.lstrip("/")
            path_f = os.path.join(self.base_path, path)
            path_f = os.path.abspath(path_f)
            path_f = os.path.normpath(path_f)

            # retrieves the current file system encoding and determines if it
            # it's required to decode the path into an unicode string, if that's
            # the case the normal decoding process is used using the currently
            # defined file system encoding as defined in the specification
            is_unicode = netius.legacy.is_unicode(path_f)
            if not is_unicode: path_f = path_f.decode("utf-8")

            # verifies if the provided path starts with the contents of the
            # base path in case it does not it's a security issue and a proper
            # exception must be raised indicating the issue
            is_sub = path_f.startswith(self.base_path)
            if not is_sub: raise netius.SecurityError("Invalid path")

            # verifies if the requested file exists in case it does not
            # raises an error indicating the problem so that the user is
            # notified about the failure to find the appropriate file
            if not os.path.exists(path_f): self.on_no_file(connection); return

            # verifies if the currently resolved path refers an directory or
            # instead a normal file and handles each of the cases properly by
            # redirecting the request to the proper handlers
            is_dir = os.path.isdir(path_f)
            if is_dir: self.on_dir_file(connection, parser, path_f)
            else: self.on_normal_file(connection, parser, path_f)
        except BaseException as exception:
            # handles the exception gracefully by sending the contents of
            # it to the client and identifying the problem correctly
            self.on_exception_file(connection, exception)

    def on_dir_file(self, connection, parser, path):
        path_v = parser.get_path()
        path_v = netius.legacy.unquote(path_v)

        is_valid = path_v.endswith("/")
        if not is_valid:
            path_q = netius.legacy.quote(path_v)
            connection.send_response(
                data = "Permanent redirect",
                headers = dict(
                    location = path_q + "/"
                ),
                code = 301,
                apply = True
            )
            return

        items = os.listdir(path)
        items.sort()

        is_root = path_v == "" or path_v == "/"
        if not is_root: items.insert(0, "..")

        buffer = list()
        buffer.append("<html>")
        buffer.append("<meta charset=\"utf-8\" />")
        buffer.append("<title>Index of %s</title>" % path_v)
        buffer.append("<body>")
        buffer.append("<h1>Index of %s</h1>" % path_v)
        buffer.append("<hr/>")
        buffer.append("<table>")
        buffer.append("<thead>")
        buffer.append("<tr>")
        buffer.append("<th align=\"left\" width=\"260\">Name</th>")
        buffer.append("<th align=\"left\" width=\"130\">Last Modified</th>")
        buffer.append("<th align=\"left\" width=\"70\">Size</th>")
        buffer.append("<th align=\"left\" width=\"250\">Type</th>")
        buffer.append("</tr>")
        buffer.append("</thead>")
        buffer.append("<tbody>")
        for item in items:
            if netius.legacy.PYTHON_3: item_s = item
            else: item_s = item.encode("utf-8")

            path_f = os.path.join(path, item)
            if not os.path.exists(path_f): continue

            is_dir = os.path.isdir(path_f)
            item_s = item_s + "/" if is_dir else item_s

            _time = os.path.getmtime(path_f)
            date_time = datetime.datetime.utcfromtimestamp(_time)
            time_s = date_time.strftime("%Y-%m-%d %H:%M")

            size = os.path.getsize(path_f)
            size_s = netius.common.size_round_unit(size, space = True)
            size_s = "-" if is_dir else size_s

            type_s, _encoding = mimetypes.guess_type(path_f, strict = True)
            type_s = type or "-"
            type_s = "Directory" if is_dir else type

            buffer.append("<tr>")
            buffer.append("<td><a href=\"%s\">%s</td>" % (item_s, item_s))
            buffer.append("<td>%s</td>" % time_s)
            buffer.append("<td>%s</td>" % size_s)
            buffer.append("<td>%s</td>" % type_s)
            buffer.append("</tr>")
        buffer.append("</tbody>")
        buffer.append("</table>")
        buffer.append("<hr/>")
        buffer.append("<span>")
        buffer.append(netius.IDENTIFIER)
        buffer.append("</span>")
        buffer.append("</body>")
        buffer.append("</html>")
        data = "".join(buffer)

        is_unicode = netius.legacy.is_unicode(data)
        if is_unicode: data = data.encode("utf-8")

        connection.send_response(
            data = data,
            code = 200,
            apply = True,
            callback = self._file_check_close
        )

    def on_normal_file(self, connection, parser, path):
        # encodes the current path in case it's currently represented by
        # a string, this is going to avoid problems in the logging of the
        # path that is being requested (unicode encoding problems)
        path_s = path if netius.legacy.is_str(path) else path.encode("utf-8")

        # prints a debug message about the file that is going to be read
        # from the current file system to be sent to the connection
        self.debug("Reading file '%s' from file system" % path_s)

        # uses the parser from the connection to be able to gather the
        # range as a string to be used latter for conversion
        range_s = parser.headers.get("range", None)
        is_partial = True if range_s else False

        # retrieves the last modified timestamp for the resource path and
        # uses it to create the etag for the resource to be served
        modified = os.path.getmtime(path)
        etag = "netius-%.2f" % modified

        # retrieves the header that describes the previous version in the
        # client side (client side etag) and compares both of the etags to
        # verify if the file changed meanwhile or not
        _etag = parser.headers.get("if-none-match", None)
        not_modified = etag == _etag

        # in case the file did not change in the mean time the not modified
        # callback must be called to correctly handled the file no change
        if not_modified: self.on_not_modified(connection, path); return

        # tries to guess the mime type of the file present in the target
        # file path that is going to be returned, this may fail as it's not
        # always possible to determine the correct mime type for a file
        # for suck situations the default mime type is used
        type, _encoding = mimetypes.guess_type(path, strict = True)
        type = type or "application/octet-stream"

        # retrieves the size of the file that has just be resolved using
        # the currently provided path value and then associates the file
        # with the current connection
        file_size = os.path.getsize(path)
        file = open(path, "rb")
        connection.file = file

        # convert the current string based representation of the range
        # into a tuple based presentation otherwise creates the default
        # tuple containing the initial position and the final one
        if is_partial:
            range_s = range_s[6:]
            start_s, end_s = range_s.split("-", 1)
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else file_size - 1
            range = (start, end)
        else: range = (0, file_size - 1)

        # calculates the real data size of the chunk that is going to be
        # sent to the client this must use the normal range approach
        data_size = range[1] - range[0] + 1

        # associates the range tuple with the current connection as it's
        # going to be used latter for additional computation
        connection.range = range
        connection.bytes_p = data_size

        # seeks the current file to the initial position where it's going
        # to start it's reading processing as according to the range
        file.seek(range[0])

        # creates the string that will represent the content range that is
        # going to be returned to the client in the current request
        content_range_s = "bytes %d-%d/%d" % (range[0], range[1], file_size)

        # creates the map that will hold the various header values for the
        # the current message to be sent it may contain both the length
        # of the file that is going to be returned and the type of it
        headers = dict()
        headers["etag"] = etag
        headers["content-length"] = "%d" % data_size
        if self.cors: headers["access-control-allow-origin"] = "*"
        if type: headers["content-type"] = type
        if is_partial: headers["content-range"] = content_range_s
        if not is_partial: headers["accept-ranges"] = "bytes"

        # in case there's a valid cache defined must populate the proper header
        # fields so that cache is applied to the request
        if self.cache:
            current = datetime.datetime.utcnow()
            target = current + self.cache_d
            target_s = target.strftime("%a, %d %b %Y %H:%M:%S GMT")
            cache_s = "public, max-age=%d" % self.cache
            headers["expires"] = target_s
            headers["cache-control"] = cache_s

        # "calculates" the proper returning code taking into account if the
        # current data to be sent is partial or not
        code = 206 if is_partial else 200

        # sends the initial part of the file response containing the headers
        # and the description of the file (includes size) the callback to this
        # operation is the initial sending of the file contents so that the
        # sending of the proper file contents starts with success
        connection.send_response(
            headers = headers,
            code = code,
            apply = True,
            flush = False,
            callback = self._file_send
        )

    def on_no_file(self, connection):
        connection.send_response(
            data = "File not found",
            headers = dict(
                connection = "close"
            ),
            code = 404,
            apply = True,
            callback = self._file_close
        )

    def on_exception_file(self, connection, exception):
        connection.send_response(
            data = "Problem handling request - %s" % str(exception),
            headers = dict(
                connection = "close"
            ),
            code = 500,
            apply = True,
            callback = self._file_close
        )

    def on_not_modified(self, connection, path):
        connection.set_encoding(netius.servers.PLAIN_ENCODING)
        connection.send_response(
            data = "",
            code = 304,
            apply = True
        )

    def _next_queue(self, connection):
        # verifies if the current connection already contains a reference to
        # the queue structure that handles the queuing/pipelining of requests
        # if it does not or the queue is empty returns immediately, as there's
        # nothing currently pending to be done/processed
        if not hasattr(connection, "queue"): return
        if not connection.queue: return

        # retrieves the state (of the parser) as the payload of the next element
        # in the queue and then uses it to construct a mock parser object that is
        # going to be used to simulate an on data call to the file server
        state = connection.queue.pop(0)
        parser = netius.common.HTTPParser.mock(connection.parser.owner, state)
        try: self.on_data_http(connection, parser)
        finally: parser.destroy()

    def _file_send(self, connection):
        file = connection.file
        range = connection.range
        is_larger = BUFFER_SIZE > connection.bytes_p
        buffer_s = connection.bytes_p if is_larger else BUFFER_SIZE
        data = file.read(buffer_s)
        data_l = len(data) if data else 0
        connection.bytes_p -= data_l
        is_final = not data or connection.bytes_p == 0
        callback = self._file_finish if is_final else self._file_send
        connection.send(
            data,
            delay = True,
            callback = callback
        )

    def _file_finish(self, connection):
        connection.file.close()
        connection.file = None
        connection.range = None
        connection.bytes_p = None
        is_keep_alive = connection.parser.keep_alive
        callback = None if is_keep_alive else self._file_close
        connection.flush(callback = callback)
        self._next_queue(connection)

    def _file_close(self, connection):
        connection.close(flush = True)

    def _file_check_close(self, connection):
        if connection.parser.keep_alive: return
        connection.close(flush = True)

if __name__ == "__main__":
    import logging

    server = FileServer(level = logging.INFO)
    server.serve(env = True)
