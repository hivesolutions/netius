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
import collections

import netius

from netius.base import conn
from netius.base import common


class BaseTest(unittest.TestCase):

    def test_unpend(self):
        loop = netius.Base()
        try:
            # a cancelled operation must no longer be considered a valid one
            # so that the callable associated with it is never called
            callable_t = loop.delay(lambda: None, timeout=60)
            loop.unpend(callable_t)
            self.assertEqual(callable_t[4][0], False)

            # the cancelling of an already cancelled operation must be a
            # no operation, so that it's not accounted for more than once
            loop.unpend(callable_t)
            self.assertEqual(loop._cancelled, 1)

            # an invalid callable tuple must be gracefully handled, as the
            # delay operation may not have returned a valid one
            loop.unpend(None)
            self.assertEqual(loop._cancelled, 1)
        finally:
            loop.close()

    def test_unpend_executed(self):
        loop = netius.Base()
        try:
            # an operation that has already been executed is no longer part
            # of the queues, so cancelling its handler must not be accounted
            # for as if it were still pending removal
            callable_t = loop.delay(lambda: None, timeout=60)
            loop._delayed = []
            loop._delayed_o = []
            loop.unpend(callable_t)
            self.assertEqual(loop._cancelled, 1)
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test_compact(self):
        loop = netius.Base()
        try:
            # the cancelled operations must be removed from the delayed
            # queues, keeping only the ones that are still valid
            valid = [loop.delay(lambda: None, timeout=60) for _index in range(10)]
            cancelled = [loop.delay(lambda: None, timeout=60) for _index in range(10)]
            for callable_t in cancelled:
                loop.unpend(callable_t)
            self.assertEqual(len(loop._delayed), 20)

            loop.compact()

            self.assertEqual(len(loop._delayed), 10)
            self.assertEqual(len(loop._delayed_o), 10)
            self.assertEqual(loop._cancelled, 0)
            self.assertEqual(all(callable_t[4][0] for callable_t in valid), True)
        finally:
            loop.close()

    def test_unpend_compact(self):
        loop = netius.Base()
        try:
            # the queues must be compacted on their own once enough of the
            # operations in them have been cancelled, so that a cancelled
            # operation does not occupy the queue until its target time
            callables = [
                loop.delay(lambda: None, timeout=60)
                for _index in range(common.COMPACT_MIN * 2)
            ]
            for callable_t in callables:
                loop.unpend(callable_t)

            self.assertEqual(len(loop._delayed), 0)
            self.assertEqual(loop._cancelled, 0)
        finally:
            loop.close()

    def test__delays(self):
        loop = netius.Base()
        try:
            fired = []
            loop.delay(lambda: fired.append("due"), timeout=-1)
            loop.delay(lambda: fired.append("late"), timeout=30)

            # only the operation that is already due may be run, the one that
            # is still pending must be kept in the queue untouched
            loop._delays()
            self.assertEqual(fired, ["due"])
            self.assertEqual(len(loop._delayed), 1)

            # a new iteration with nothing due must not run anything, note
            # that the pending operation must remain in the queue
            loop._delays()
            self.assertEqual(fired, ["due"])
            self.assertEqual(len(loop._delayed), 1)
            self.assertEqual(len(loop._delayed_o), 1)
        finally:
            loop.close()

    def test_resolve_hostname(self):
        loop = netius.get_main()
        future = loop.resolve_hostname("gmail.com")
        result = loop.run_coroutine(future)
        loop.close()

        self.assertNotEqual(result, None)
        self.assertEqual(isinstance(result, str), True)

    def test_record_closed(self):
        loop = netius.Base()
        buffer = common.AbstractBase._DIAG_CLOSED
        try:
            buffer.clear()

            # a connection that keeps track of its creation must have the
            # duration of it calculated from the closing timestamp
            connection = self._make_connection(loop, diag=True)
            connection.creation = connection.close_timestamp - 2.0
            connection.close_paired = "other"
            connection.recvs = 3
            connection.sends = 2
            connection.in_bytes = 512
            connection.out_bytes = 1024
            connection.last_recv_ts = connection.close_timestamp - 1.0
            loop.record_closed(connection)

            self.assertEqual(len(buffer), 1)
            self.assertEqual(buffer[0]["id"], connection.id)
            self.assertEqual(buffer[0]["close_reason"], netius.REASON_TIMEOUT)
            self.assertEqual(buffer[0]["close_error"], "idle")
            self.assertEqual(buffer[0]["close_paired"], "other")
            self.assertEqual(buffer[0]["duration"], 2.0)

            # the record must reflect the values of the connection at the
            # moment it was taken, so they are verified one by one
            self.assertEqual(buffer[0]["status"], connection.status)
            self.assertEqual(buffer[0]["recvs"], connection.recvs)
            self.assertEqual(buffer[0]["sends"], connection.sends)
            self.assertEqual(buffer[0]["in_bytes"], connection.in_bytes)
            self.assertEqual(buffer[0]["out_bytes"], connection.out_bytes)
            self.assertEqual(buffer[0]["close_timestamp"], connection.close_timestamp)
            self.assertEqual(
                buffer[0]["last_activity_timestamp"], connection._last_activity()
            )

            # the duration must be the exact distance between the creation
            # and the closing of the connection
            self.assertEqual(
                buffer[0]["duration"],
                connection.close_timestamp - connection.creation,
            )

            # the record is detached from the connection, so a change in the
            # latter must never be reflected in the value already stored
            connection.close_reason = netius.REASON_ERROR
            connection.in_bytes = 0

            self.assertEqual(buffer[0]["close_reason"], netius.REASON_TIMEOUT)
            self.assertEqual(buffer[0]["in_bytes"], 512)

            # a connection with no creation time has no duration associated
            # with it, as there's no value from which to measure it
            connection = self._make_connection(loop)
            loop.record_closed(connection)

            self.assertEqual(len(buffer), 2)
            self.assertEqual(buffer[1]["duration"], None)
            self.assertEqual(buffer[1]["close_paired"], None)
        finally:
            buffer.clear()
            loop.close()

    def test_connections_closed_dict(self):
        loop = netius.Base()
        original = common.AbstractBase._DIAG_CLOSED
        try:
            # replaces the ring buffer by a smaller one so that the bound
            # of it may be verified without a large number of entries
            common.AbstractBase._DIAG_CLOSED = collections.deque(maxlen=2)

            first = self._make_connection(loop)
            second = self._make_connection(loop)
            loop.record_closed(first)
            loop.record_closed(second)

            # the most recently closed connection must be the first one to
            # be reported, so that the latest events are the visible ones
            closed = loop.connections_closed_dict()
            self.assertEqual([info["id"] for info in closed], [second.id, first.id])

            # once the maximum number of entries is reached the oldest of
            # them must be dropped, keeping the memory usage bounded
            third = self._make_connection(loop)
            loop.record_closed(third)

            closed = loop.connections_closed_dict()
            self.assertEqual(len(closed), 2)
            self.assertEqual([info["id"] for info in closed], [third.id, second.id])
        finally:
            common.AbstractBase._DIAG_CLOSED = original
            loop.close()

    def _make_connection(self, loop, diag=False):
        # builds a closed connection registered in the loop, so that it may
        # be recorded in the ring buffer of closed connections
        _socket = socket.socket()
        cls = conn.DiagConnection if diag else conn.BaseConnection
        connection = cls(owner=loop, socket=_socket)
        connection.status = conn.OPEN
        loop.connections.append(connection)
        loop.connections_m[_socket] = connection
        connection.close_reason = netius.REASON_TIMEOUT
        connection.close_error = "idle"
        connection.close()
        return connection
