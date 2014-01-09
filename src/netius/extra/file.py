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
import mimetypes

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

        items = os.listdir(path)

        is_root = path_v == "" or path_v == "/"
        if not is_root: items.insert(0, "..")

        buffer = list()
        buffer.append("<html>")
        buffer.append("<title>Directory listing for %s</title>" % path_v)
        buffer.append("<body>")
        buffer.append("<h2>Directory listing for %s</h2>" % path_v)
        buffer.append("<hr/>")
        buffer.append("<ul>")
        for item in items:
            path_f = os.path.join(path, item)
            is_dir = os.path.isdir(path_f)
            item_s = item + "/" if is_dir else item
            buffer.append("<li><a href=\"%s\">%s</a>" % (item_s, item_s))
        buffer.append("</ul>")
        buffer.append("<hr/>")
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

        # tries to guess the mime type of the file present in the target
        # file path that is going to be returned, this may fails as it's not
        # always possible to determine the correct mime type for a file
        type, _encoding = mimetypes.guess_type(path)

        # retrieves the size of the file that has just be resolved using
        # the currently provided path value and then associates the file
        # with the current connection
        file_size = os.path.getsize(path)
        file = open(path, "rb")
        connection.file = file

        # creates the map that will hold the various header values for the
        # the current message to be sent it may contain both the length
        # of the file that is going to be returned and the type of it
        headers = dict()
        headers["content-length"] = "%d" % file_size
        if type: headers["content-type"] = type

        # sends the initial part of the file response containing the headers
        # and the description of the file (includes size) the callback to this
        # operation is the initial sending of the file contents so that the
        # sending of the proper file contents starts with success
        return connection.send_response(
            headers = headers,
            code = 200,
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
        data = file.read(BUFFER_SIZE)
        if data: connection.send(
            data,
            delay = True,
            callback = self._file_send
        )
        else: self._file_finish(connection)

    def _file_finish(self, connection):
        connection.file.close()
        connection.file = None
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
