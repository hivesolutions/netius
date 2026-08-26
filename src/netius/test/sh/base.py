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

import sys
import unittest

import netius.sh.base

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class SHBaseTest(unittest.TestCase):

    def test_sh_call(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        method = mock.Mock()

        with mock.patch.object(sys, "argv", ["sh", "method", "first", "second"]):
            netius.sh.base.sh_call(dict(method=method))

        # the first argument selects the method to be run and the remaining
        # ones are forwarded to it as the plain strings coming from the shell
        self.assertEqual(method.call_count, 1)
        self.assertEqual(method.call_args[0], ("first", "second"))

    def test_sh_call_no_extra(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        method = mock.Mock()

        with mock.patch.object(sys, "argv", ["sh", "method"]):
            netius.sh.base.sh_call(dict(method=method))

        self.assertEqual(method.call_count, 1)
        self.assertEqual(method.call_args[0], ())

    def test_sh_call_no_method(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(sys, "argv", ["sh"]):
            self.assertRaises(RuntimeError, netius.sh.base.sh_call, dict())

    def test_sh_call_unknown(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(sys, "argv", ["sh", "unknown"]):
            self.assertRaises(KeyError, netius.sh.base.sh_call, dict())

    def test_sh_call_locals(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        method = mock.Mock()

        # the locals are only accepted so that the caller may hand over the
        # complete namespace, the method is always resolved from the globals
        with mock.patch.object(sys, "argv", ["sh", "method"]):
            self.assertRaises(
                KeyError, netius.sh.base.sh_call, dict(), dict(method=method)
            )

        self.assertEqual(method.call_count, 0)
