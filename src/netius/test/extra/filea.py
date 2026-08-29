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

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import shutil
import tempfile
import unittest

import netius
import netius.extra

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class FileAsyncServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.hello_path = os.path.join(self.base_path, "hello.txt")
        self._write(self.hello_path, b"Hello World")
        self.large_path = os.path.join(self.base_path, "large.bin")
        self._write(self.large_path, b"L" * (netius.extra.filea.BUFFER_SIZE + 1))
        self.server = netius.extra.FileAsyncServer(base_path=self.base_path)
        self.connections = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self._close_files()
        self.server.cleanup()
        shutil.rmtree(self.base_path)

    def test_on_connection_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        file = mock.MagicMock()
        connection.file = file

        with mock.patch.object(self.server, "fclose") as fclose:
            self.server.on_connection_d(connection)

        # the closing of the file is handed to the file pool, so that the
        # event loop is not blocked by it, and never run in place
        self.assertEqual(fclose.call_args[0][0], file)
        self.assertEqual(file.close.call_count, 0)
        self.assertEqual(connection.file, None)
        self.assertEqual(connection.range, None)
        self.assertEqual(connection.bytes_p, None)
        self.assertEqual(connection.queue, None)

    def test_on_connection_d_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = mock.MagicMock()
        connection.file = None

        with mock.patch.object(self.server, "fclose") as fclose:
            self.server.on_connection_d(connection)

        # a connection that carries no file has nothing to be released,
        # meaning that the pool is never reached for it
        self.assertEqual(fclose.call_count, 0)
        self.assertEqual(connection.file, None)

    def test_on_stream_d(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        stream = mock.MagicMock()
        file = mock.MagicMock()
        stream.file = file

        with mock.patch.object(self.server, "fclose") as fclose:
            self.server.on_stream_d(stream)

        self.assertEqual(fclose.call_args[0][0], file)
        self.assertEqual(file.close.call_count, 0)
        self.assertEqual(stream.file, None)
        self.assertEqual(stream.range, None)
        self.assertEqual(stream.bytes_p, None)
        self.assertEqual(stream.queue, None)

    def test_on_stream_d_no_file(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        stream = mock.MagicMock()
        stream.file = None

        with mock.patch.object(self.server, "fclose") as fclose:
            self.server.on_stream_d(stream)

        self.assertEqual(fclose.call_count, 0)
        self.assertEqual(stream.file, None)

    def test__file_send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))

        callback = self._file_send(connection)

        callback(b"Hello World")

        args, kwargs = connection.send_part.call_args

        # the whole file fits a single buffer and so the sending is final,
        # the finish callback releasing the file and flushing the connection
        self.assertEqual(args[0], b"Hello World")
        self.assertEqual(kwargs["final"], False)
        self.assertEqual(kwargs["callback"], self.server._file_finish)
        self.assertEqual(connection.bytes_p, 0)

    def test__file_send_buffer(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        size = netius.extra.filea.BUFFER_SIZE + 1
        connection = self._make_file_connection(self.large_path, (0, size - 1))

        with mock.patch.object(self.server, "fread") as fread:
            self.server._file_send(connection)

        # the amount that is asked from the pool is bound by the buffer,
        # which is a multiple of the one of the blocking server
        self.assertEqual(fread.call_args[0][1], netius.extra.filea.BUFFER_SIZE)

        callback = fread.call_args[1]["data"]

        callback(b"L" * netius.extra.filea.BUFFER_SIZE)

        args, kwargs = connection.send_part.call_args

        # there are bytes left to be sent, so the next part is scheduled
        # through the very same callback, instead of the finish one
        self.assertEqual(kwargs["callback"], self.server._file_send)
        self.assertEqual(connection.bytes_p, 1)

    def test__file_send_empty(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))

        callback = self._file_send(connection)

        callback(b"")

        args, kwargs = connection.send_part.call_args

        # a reading that gives nothing back closes the sending, as there's
        # no more data to be taken from the file
        self.assertEqual(args[0], b"")
        self.assertEqual(kwargs["callback"], self.server._file_finish)
        self.assertEqual(connection.bytes_p, 11)

    def test__file_send_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))

        callback = self._file_send(connection)

        connection.file.close()
        connection.file = None

        callback(b"Hello World")

        # the file of the connection was released while the reading was
        # pending, so the data that arrives late must be dropped
        self.assertEqual(connection.send_part.call_count, 0)

    def test__file_send_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_file_connection(self.hello_path, (0, 10))

        callback = self._file_send(connection)

        callback(netius.NetiusError("Invalid file"))

        # a reading that failed gives an exception in the place of the
        # data, which must not be sent to the client
        self.assertEqual(connection.send_part.call_count, 0)
        self.assertEqual(connection.bytes_p, 11)

    def _file_send(self, connection):
        with mock.patch.object(self.server, "fread") as fread:
            self.server._file_send(connection)

        args, kwargs = fread.call_args

        self.assertEqual(args[0], connection.file)

        return kwargs["data"]

    def _make_connection(self):
        connection = mock.MagicMock()
        # removes the dynamic attributes that the server checks through
        # hasattr, otherwise they would always be reported as present
        del connection.file
        del connection.queue
        self.connections.append(connection)
        return connection

    def _make_file_connection(self, path, range):
        connection = self._make_connection()
        connection.file = open(path, "rb")
        connection.file.seek(range[0])
        connection.range = range
        connection.bytes_p = range[1] - range[0] + 1
        return connection

    def _close_files(self):
        # the file of a connection is only released once the sending of the
        # response is finished, so an interrupted one has to be closed by
        # hand, otherwise the removal of the directory fails under Windows
        for connection in self.connections:
            file = getattr(connection, "file", None)
            if not file:
                continue
            file.close()

    def _write(self, path, data):
        file = open(path, "wb")
        try:
            file.write(data)
        finally:
            file.close()
