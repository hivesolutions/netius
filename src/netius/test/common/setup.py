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
import unittest

import netius.common


class CommonTest(unittest.TestCase):

    def test__download_ca(self):
        if netius.conf("NO_NETWORK", False, cast=bool):
            self.skipTest("Network access is disabled")

        netius.common.ensure_ca(path="test.ca")
        file = open("test.ca", "rb")
        try:
            data = file.read()
        finally:
            file.close()
            os.unlink("test.ca")

        self.assertNotEqual(data, None)
        self.assertNotEqual(len(data), 0)
