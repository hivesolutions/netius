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

import time
import socket
import unittest

import netius
import netius.common

from netius.base import conn

try:
    import unittest.mock as mock
except ImportError:
    mock = None


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

    def test_isolation(self):
        first = self._make_connection(payload=b"hello")
        second = self._make_connection(payload=b"hello")
        first.status = conn.OPEN
        second.status = conn.OPEN

        first.recv()
        first.send(b"abc")

        # the accounting is kept per connection, so the operations of one
        # of them must never be reflected in another one
        self.assertEqual(second.recvs, 0)
        self.assertEqual(second.sends, 0)
        self.assertEqual(second.in_bytes, 0)
        self.assertEqual(second.out_bytes, 0)
        self.assertEqual(second.last_recv_ts, None)
        self.assertEqual(second.last_send_ts, None)

        # the identifiers of the connections must also be distinct, as they
        # are what correlates a record with the connection it describes
        self.assertNotEqual(first.id, second.id)

    def test_recv(self):
        connection = self._make_connection(payload=b"hello")

        # a connection that has not received anything reports no receive
        # operations and no bytes accounted for them
        self.assertEqual(connection.recvs, 0)
        self.assertEqual(connection.in_bytes, 0)
        self.assertEqual(connection.last_recv_ts, None)

        # a receive on a connection that is not open reports no data, but
        # it's still accounted as an operation over the connection
        self.assertEqual(connection.recv(), b"")
        self.assertEqual(connection.recvs, 1)
        self.assertEqual(connection.in_bytes, 0)
        self.assertNotEqual(connection.last_recv_ts, None)

        # the data of an open connection must be both returned to the caller
        # and accumulated in the total of the received bytes
        connection.status = conn.OPEN

        self.assertEqual(connection.recv(), b"hello")
        self.assertEqual(connection.recvs, 2)
        self.assertEqual(connection.in_bytes, 5)

        self.assertEqual(connection.recv(), b"hello")
        self.assertEqual(connection.recvs, 3)
        self.assertEqual(connection.in_bytes, 10)

    def test_recv_partial(self):
        payload = b"0123456789"
        connection = self._make_connection(payload=payload)
        connection.status = conn.OPEN

        # a receive that is bound by a size smaller than the payload must
        # account only for the bytes that have effectively been returned
        data = connection.recv(size=4)

        self.assertEqual(data, payload[:4])
        self.assertEqual(connection.in_bytes, 4)

        # the accounting must follow the size of every operation, so that
        # the total matches the sum of the bytes that were returned
        total = 4
        for size in (1, 2, 3, 10):
            data = connection.recv(size=size)
            total += len(data)
            self.assertEqual(len(data), min(size, len(payload)))
            self.assertEqual(connection.in_bytes, total)

        self.assertEqual(connection.recvs, 5)

    def test_send(self):
        connection = self._make_connection()
        connection.status = conn.OPEN

        # a connection that has not sent anything reports no send operations
        # and no bytes accounted for them
        self.assertEqual(connection.sends, 0)
        self.assertEqual(connection.out_bytes, 0)
        self.assertEqual(connection.last_send_ts, None)

        # the number of bytes reported by the send operation is the one that
        # gets accumulated in the total of the sent bytes
        self.assertEqual(connection.send(b"abc"), 3)
        self.assertEqual(connection.sends, 1)
        self.assertEqual(connection.out_bytes, 3)
        self.assertNotEqual(connection.last_send_ts, None)

        connection.send(b"de")

        self.assertEqual(connection.sends, 2)
        self.assertEqual(connection.out_bytes, 5)

    def test_send_sequence(self):
        connection = self._make_connection()
        connection.status = conn.OPEN

        # the total of the sent bytes must match the sum of the payloads
        # that were sent, independently of how they are split
        payloads = [b"a", b"bc", b"def", b"g" * 128, b"h" * 4096]
        for payload in payloads:
            connection.send(payload)

        self.assertEqual(connection.sends, len(payloads))
        self.assertEqual(connection.out_bytes, sum(len(p) for p in payloads))

        # the accounted bytes are the ones handed to the connection and not
        # the ones already written to the socket, as the writing is deferred
        # to the event loop, so they must match the pending amount
        self.assertEqual(connection.out_bytes, connection.pending_s)
        self.assertEqual(connection.socket.sent, [])

    def test_info_dict(self):
        connection = self._make_connection()
        connection.last_recv_ts = 100.0
        connection.last_send_ts = 200.0
        info = connection.info_dict()

        self.assertEqual(info["last_activity_timestamp"], 200.0)

        # the accounting of the connection must be part of the information,
        # as it's the basis for the diagnostics of the traffic in it
        connection.status = conn.OPEN
        connection.recv()
        connection.send(b"abc")
        info = connection.info_dict()

        self.assertEqual(info["recvs"], 1)
        self.assertEqual(info["sends"], 1)
        self.assertEqual(info["in_bytes"], 0)
        self.assertEqual(info["out_bytes"], 3)
        self.assertEqual(info["uptime"], connection._uptime())
        self.assertEqual(info["last_recv_ts"], connection.last_recv_ts)
        self.assertEqual(info["last_send_ts"], connection.last_send_ts)

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

    def test__last_activity_bounds(self):
        connection = self._make_connection(payload=b"hello")
        connection.status = conn.OPEN

        connection.recv()
        connection.send(b"abc")
        connection.close(reason=netius.REASON_EXPLICIT)

        # every timestamp of the connection must fall inside its lifetime,
        # so that the reported activity is coherent with it
        self.assertEqual(connection.creation <= connection.last_recv_ts, True)
        self.assertEqual(connection.last_recv_ts <= connection.last_send_ts, True)
        self.assertEqual(connection.last_send_ts <= connection.close_timestamp, True)

        # the last activity is the most recent of the two operations, which
        # in this case is the sending one
        self.assertEqual(connection._last_activity(), connection.last_send_ts)

    def test__uptime(self):
        connection = self._make_connection()

        # a connection created right now has no measurable uptime, so only
        # the seconds component is reported for it
        self.assertEqual(connection._uptime(), "0s")

        # only the two most significant components are reported, meaning
        # that the seconds are dropped once there are larger ones
        connection.creation = time.time() - 3661
        self.assertEqual(connection._uptime(), "1h 1m")

        connection.creation = time.time() - 90000
        self.assertEqual(connection._uptime(), "1d 1h")

        # the resolution of the clocks may place the creation of the
        # connection after the current time, which must not be reported
        # as an almost complete day of uptime
        connection.creation = time.time() + 60
        self.assertEqual(connection._uptime(), "0s")

    def test__resolve(self):
        connection = self._make_connection()

        # an unset address carries no geographical information, so no
        # resolution is attempted for it
        self.assertEqual(connection._resolve(None), None)

        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the resolution is delegated to the geo resolver using only the
        # host part of the address, as the port is not relevant for it
        with mock.patch.object(
            netius.common.GeoResolver, "resolve", return_value=dict(country="PT")
        ) as resolve:
            result = connection._resolve(("8.8.8.8", 80))

        self.assertEqual(result, dict(country="PT"))
        self.assertEqual(resolve.call_args[0], ("8.8.8.8",))

    def _make_connection(self, payload=b""):
        # builds a connection over a socket stand-in that reports the
        # provided payload on receive and accumulates what is sent through
        # it, sparing the tests from any real network usage
        class Socket(object):

            def __init__(self):
                self.sent = []

            def recv(self, size):
                return payload[:size]

            def send(self, data):
                self.sent.append(data)
                return len(data)

            def close(self):
                pass

            def fileno(self):
                return 0

        return conn.DiagConnection(owner=self.loop, socket=Socket())
