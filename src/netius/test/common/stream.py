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

import netius.common


class StreamTest(unittest.TestCase):

    def test_unimplemented(self):
        stream = netius.common.Stream()

        # the base of the streams implements none of the operations, so that
        # a sub class that forgets one of them is told about it
        self.assertRaises(netius.NotImplemented, stream.open)
        self.assertRaises(netius.NotImplemented, stream.close)
        self.assertRaises(netius.NotImplemented, stream.seek, 0)
        self.assertRaises(netius.NotImplemented, stream.read, 1)
        self.assertRaises(netius.NotImplemented, stream.write, b"")
        self.assertRaises(netius.NotImplemented, stream.flush)


class FileStreamTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.dir_path = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.dir_path, ignore_errors=True)

    def test_open(self):
        path = os.path.join(self.dir_path, "netius.bin")
        stream = netius.common.FileStream(path, 32)
        stream.open()
        try:
            # the file is allocated to the size that was named, so that the
            # writing of it may happen at any offset from the start
            self.assertEqual(os.path.getsize(path), 32)
        finally:
            stream.close()

    def test_open_unallocated(self):
        path = os.path.join(self.dir_path, "netius.bin")
        stream = netius.common.FileStream(path, 32)
        stream.open(allocate=False)
        try:
            # one that is not allocated is left empty, the writing of it
            # growing the file as it goes
            self.assertEqual(os.path.getsize(path), 0)
        finally:
            stream.close()

    def test_close(self):
        path = os.path.join(self.dir_path, "netius.bin")
        stream = netius.common.FileStream(path, 32)

        # a stream that was never opened has no file to be closed, and asking
        # for it must not raise
        self.assertEqual(stream.close(), None)

        stream.open()
        stream.close()

        self.assertEqual(stream.file, None)
        self.assertEqual(stream.close(), None)

    def test_read_write(self):
        path = os.path.join(self.dir_path, "netius.bin")
        stream = netius.common.FileStream(path, 32)
        stream.open()
        try:
            stream.seek(4)
            stream.write(b"netius")
            stream.flush()

            # what was written is read back from the offset it was put at,
            # the file being addressed as one contiguous space
            stream.seek(4)
            self.assertEqual(stream.read(6), b"netius")
        finally:
            stream.close()


class FilesStreamTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.dir_path = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.dir_path, ignore_errors=True)

    def test_open(self):
        stream = self._make_stream()
        stream.open()
        try:
            # every file of the set is allocated to the size that was named
            # for it, as the stream addresses them as one
            self.assertEqual(len(stream.files), 2)
            self.assertEqual(
                os.path.getsize(os.path.join(self.dir_path, "first.bin")), 8
            )
            self.assertEqual(
                os.path.getsize(os.path.join(self.dir_path, "second.bin")), 4
            )
        finally:
            stream.close()

    def test_open_unallocated(self):
        stream = self._make_stream()
        stream.open(allocate=False)
        try:
            self.assertEqual(
                os.path.getsize(os.path.join(self.dir_path, "first.bin")), 0
            )
        finally:
            stream.close()

    def test_close(self):
        stream = self._make_stream()

        # a stream that was never opened has no file to be closed, and asking
        # for it must not raise
        self.assertEqual(stream.close(), None)

        stream.open()
        stream.close()

        self.assertEqual(stream.files, [])

    def test_write_read(self):
        stream = self._make_stream()
        stream.open()
        try:
            stream.seek(0)
            stream.write(b"0123456789ab")

            # the payload is spread over the files by the sizes that were
            # named, the boundary between them being invisible to the caller
            first = self._read(os.path.join(self.dir_path, "first.bin"))
            second = self._read(os.path.join(self.dir_path, "second.bin"))
            self.assertEqual(first, b"01234567")
            self.assertEqual(second, b"89ab")

            stream.seek(0)
            self.assertEqual(stream.read(12), b"0123456789ab")
        finally:
            stream.close()

    def test_write_read_offset(self):
        stream = self._make_stream()
        stream.open()
        try:
            stream.seek(0)
            stream.write(b"0123456789ab")

            # a read that starts inside one file and ends inside the next one
            # is served from both of them, joined in the order they were named
            stream.seek(6)
            self.assertEqual(stream.read(4), b"6789")

            # and so is a write, the files that it does not reach being left
            # exactly as they were
            stream.seek(6)
            stream.write(b"XYZW")

            stream.seek(0)
            self.assertEqual(stream.read(12), b"012345XYZWab")
        finally:
            stream.close()

    def test_write_offset(self):
        stream = self._make_stream()
        stream.open()
        try:
            stream.seek(0)
            stream.write(b"0123456789ab")

            # a write that starts past the first of the files skips it, so
            # that what it already carries is left untouched
            stream.seek(9)
            stream.write(b"XY")

            first = self._read(os.path.join(self.dir_path, "first.bin"))
            second = self._read(os.path.join(self.dir_path, "second.bin"))
            self.assertEqual(first, b"01234567")
            self.assertEqual(second, b"8XYb")
        finally:
            stream.close()

    def test_read_bounded(self):
        stream = self._make_stream()
        stream.open()
        try:
            stream.seek(0)
            stream.write(b"0123456789ab")

            # a read that asks for more than what is left gives back only what
            # there is, instead of reaching past the end of the set
            stream.seek(10)
            self.assertEqual(stream.read(8), b"ab")

            # and the offset never runs past the size of the set, so that a
            # read that follows it is still a valid one
            self.assertEqual(stream._offset, 12)
        finally:
            stream.close()

    def test_flush(self):
        stream = self._make_stream()
        stream.open()
        try:
            stream.seek(0)
            stream.write(b"0123456789ab")

            # the flushing reaches every file of the set, as each of them
            # carries a buffer of its own
            self.assertEqual(stream.flush(), None)
        finally:
            stream.close()

    def _make_stream(self):
        # builds a stream over two files, so that the addressing of them as a
        # contiguous space may be verified across the boundary
        files_m = [
            dict(path=["first.bin"], length=8),
            dict(path=["second.bin"], length=4),
        ]
        return netius.common.FilesStream(self.dir_path, 12, files_m)

    def _read(self, path):
        file = open(path, "rb")
        try:
            return file.read()
        finally:
            file.close()
