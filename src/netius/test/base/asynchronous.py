#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius

class AsynchronousTest(unittest.TestCase):

    def test_basic(self):
        loop = netius.get_loop(asyncio = False)

        self.assertNotEqual(loop, None)
        self.assertEqual(isinstance(loop, netius.Base), True)

        future = netius.build_future(compat = False, asyncio = False)

        self.assertNotEqual(future, None)
        self.assertEqual(isinstance(future, netius.Future), True)
        self.assertNotEqual(future._loop, None)
        self.assertEqual(isinstance(future._loop, netius.Base), True)

        previous = loop
        loop = netius.get_loop(_compat = True)

        self.assertNotEqual(loop, None)

        self.assertEqual(isinstance(loop, netius.BaseLoop), True)
        self.assertEqual(isinstance(loop, netius.CompatLoop), True)
        self.assertEqual(loop, previous._compat)
        self.assertEqual(loop._loop_ref(), previous)

        loop = netius.get_loop(asyncio = True)

        self.assertNotEqual(loop, None)

        if netius.is_asynclib():
            self.assertEqual(isinstance(loop, netius.BaseLoop), True)
            self.assertEqual(isinstance(loop, netius.CompatLoop), True)
        else:
            self.assertEqual(isinstance(loop, netius.Base), True)

    @netius.async_test
    def test_sleep(self):
        for value in netius.sleep(1.0):
            yield value
            future = value
        timeout = future.result()

        self.assertEqual(timeout, 1.0)
        self.assertEqual(isinstance(future, netius.Future), True)
        self.assertEqual(future.done(), True)
