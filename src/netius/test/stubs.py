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
import ast
import sys
import unittest

import netius

EXCLUDED = ("examples", "test")
""" The sequence of packages that are not part of the public interface
of netius and for that reason are not expected to be typed """


class StubsTest(unittest.TestCase):

    def test_py_typed(self):
        base_path = os.path.dirname(netius.__file__)
        marker_path = os.path.join(base_path, "py.typed")

        # the PEP 561 marker is the only way a type checker is able to
        # tell that the stubs bundled with the package are to be used
        self.assertEqual(os.path.isfile(marker_path), True)

    def test_stubs_module(self):
        orphan = [path for path in self._stubs() if not os.path.isfile(path[:-1])]

        self.assertEqual(orphan, [])

    def test_stubs_complete(self):
        missing = [path for path in self._modules() if not os.path.isfile(path + "i")]

        self.assertEqual(missing, [])

    def test_stubs_syntax(self):
        # the stubs declare the type of the attributes using the variable
        # annotation syntax, which is only understood from Python 3.6 onwards
        if sys.version_info < (3, 6):
            self.skipTest("Skipping test: stub syntax requires Python 3.6")

        for path in self._stubs():
            ast.parse(self._read(path), path)

    def test_stubs_newlines(self):
        invalid = [
            path
            for path in self._stubs()
            if b"\n" in self._read(path).replace(b"\r\n", b"")
        ]

        self.assertEqual(invalid, [])

    def _modules(self):
        return self._walk(".py")

    def _stubs(self):
        return self._walk(".pyi")

    def _walk(self, extension):
        paths = []
        base_path = os.path.dirname(netius.__file__)
        for root, directories, files in os.walk(base_path):
            directories[:] = [
                directory
                for directory in directories
                if not directory in EXCLUDED and not directory == "__pycache__"
            ]
            for name in files:
                if not name.endswith(extension):
                    continue
                if name == "__init__.py":
                    continue
                paths.append(os.path.join(root, name))
        return sorted(paths)

    def _read(self, path):
        file = open(path, "rb")
        try:
            return file.read()
        finally:
            file.close()
