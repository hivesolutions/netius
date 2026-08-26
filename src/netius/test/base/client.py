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
from netius.base import request
from netius.base import client as client_c

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ClientTest(unittest.TestCase):

    def test_get_client_s(self):
        client = netius.DatagramClient.get_client_s(level=logging.CRITICAL)
        try:
            # the static client is a singleton, so that a second request for
            # it re-uses the instance that has already been built
            self.assertEqual(
                netius.DatagramClient.get_client_s(level=logging.CRITICAL), client
            )
            self.assertEqual(netius.DatagramClient._client, client)
        finally:
            netius.DatagramClient.cleanup_s()
            netius.DatagramClient._client = None

    def test_cleanup_s(self):
        # the cleanup of a class that never built a static client must be
        # a no operation instead of an error
        netius.DatagramClient._client = None
        netius.DatagramClient.cleanup_s()

        self.assertEqual(netius.DatagramClient._client, None)

    def test_ensure_loop(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        client = netius.DatagramClient(level=logging.CRITICAL)
        try:
            with mock.patch.object(client_c, "BaseThread") as thread_c:
                client.ensure_loop()

            # the thread that runs the loop is built lazily, only once an
            # operation that requires the loop has been requested
            self.assertEqual(thread_c.call_count, 1)
            self.assertEqual(thread_c.call_args[1]["owner"], client)
            self.assertEqual(thread_c.return_value.start.call_count, 1)
            self.assertEqual(client._thread, thread_c.return_value)

            with mock.patch.object(client_c, "BaseThread") as thread_c:
                client.ensure_loop()

            # a client that already has a loop thread must not build a new
            # one, as that would leave the first one orphaned
            self.assertEqual(thread_c.call_count, 0)
        finally:
            client._thread = None
            client.close()

    def test_ensure_loop_threadless(self):
        client = netius.DatagramClient(level=logging.CRITICAL, thread=False)
        try:
            # a client that is not meant to run in its own thread must never
            # build one, as the loop is driven by the caller instead
            client.ensure_loop()

            self.assertEqual(client._thread, None)
        finally:
            client.close()


class DatagramClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.DatagramClient(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.close()

    def test_keep_gc(self):
        # the garbage collection re-schedules itself so that it keeps being
        # run for as long as the client is alive
        self.client.keep_gc(timeout=60, run=False)

        self.assertEqual(len(self.client._delayed), 1)

    def test_keep_gc_run(self):
        expired = request.Request(timeout=-1)
        self.client.add_request(expired)

        # the collection may also be run right away, instead of only being
        # scheduled for a later moment in time
        self.client.keep_gc(timeout=60)

        self.assertEqual(self.client.requests, [])
        self.assertEqual(len(self.client._delayed), 1)

    def test_gc(self):
        expired = request.Request(timeout=-1)
        pending = request.Request(timeout=60)
        self.client.add_request(expired)
        self.client.add_request(pending)

        self.client.gc()

        # only the request that has timed out is dropped, the one that is
        # still within its timeout must be kept for a later response
        self.assertEqual(self.client.requests, [pending])
        self.assertEqual(self.client.requests_m, {pending.id: pending})

    def test_gc_empty(self):
        # a client with no pending requests has nothing to collect, so the
        # operation must return before any bookkeeping is done
        self.client.gc()

        self.assertEqual(self.client.requests, [])

    def test_gc_callback(self):
        called = []
        expired = request.Request(
            timeout=-1, callback=lambda result: called.append(result)
        )
        self.client.add_request(expired)

        self.client.gc()

        # the callback of a timed out request is called with an invalid
        # value, so that the caller is able to tell the request has failed
        self.assertEqual(called, [None])

    def test_gc_no_callbacks(self):
        called = []
        expired = request.Request(
            timeout=-1, callback=lambda result: called.append(result)
        )
        self.client.add_request(expired)

        self.client.gc(callbacks=False)

        self.assertEqual(called, [])
        self.assertEqual(self.client.requests, [])

    def test_add_request(self):
        item = request.Request()
        self.client.add_request(item)

        # the request is kept both in the sequence used by the garbage
        # collection and in the map used for the response matching
        self.assertEqual(self.client.requests, [item])
        self.assertEqual(self.client.requests_m, {item.id: item})

    def test_remove_request(self):
        item = request.Request()
        self.client.add_request(item)

        self.client.remove_request(item)

        self.assertEqual(self.client.requests, [])
        self.assertEqual(self.client.requests_m, {})

    def test_get_request(self):
        item = request.Request()
        self.client.add_request(item)

        self.assertEqual(self.client.get_request(item.id), item)

        # a response may be used in place of an identifier, as the identifier
        # of the request that originated it is carried by it
        response = _MockResponse(b"", request=item)

        self.assertEqual(self.client.get_request(response), item)

        # an identifier that matches no request must yield an invalid value
        # instead of raising, as a response may be an unsolicited one
        self.assertEqual(self.client.get_request(-1), None)

    def test_remove_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "unsub_write") as unsub_write:
            self.client.remove_write()

        self.assertEqual(unsub_write.call_count, 1)

    def test_enable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.renable = False

        with mock.patch.object(self.client, "sub_read") as sub_read:
            self.client.enable_read()

        self.assertEqual(self.client.renable, True)
        self.assertEqual(sub_read.call_count, 1)

    def test_enable_read_enabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # a client that is already reading must not be subscribed once again
        # as that would be a duplicated registration in the poll
        with mock.patch.object(self.client, "sub_read") as sub_read:
            self.client.enable_read()

        self.assertEqual(self.client.renable, True)
        self.assertEqual(sub_read.call_count, 0)

    def test_disable_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "unsub_read") as unsub_read:
            self.client.disable_read()

        self.assertEqual(self.client.renable, False)
        self.assertEqual(unsub_read.call_count, 1)

    def test_disable_read_disabled(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.client.renable = False

        with mock.patch.object(self.client, "unsub_read") as unsub_read:
            self.client.disable_read()

        self.assertEqual(self.client.renable, False)
        self.assertEqual(unsub_read.call_count, 0)


class StreamClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.StreamClient(level=logging.CRITICAL)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.close()

    def test_acquire_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        # a connection that is free in the pool must be re-used instead of
        # a new one being established for the same endpoint
        result = self.client.acquire_c("host", 80)

        self.assertEqual(result, connection)
        self.assertEqual(self.client.free_map[connection.tuple], [])

    def test_acquire_c_connect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.client, "connect") as connect:
            result = self.client.acquire_c("host", 80)

        # with no connection free in the pool a new one has to be established
        # and tagged with the endpoint it belongs to, for a later re-usage
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(result.tuple, ("host", 80, False, None, None))

    def test_acquire_c_invalid(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        with mock.patch.object(self.client, "validate_c", return_value=False):
            with mock.patch.object(self.client, "connect") as connect:
                result = self.client.acquire_c("host", 80, validate=True)

        # a pooled connection that no longer validates must be dropped and a
        # new connection established in its place
        self.assertNotEqual(result, connection)
        self.assertEqual(connect.call_count, 1)

    def test_release_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)

        self.client.release_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [connection])

    def test_release_c_untied(self):
        connection = self._make_connection()

        # a connection that has never been acquired through the pool has no
        # endpoint tuple, so releasing it must be ignored
        self.client.release_c(connection)

        self.assertEqual(self.client.free_map, {})

    def test_remove_c(self):
        connection = self._make_connection()
        connection.tuple = ("host", 80, False, None, None)
        self.client.release_c(connection)

        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [])

        # the removal of a connection that is no longer in the pool must be
        # a no operation, as it may have been removed by the closing of it
        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map[connection.tuple], [])

    def test_remove_c_untied(self):
        connection = self._make_connection()

        self.client.remove_c(connection)

        self.assertEqual(self.client.free_map, {})

    def test_acquire(self):
        connection = self._make_connection()

        # the acquire notification is deferred to the next tick, so that it's
        # never run in the middle of the acquiring of the connection
        self.client.acquire(connection)

        self.assertEqual(len(self.client._delayed), 1)

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

    def test_on_acquire(self):
        connection = self._make_connection()

        # the acquire and release notifications are extension points with no
        # default behaviour, so that a sub class may hook into them
        self.client.on_acquire(connection)
        self.client.on_release(connection)

        self.assertEqual(connection.status, conn.OPEN)

    def test_on_data(self):
        connection = self._make_connection()

        # the default handling of the data hands it over to the connection
        # so that it's dispatched through the data event
        received = []
        connection.bind("data", lambda _connection, data: received.append(data))
        self.client.on_data(connection, b"Hello World")

        self.assertEqual(received, [b"Hello World"])

    def _make_connection(self):
        # builds an open connection registered in the client, so that the
        # closing of it may be run over the complete set of structures
        _socket = socket.socket()
        connection = conn.BaseConnection(owner=self.client, socket=_socket)
        connection.status = conn.OPEN
        self.client.connections.append(connection)
        self.client.connections_m[_socket] = connection
        return connection


class _MockResponse(request.Response):

    def get_id(self):
        return self.request.id
