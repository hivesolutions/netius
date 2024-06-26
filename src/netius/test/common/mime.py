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

import netius.common


class MimeTest(unittest.TestCase):

    def test_headers(self):
        headers = netius.common.mime.Headers()
        headers.set("Header", "Value")
        headers_s = headers.join()
        self.assertEqual(headers_s, b"Header: Value")

        headers = netius.common.mime.Headers()
        headers.set(b"Header", b"Value")
        headers_s = headers.join()
        self.assertEqual(headers_s, b"Header: Value")

        headers = netius.common.mime.Headers()
        headers.set(b"Header", netius.legacy.u("值").encode("utf-8"))
        headers_s = headers.join()
        self.assertEqual(headers_s, netius.legacy.u("Header: 值").encode("utf-8"))
