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

import os
import urllib
import datetime
import mimetypes

import netius.common
import netius.servers

BUFFER_SIZE = 4096
""" The size of the buffer that is going to be used when
sending the file to the client, this should not be neither
to big nor to small (as both situations would create problems) """

class FileServer(netius.servers.HTTPServer):

    def __init__(self, base_path = "", *args, **kwargs):
        netius.servers.HTTPServer.__init__(self, *args, **kwargs)
        self.base_path = base_path

    def on_connection_d(self, connection):
        netius.servers.HTTPServer.on_connection_d(self, connection)

        file = hasattr(connection, "file") and connection.file
        if file: file.close()
        setattr(connection, "file", None)
        setattr(connection, "range", None)
        setattr(connection, "bytes_p", None)

    def on_serve(self):
        netius.servers.HTTPServer.on_serve(self)
        if self.env: self.base_path = os.environ.get("BASE_PATH", self.base_path)
        self.info("Defining '%s' as the root of the file server ..." % (self.base_path or "."))

    def on_data_http(self, connection, parser):
        netius.servers.HTTPServer.on_data_http(self, connection, parser)

        # retrieves the requested path from the parser and the constructs
        # the correct file name/path to be used in the reading from the
        # current file system, so that it's possible to handle the data
        path = parser.get_path()
        path = urllib.unquote(path)
        path = path.lstrip("/")
        path_f = os.path.join(self.base_path, path)
        path_f = os.path.abspath(path_f)
        path_f = os.path.normpath(path_f)

        # verifies if the requested file exists in case it does not
        # raises an error indicating the problem so that the user is
        # notified about the failure to find the appropriate file
        if not os.path.exists(path_f): return self.on_no_file(connection)

        try:
            # verifies if the currently resolved path refers an directory or
            # instead a normal file and handles each of the cases properly by
            # redirecting the request to the proper handlers
            is_dir = os.path.isdir(path_f)
            if is_dir: return self.on_dir_file(connection, path_f)
            else: return self.on_normal_file(connection, path_f)
        except BaseException, exception:
            # handles the exception gracefully by sending the contents of
            # it to the client and identifying the problem correctly
            return self.on_exception_file(connection, exception)

    def on_dir_file(self, connection, path):
        parser = connection.parser
        path_v = parser.get_path()
        path_v = urllib.unquote(path_v)

        is_valid = path_v.endswith("/")
        if not is_valid:
            return connection.send_response(
                data = "Permanent redirect",
                headers = dict(
                    location = path_v + "/"
                ),
                code = 301,
                apply = True
            )

        items = os.listdir(path)
        items.sort()

        is_root = path_v == "" or path_v == "/"
        if not is_root: items.insert(0, "..")

        buffer = list()
        buffer.append("<html>")
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
            path_f = os.path.join(path, item)
            is_dir = os.path.isdir(path_f)
            item_s = item + "/" if is_dir else item

            _time = os.path.getmtime(path_f)
            date_time = datetime.datetime.utcfromtimestamp(_time)
            time_s = date_time.strftime("%Y-%m-%d %H:%M")

            size = os.path.getsize(path_f)
            size_s = netius.common.size_round_unit(size, space = True)
            size_s = "-" if is_dir else size_s

            type, _encoding = mimetypes.guess_type(path_f, strict = True)
            type = type or "-"
            type = "Directory" if is_dir else type

            buffer.append("<tr>")
            buffer.append("<td><a href=\"%s\">%s</td>" % (item_s, item_s))
            buffer.append("<td>%s</td>" % time_s)
            buffer.append("<td>%s</td>" % size_s)
            buffer.append("<td>%s</td>" % type)
            buffer.append("</tr>")
        buffer.append("</tbody>")
        buffer.append("</table>")
        buffer.append("<hr/>")
        buffer.append("<span>")
        buffer.append("%s/%s" % (netius.NAME, netius.VERSION))
        buffer.append("</span>")
        buffer.append("</body>")
        buffer.append("</html>")
        data = "".join(buffer)

        return connection.send_response(
            data = data,
            code = 200,
            apply = True,
            callback = self._file_check_close
        )

    def on_normal_file(self, connection, path):
        # prints a debug message about the file that is going to be read
        # from the current file system to be sent to the connection
        self.debug("Reading file '%s' from file system" % path)

        # retrieves the parser from the connection and then uses it to
        # gather the range as a string to be used latter for conversion
        parser = connection.parser
        range_s = parser.headers.get("range", None)
        is_partial = True if range_s else False

        # tries to guess the mime type of the file present in the target
        # file path that is going to be returned, this may fails as it's not
        # always possible to determine the correct mime type for a file
        type, _encoding = mimetypes.guess_type(path, strict = True)

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
        headers["content-length"] = "%d" % data_size
        if type: headers["content-type"] = type
        if is_partial: headers["content-range"] = content_range_s
        if not is_partial: headers["accept-ranges"] = "bytes"

        # "calculates" the proper returning code taking into account if the
        # current data to be sent is partial or not
        code = 206 if is_partial else 200

        # sends the initial part of the file response containing the headers
        # and the description of the file (includes size) the callback to this
        # operation is the initial sending of the file contents so that the
        # sending of the proper file contents starts with success
        return connection.send_response(
            headers = headers,
            code = code,
            apply = True,
            callback = self._file_send
        )

    def on_no_file(self, connection):
        return connection.send_response(
            data = "File not found",
            headers = dict(
                connection = "close"
            ),
            code = 404,
            apply = True,
            callback = self._file_close
        )

    def on_exception_file(self, connection, exception):
        return connection.send_response(
            data = "Problem handling request - %s" % str(exception),
            headers = dict(
                connection = "close"
            ),
            code = 500,
            apply = True,
            callback = self._file_close
        )

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
        if connection.parser.keep_alive: return
        connection.close()

    def _file_close(self, connection):
        connection.close()

    def _file_check_close(self, connection):
        if connection.parser.keep_alive: return
        connection.close()

if __name__ == "__main__":
    import logging

    server = FileServer(level = logging.INFO)
    server.serve(env = True)
