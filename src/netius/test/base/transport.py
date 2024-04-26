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


class TransportTest(unittest.TestCase):

    def test_write_closing(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        self.assertEqual(transport._loop, None)
        self.assertEqual(transport._connection, connection)
        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(connection.is_closed(), False)

        connection.status = netius.CLOSED

        self.assertEqual(transport._loop, None)
        self.assertEqual(transport._connection, connection)
        self.assertEqual(transport.is_closing(), True)
        self.assertEqual(connection.is_closed(), True)

        transport.write(b"")
