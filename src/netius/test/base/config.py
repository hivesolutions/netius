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

import unittest

import netius

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ConfigTest(unittest.TestCase):

    def test_basic(self):
        netius.conf_s("NAME", "name")
        result = netius.conf("NAME")

        self.assertEqual(result, "name")

        result = netius.conf("NAME", cast=str)

        self.assertEqual(result, "name")
        self.assertEqual(type(result), str)

        result = netius.conf("NAME", cast="str")

        self.assertEqual(result, "name")
        self.assertEqual(type(result), str)

        netius.conf_s("AGE", "10")
        result = netius.conf("AGE", cast=int)

        self.assertEqual(result, 10)
        self.assertEqual(type(result), int)

        result = netius.conf("AGE", cast="int")

        self.assertEqual(result, 10)
        self.assertEqual(type(result), int)

        result = netius.conf("AGE", cast=str)

        self.assertEqual(result, "10")
        self.assertEqual(type(result), str)

        result = netius.conf("HEIGHT")

        self.assertEqual(result, None)

    def test_none(self):
        netius.conf_s("AGE", None)
        result = netius.conf("AGE", cast=int)

        self.assertEqual(result, None)

        result = netius.conf("HEIGHT", cast=int)

        self.assertEqual(result, None)

    def test_load_dot_env(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        mock_data = mock.mock_open(
            read_data=b"#This is a comment\nAGE=10\nNAME=colony\n"
        )

        with mock.patch("os.path.exists", return_value=True), mock.patch(
            "builtins.open", mock_data, create=True
        ) as mock_open:
            ctx = dict(configs={}, config_f=[])

            netius.config.load_dot_env(".env", "utf-8", ctx)

            result = netius.conf("AGE", cast=int)
            self.assertEqual(type(result), int)
            self.assertEqual(result, 10)

            result = netius.conf("AGE", cast=str)

            self.assertEqual(result, "10")
            self.assertEqual(type(result), str)

            result = netius.conf("HEIGHT", cast=int)
            self.assertEqual(result, None)

            self.assertEqual(len(ctx["configs"]), 2)

            self.assertEqual(mock_open.return_value.close.call_count, 1)
