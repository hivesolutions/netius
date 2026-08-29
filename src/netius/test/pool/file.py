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
import netius.pool

from netius.pool import file


class FileThreadTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.pool = netius.pool.FilePool()
        self.thread = netius.pool.FileThread(0, owner=self.pool)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_execute(self):
        path = self._store("simple.txt", b"hello world")

        self.thread.execute((file.FILE_WORK, file.OPEN_ACTION, path, "rb", "data"))

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.OPEN_ACTION)
        self.assertEqual(data, "data")

        result.close()

        # an exception raised by the action is turned into an error event
        # carrying it, so that the owner is able to react to the failure
        self.thread.execute(
            (
                file.FILE_WORK,
                file.OPEN_ACTION,
                os.path.join(self.base, "missing.txt"),
                "rb",
                "data",
            )
        )

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.ERROR_ACTION)
        self.assertEqual(isinstance(result, IOError), True)
        self.assertEqual(data, "data")

        # a work of a type other than the file one is refused, as the
        # thread is only able to handle the file kind of work
        self.assertRaises(
            netius.NotImplemented,
            self.thread.execute,
            (file.FILE_WORK + 1, file.OPEN_ACTION, path, "rb", None),
        )

    def test_open(self):
        path = self._store("simple.txt", b"hello world")

        self.thread.open(path, "rb", None)

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.OPEN_ACTION)
        self.assertEqual(result.read(), b"hello world")
        self.assertEqual(data, None)

        result.close()

        # the mode is the one that the caller asked for, so that a file
        # may also be opened for writing and not only for reading
        path = os.path.join(self.base, "target.txt")

        self.thread.open(path, "wb", None)

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.OPEN_ACTION)
        self.assertEqual(result.mode, "wb")

        result.write(b"hello world")
        result.close()

        self.assertEqual(self._read("target.txt"), b"hello world")

    def test_close(self):
        path = self._store("simple.txt", b"hello world")
        handle = open(path, "rb")

        self.thread.close(handle, "data")

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.CLOSE_ACTION)
        self.assertEqual(result.closed, True)
        self.assertEqual(data, "data")

    def test_read(self):
        path = self._store("simple.txt", b"hello world")
        handle = open(path, "rb")

        try:
            self.thread.read(handle, 5, "data")

            action, result, data = self.pool.pop_event()

            self.assertEqual(action, file.READ_ACTION)
            self.assertEqual(result, b"hello")
            self.assertEqual(data, "data")

            # a count of minus one reads the complete remainder of the
            # file, starting from where the previous read has stopped
            self.thread.read(handle, -1, None)

            action, result, data = self.pool.pop_event()

            self.assertEqual(result, b" world")

            # a read that reaches the end of the file gives an empty
            # sequence, instead of raising for the exhausted file
            self.thread.read(handle, -1, None)

            action, result, data = self.pool.pop_event()

            self.assertEqual(result, b"")
        finally:
            handle.close()

    def test_write(self):
        path = os.path.join(self.base, "target.txt")
        handle = open(path, "wb")

        try:
            self.thread.write(handle, b"hello world", "data")

            action, result, data = self.pool.pop_event()

            # the event carries the number of bytes that were written and
            # not the buffer itself, as the caller already owns it
            self.assertEqual(action, file.WRITE_ACTION)
            self.assertEqual(result, 11)
            self.assertEqual(data, "data")
        finally:
            handle.close()

        self.assertEqual(self._read("target.txt"), b"hello world")

    def test__execute(self):
        path = self._store("simple.txt", b"hello world")

        # every one of the actions must be routed to the method of the
        # same name, the open one giving back a file for the path
        self.thread._execute((file.FILE_WORK, file.OPEN_ACTION, path, "rb", None))

        action, handle, data = self.pool.pop_event()

        self.assertEqual(action, file.OPEN_ACTION)

        self.thread._execute((file.FILE_WORK, file.READ_ACTION, handle, -1, None))

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.READ_ACTION)
        self.assertEqual(result, b"hello world")

        self.thread._execute((file.FILE_WORK, file.CLOSE_ACTION, handle, None))

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.CLOSE_ACTION)
        self.assertEqual(result.closed, True)

        # the write action must reach the write method, so that the
        # buffer is stored and the number of bytes reported back
        handle = open(os.path.join(self.base, "target.txt"), "wb")

        try:
            self.thread._execute(
                (file.FILE_WORK, file.WRITE_ACTION, handle, b"hello world", None)
            )

            action, result, data = self.pool.pop_event()

            self.assertEqual(action, file.WRITE_ACTION)
            self.assertEqual(result, 11)
        finally:
            handle.close()

        self.assertEqual(self._read("target.txt"), b"hello world")

        # an action that is not one of the defined ones is refused, as
        # there's no method to which it may be routed
        self.assertRaises(
            netius.NotImplemented,
            self.thread._execute,
            (file.FILE_WORK, file.WRITE_ACTION + 1, handle, None),
        )

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        handle = open(path, "wb")
        try:
            handle.write(contents)
        finally:
            handle.close()
        return path

    def _read(self, name):
        handle = open(os.path.join(self.base, name), "rb")
        try:
            return handle.read()
        finally:
            handle.close()


class FilePoolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.pool = netius.pool.FilePool()
        self.thread = netius.pool.FileThread(0, owner=self.pool)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_open(self):
        path = self._store("simple.txt", b"hello world")

        self.pool.open(path, mode="rb", data="data")

        # the work that is queued carries the action and every one of the
        # arguments that the thread needs to run it
        self.assertEqual(
            self.pool.peek(), (file.FILE_WORK, file.OPEN_ACTION, path, "rb", "data")
        )

        self.thread.execute(self.pool.pop())

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.OPEN_ACTION)
        self.assertEqual(result.read(), b"hello world")
        self.assertEqual(data, "data")

        result.close()

    def test_close(self):
        path = self._store("simple.txt", b"hello world")
        handle = open(path, "rb")

        self.pool.close(handle, data="data")

        self.assertEqual(
            self.pool.peek(), (file.FILE_WORK, file.CLOSE_ACTION, handle, "data")
        )

        self.thread.execute(self.pool.pop())

        action, result, data = self.pool.pop_event()

        self.assertEqual(action, file.CLOSE_ACTION)
        self.assertEqual(result.closed, True)
        self.assertEqual(data, "data")

    def test_read(self):
        path = self._store("simple.txt", b"hello world")
        handle = open(path, "rb")

        try:
            self.pool.read(handle, count=5, data="data")

            self.assertEqual(
                self.pool.peek(), (file.FILE_WORK, file.READ_ACTION, handle, 5, "data")
            )

            self.thread.execute(self.pool.pop())

            action, result, data = self.pool.pop_event()

            self.assertEqual(action, file.READ_ACTION)
            self.assertEqual(result, b"hello")
            self.assertEqual(data, "data")
        finally:
            handle.close()

    def test_write(self):
        path = os.path.join(self.base, "target.txt")
        handle = open(path, "wb")

        try:
            self.pool.write(handle, b"hello world", data="data")

            self.assertEqual(
                self.pool.peek(),
                (file.FILE_WORK, file.WRITE_ACTION, handle, b"hello world", "data"),
            )

            self.thread.execute(self.pool.pop())

            action, result, data = self.pool.pop_event()

            # the buffer must reach the file, meaning that the work is
            # routed to the write method and not to the read one
            self.assertEqual(action, file.WRITE_ACTION)
            self.assertEqual(result, 11)
            self.assertEqual(data, "data")
        finally:
            handle.close()

        self.assertEqual(self._read("target.txt"), b"hello world")

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        handle = open(path, "wb")
        try:
            handle.write(contents)
        finally:
            handle.close()
        return path

    def _read(self, name):
        handle = open(os.path.join(self.base, name), "rb")
        try:
            return handle.read()
        finally:
            handle.close()
