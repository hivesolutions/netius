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

from netius.base.mixin import ConnectionCompat


class ConnectionCompatTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.connection = _MockConnection()
        self.compat = _MockCompat(self.connection)
        self.compat_none = _MockCompat(None)

    def test_id(self):
        self.connection.id = "abc-123"
        self.assertEqual(self.compat.id, "abc-123")

    def test_id_no_connection(self):
        self.assertEqual(self.compat_none.id, None)

    def test_socket(self):
        self.connection.socket = "mock-socket"
        self.assertEqual(self.compat.socket, "mock-socket")

    def test_socket_no_connection(self):
        self.assertEqual(self.compat_none.socket, None)

    def test_address(self):
        self.connection.address = ("127.0.0.1", 8080)
        self.assertEqual(self.compat.address, ("127.0.0.1", 8080))

    def test_address_setter(self):
        self.compat.address = ("10.0.0.1", 9090)
        self.assertEqual(self.connection.address, ("10.0.0.1", 9090))
        self.assertEqual(self.compat._address, ("10.0.0.1", 9090))

    def test_address_no_connection(self):
        self.compat_none.address = ("10.0.0.1", 9090)
        self.assertEqual(self.compat_none.address, ("10.0.0.1", 9090))

    def test_status(self):
        self.connection.status = 1
        self.assertEqual(self.compat.status, 1)

    def test_status_setter(self):
        self.compat.status = 2
        self.assertEqual(self.connection.status, 2)

    def test_status_no_connection(self):
        self.compat_none.status = 1
        self.assertEqual(self.compat_none.status, 1)

    def test_renable(self):
        self.connection.renable = False
        self.assertEqual(self.compat.renable, False)

    def test_renable_no_connection(self):
        self.assertEqual(self.compat_none.renable, True)

    def test_is_throttleable(self):
        self.connection._throttleable = True
        self.assertEqual(self.compat.is_throttleable(), True)

    def test_is_throttleable_no_connection(self):
        self.assertEqual(self.compat_none.is_throttleable(), False)

    def test_is_exhausted(self):
        self.connection._exhausted = True
        self.assertEqual(self.compat.is_exhausted(), True)

    def test_is_exhausted_no_connection(self):
        self.assertEqual(self.compat_none.is_exhausted(), False)

    def test_is_restored(self):
        self.connection._restored = False
        self.assertEqual(self.compat.is_restored(), False)

    def test_is_restored_no_connection(self):
        self.assertEqual(self.compat_none.is_restored(), True)

    def test_disable_read(self):
        self.compat.disable_read()
        self.assertEqual(self.connection._read_disabled, True)

    def test_enable_read(self):
        self.connection._read_disabled = True
        self.compat.enable_read()
        self.assertEqual(self.connection._read_disabled, False)

    def test_max_pending(self):
        self.connection.max_pending = 65536
        self.assertEqual(self.compat.max_pending, 65536)

    def test_max_pending_setter(self):
        self.compat.max_pending = 32768
        self.assertEqual(self.connection.max_pending, 32768)
        self.assertEqual(self.compat._max_pending, 32768)

    def test_max_pending_no_connection(self):
        self.compat_none.max_pending = 32768
        self.assertEqual(self.compat_none.max_pending, 32768)

    def test_min_pending(self):
        self.connection.min_pending = 4096
        self.assertEqual(self.compat.min_pending, 4096)

    def test_min_pending_setter(self):
        self.compat.min_pending = 2048
        self.assertEqual(self.connection.min_pending, 2048)
        self.assertEqual(self.compat._min_pending, 2048)

    def test_min_pending_no_connection(self):
        self.compat_none.min_pending = 2048
        self.assertEqual(self.compat_none.min_pending, 2048)

    def test_waiting(self):
        self.connection.waiting = True
        self.assertEqual(self.compat.waiting, True)

    def test_waiting_setter(self):
        self.compat.waiting = True
        self.assertEqual(self.connection.waiting, True)
        self.assertEqual(self.compat._waiting, True)

    def test_waiting_no_connection(self):
        self.compat_none.waiting = True
        self.assertEqual(self.compat_none.waiting, True)

    def test_waiting_default(self):
        self.assertEqual(self.compat.waiting, False)

    def test_busy(self):
        self.connection.busy = 3
        self.assertEqual(self.compat.busy, 3)

    def test_busy_setter(self):
        self.compat.busy = 2
        self.assertEqual(self.connection.busy, 2)
        self.assertEqual(self.compat._busy, 2)

    def test_busy_no_connection(self):
        self.compat_none.busy = 5
        self.assertEqual(self.compat_none.busy, 5)

    def test_busy_default(self):
        self.assertEqual(self.compat.busy, 0)

    def test_state(self):
        self.connection.state = "robin"
        self.assertEqual(self.compat.state, "robin")

    def test_state_setter(self):
        self.compat.state = "smart"
        self.assertEqual(self.connection.state, "smart")
        self.assertEqual(self.compat._state, "smart")

    def test_state_no_connection(self):
        self.compat_none.state = "robin"
        self.assertEqual(self.compat_none.state, "robin")

    def test_state_default(self):
        self.assertEqual(self.compat.state, None)

    def test_error_url(self):
        self.connection.error_url = "/error.html"
        self.assertEqual(self.compat.error_url, "/error.html")

    def test_error_url_setter(self):
        self.compat.error_url = "/fallback.html"
        self.assertEqual(self.connection.error_url, "/fallback.html")
        self.assertEqual(self.compat._error_url, "/fallback.html")

    def test_error_url_no_connection(self):
        self.compat_none.error_url = "/error.html"
        self.assertEqual(self.compat_none.error_url, "/error.html")

    def test_error_url_default(self):
        self.assertEqual(self.compat.error_url, None)


class _MockConnection(object):

    def __init__(self):
        self.id = None
        self.socket = None
        self.address = None
        self.status = 0
        self.renable = True
        self.max_pending = -1
        self.min_pending = -1
        self._throttleable = False
        self._exhausted = False
        self._restored = True
        self._read_disabled = False

    def is_throttleable(self):
        return self._throttleable

    def is_exhausted(self):
        return self._exhausted

    def is_restored(self):
        return self._restored

    def disable_read(self):
        self._read_disabled = True

    def enable_read(self):
        self._read_disabled = False


class _MockCompat(ConnectionCompat):

    def __init__(self, connection):
        self._connection = connection

    @property
    def connection(self):
        return self._connection
