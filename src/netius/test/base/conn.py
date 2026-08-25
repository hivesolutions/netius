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
import unittest

import netius

from netius.base import conn


class BaseConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.loop = netius.Base()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.loop.close()

    def test_close(self):
        connection = self._make_connection()

        # an open connection carries no closing information at all, as
        # the values are only set once the closing is performed
        self.assertEqual(connection.close_reason, None)
        self.assertEqual(connection.close_timestamp, None)

        connection.close()

        # a connection closed with no explicit reason must still be
        # identified, falling back to the unknown reason
        self.assertEqual(connection.close_reason, netius.REASON_UNKNOWN)
        self.assertNotEqual(connection.close_timestamp, None)

    def test_close_reason(self):
        connection = self._make_connection()
        connection.close_reason = netius.REASON_TIMEOUT
        connection.close()

        # the reason set before the closing must be preserved, as it's
        # more specific than the fallback one
        self.assertEqual(connection.close_reason, netius.REASON_TIMEOUT)

        # the closing of an already closed connection must not change any
        # of the values that describe the original closing
        timestamp = connection.close_timestamp
        connection.close()
        self.assertEqual(connection.close_reason, netius.REASON_TIMEOUT)
        self.assertEqual(connection.close_timestamp, timestamp)

    def test_close_reason_param(self):
        connection = self._make_connection()
        connection.close(reason=netius.REASON_ERROR, error="broken pipe")

        # the values provided to the closing must be associated with the
        # connection, sparing the caller from setting them before hand
        self.assertEqual(connection.close_reason, netius.REASON_ERROR)
        self.assertEqual(connection.close_error, "broken pipe")

        # a reason provided to the closing takes precedence over one that
        # was set before it, as it's the more immediate of the two
        connection = self._make_connection()
        connection.close_reason = netius.REASON_TIMEOUT
        connection.close(reason=netius.REASON_EXPLICIT)

        self.assertEqual(connection.close_reason, netius.REASON_EXPLICIT)

        # the closing of an already closed connection must not replace the
        # values that describe the original closing of it
        connection.close(reason=netius.REASON_ERROR)

        self.assertEqual(connection.close_reason, netius.REASON_EXPLICIT)

    def test_close_reason_flush(self):
        connection = self._make_connection()
        connection.close(flush=True, reason=netius.REASON_TIMEOUT)

        # the closing is deferred until the pending data is flushed, but the
        # reason must be kept so that it's available once it does happen
        self.assertEqual(connection.status, conn.OPEN)
        self.assertEqual(connection.close_reason, netius.REASON_TIMEOUT)

        connection.close()

        self.assertEqual(connection.status, conn.CLOSED)
        self.assertEqual(connection.close_reason, netius.REASON_TIMEOUT)

    def test_info_dict(self):
        connection = self._make_connection()
        info = connection.info_dict()

        self.assertEqual(info["close_reason"], None)
        self.assertEqual(info["close_error"], None)
        self.assertEqual(info["close_timestamp"], None)

        connection.close_reason = netius.REASON_ERROR
        connection.close_error = "broken pipe"
        connection.close()
        info = connection.info_dict()

        self.assertEqual(info["close_reason"], netius.REASON_ERROR)
        self.assertEqual(info["close_error"], "broken pipe")
        self.assertEqual(info["close_timestamp"], connection.close_timestamp)

    def _make_connection(self):
        # builds an open connection registered in the loop, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.loop, socket=_socket)
        connection.status = conn.OPEN
        self.loop.connections.append(connection)
        self.loop.connections_m[_socket] = connection
        return connection


class DiagConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.loop = netius.Base()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.loop.close()

    def test_info_dict(self):
        connection = self._make_connection()
        connection.last_recv_ts = 100.0
        connection.last_send_ts = 200.0
        info = connection.info_dict()

        self.assertEqual(info["last_activity_timestamp"], 200.0)

        # the geographical resolution is an expensive operation, so it must
        # only be performed for the full version of the information
        connection._resolve = lambda address: dict(country="PT")

        info = connection.info_dict()
        self.assertEqual("geo" in info, False)

        info = connection.info_dict(full=True)
        self.assertEqual(info["geo"], dict(country="PT"))

    def test__last_activity(self):
        connection = self._make_connection()

        # a connection with no activity at all has no timestamp to be
        # reported as the last activity one
        self.assertEqual(connection._last_activity(), None)

        # the most recent of the receive and send timestamps is the one
        # that represents the last activity of the connection
        connection.last_recv_ts = 100.0
        self.assertEqual(connection._last_activity(), 100.0)

        connection.last_send_ts = 200.0
        self.assertEqual(connection._last_activity(), 200.0)

        connection.last_recv_ts = 300.0
        self.assertEqual(connection._last_activity(), 300.0)

    def _make_connection(self):
        _socket = socket.socket()
        return conn.DiagConnection(owner=self.loop, socket=_socket)
