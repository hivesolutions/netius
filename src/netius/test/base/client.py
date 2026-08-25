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

import socket
import logging
import unittest

import netius

from netius.base import conn


class StreamClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.StreamClient(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.close()

    def test_on_exception(self):
        connection = self._make_connection()
        self.client.on_exception(netius.NetiusError("boom"), connection)

        # the closing must be identified as an error driven one, carrying
        # the details of the exception that has originated it
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "boom")

    def test_on_expected(self):
        connection = self._make_connection()
        self.client.on_expected(netius.NetiusError("broken pipe"), connection)

        # an expected exception is still an error driven closing, as the
        # connection was not closed by a decision of the upper layers
        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "broken pipe")

    def _make_connection(self):
        # builds an open connection registered in the client, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.client, socket=_socket)
        connection.status = conn.OPEN
        self.client.connections.append(connection)
        self.client.connections_m[_socket] = connection
        return connection
