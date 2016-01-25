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

from . import file as _file

BUFFER_SIZE = _file.BUFFER_SIZE * 16
""" Re-creates the buffer size of the file buffer so that it
handles more data for each chunk, this is required to avoid
extreme amounts of overhead in the file pool """

class FileAsyncServer(_file.FileServer):
    """
    Simple implementation of a file server that uses the async
    file pool infra-structure.

    This is a test implementation and should never be used for
    production work that required mature and stable codebase.

    Using this kind of server (file pool based) is not recommended
    for system that don't provide some system of event fd (windows)
    as it would provide very slow performance or even stall the
    event loop as no notification occurs on events.
    """

    def on_connection_d(self, connection):
        file = hasattr(connection, "file") and connection.file
        if file: self.fclose(file); connection.file = None
        _file.FileServer.on_connection_d(self, connection)

    def _file_send(self, connection):
        file = connection.file
        range = connection.range
        is_larger = BUFFER_SIZE > connection.bytes_p
        buffer_s = connection.bytes_p if is_larger else BUFFER_SIZE

        def callback(data, *args, **kwargs):
            if connection.file == None: return
            if isinstance(data, BaseException): return
            data_l = len(data) if data else 0
            connection.bytes_p -= data_l
            is_final = not data or connection.bytes_p == 0
            callback = self._file_finish if is_final else self._file_send
            connection.send(
                data,
                delay = True,
                callback = callback
            )

        self.fread(file, buffer_s, data = callback)

if __name__ == "__main__":
    import logging

    server = FileAsyncServer(level = logging.INFO)
    server.serve(env = True)
