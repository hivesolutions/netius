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
import netius.common
import netius.servers

REQUEST = b"GET /hello?name=world HTTP/1.1\r\nHost: netius.hive.pt\r\n\r\n"
""" The raw contents of a simple request to be used as the
base one for the majority of the tests """


class ReturnIterator(object):
    """
    Iterator that delivers its payload through the return value
    of the stop iteration exception, the same way that a generator
    that returns a value does under the Python 3 infra-structure.
    """

    def __init__(self, value):
        self.value = value
        self.raised = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.raised:
            raise StopIteration()
        self.raised = True
        raise StopIteration(self.value)

    next = __next__


class LengthIterator(object):
    """
    Iterator that is its own iterable and reports the number of
    values that it still holds, the shape of a response wrapper
    that becomes a falsy value once it has been exhausted.
    """

    def __init__(self, values):
        self.values = list(values)

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.values)

    def __next__(self):
        if not self.values:
            raise StopIteration()
        return self.values.pop(0)

    next = __next__


class WSGIServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.servers = []
        self.connections = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for connection in self.connections:
            connection.parser.destroy()
        for server in self.servers:
            server.cleanup()

    def test_on_connection_d(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        connection.parse(REQUEST)
        iterator = connection.iterator

        server.on_connection_d(connection)

        # the destruction of a connection releases the request that it was
        # handling together with the queue of the ones that were pending,
        # so that nothing is kept alive by a connection that is gone
        self.assertEqual(connection.iterator, None)
        self.assertEqual(connection.environ, None)
        self.assertEqual(connection.queue, [])
        self.assertRaises(StopIteration, next, iterator)

    def test_on_data_http(self):
        server = self._make_server()
        connection = self._make_connection(server)

        connection.parse(REQUEST)

        # the complete handling of the request must produce the response of
        # the application and release the connection at the end of it
        self.assertEqual(self._data(connection).count(b"Hello World"), 1)
        self.assertEqual(connection.iterator, None)
        self.assertEqual(connection.environ, None)

    def test_on_data_http_queue(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)

        connection.parse(REQUEST)
        connection.parse(REQUEST)

        # a request that arrives while another one is still being handled
        # is queued, so that the pipelining of them is possible
        self.assertEqual(len(connection.queue), 1)
        self.assertEqual(connection.queue[0]["PATH_INFO"], "/hello")

        connection.parse(REQUEST)

        # the queue is a shared one, so the requests that follow are
        # appended to the one that already exists
        self.assertEqual(len(connection.queue), 2)

    def test_on_data_http_pending(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)

        connection.parse(REQUEST)
        self._deliver(connection)

        # the application has been exhausted but the flushing of the response
        # is still pending, so the connection is not yet a free one
        self.assertNotEqual(connection.iterator, None)

        connection.parse(REQUEST)

        # a request that arrives while the response of the previous one has
        # not been released must be queued, as the releasing of it would
        # otherwise close the iterator of the request that took its place
        self.assertEqual(len(connection.queue), 1)

        self._deliver(connection)

        # the releasing of the response dispatches the queued request, whose
        # response must reach the client as well (no request is lost)
        self.assertEqual(connection.queue, [])
        self.assertEqual(self._data(connection).count(b"Hello World"), 2)

    def test_on_environ(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        environ = connection.environ

        # the starting of a request keeps both the iterator and the map of
        # environment in the connection, marking it as a busy one
        self.assertNotEqual(connection.iterator, None)
        self.assertEqual(environ["REQUEST_METHOD"], "GET")
        self.assertEqual(environ["PATH_INFO"], "/hello")
        self.assertEqual(environ["QUERY_STRING"], "name=world")

    def test__next_queue(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)

        # a connection with no queue at all and one with an empty queue are
        # both a no operation, leaving the connection untouched
        server._next_queue(connection)
        self.assertEqual(hasattr(connection, "iterator"), False)

        connection.queue = []
        server._next_queue(connection)
        self.assertEqual(hasattr(connection, "iterator"), False)

    def test__send_part(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)

        # the first part of the response carries the payload of the
        # application, the iterator being kept for the next part
        self.assertEqual(self._data(connection).count(b"Hello World"), 1)
        self.assertNotEqual(connection.iterator, None)

        self._deliver(connection)

        # the exhaustion of the application does not release the iterator,
        # as the connection is only free once the response is flushed
        self.assertNotEqual(connection.iterator, None)

    def test__send_part_return(self):
        server = self._make_server(app=self._app_return)
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)

        # the payload carried by the stop iteration is sent as the last
        # part of the response, the iterator being kept for the flush
        self.assertEqual(self._data(connection).count(b"Hello World"), 1)
        self.assertNotEqual(connection.iterator, None)

        self._deliver(connection)
        self._deliver(connection)

        # the exhaustion of the iterator that follows completes the response
        # and releases the connection for the request that comes next
        self.assertEqual(connection.iterator, None)

    def test__send_part_stale(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)

        # retains the callback of the request that is in flight and then
        # releases the connection, as the closing of it would, so that a
        # new request is able to take the place of the previous one
        stale = connection.callbacks.pop()
        server._release(connection)
        self.assertEqual(connection.iterator, None)

        # a new request takes the connection and starts producing its own
        # response, which the stale callback must not be allowed to touch
        connection.parse(REQUEST)
        count = len(connection.data)

        stale(connection)

        # the stale callback belongs to a request that has already been
        # released, so it must not advance the iterator of the one that
        # took its place, no extra data reaching the client
        self.assertEqual(len(connection.data), count)

    def test__send_part_stale_empty(self):
        server = self._make_server(app=self._app_length)
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)

        # retains the callback of the request that is in flight and then
        # releases the connection, note that the iterator of it has been
        # exhausted, which makes a wrapper that reports its length falsy
        stale = connection.callbacks.pop()
        server._release(connection)

        connection.parse(REQUEST)
        count = len(connection.data)

        stale(connection)

        # the emptiness of a response is unrelated to the ownership of the
        # connection, so the stale callback must be stopped by the guard
        # even though its iterator no longer evaluates to true
        self.assertEqual(len(connection.data), count)

    def test__final(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        self._deliver(connection)
        self._deliver(connection)

        # the flushing of the response releases the connection, so that it
        # becomes a free one, ready to handle a new request
        self.assertEqual(connection.iterator, None)
        self.assertEqual(connection.environ, None)
        self.assertEqual(connection.closed, False)

    def test__final_close(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        connection.parser.keep_alive = False
        self._deliver(connection)
        self._deliver(connection)

        # a connection that is not meant to be kept alive is closed instead
        # of being released for the handling of a new request
        self.assertEqual(connection.closed, True)

    def test__final_stale(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        self._deliver(connection)

        # retains the flush callback of the request that is in flight and
        # then releases the connection, as the closing of it would, so that
        # a new request is able to take the place of the previous one
        stale = connection.callbacks.pop()
        server._release(connection)

        # a new request takes the connection and starts producing its own
        # response, which the stale callback must not be allowed to release
        connection.parse(REQUEST)
        iterator = connection.iterator

        stale(connection)

        # the stale callback belongs to a request that has already been
        # released, so the one that took its place must survive it
        self.assertEqual(connection.iterator, iterator)
        self.assertNotEqual(connection.environ, None)

    def test__final_stale_empty(self):
        server = self._make_server(app=self._app_length)
        connection = self._make_connection(server, deliver=False)
        connection.parse(REQUEST)
        self._deliver(connection)

        # retains the flush callback of the request that is in flight, whose
        # iterator has been exhausted and is therefore a falsy value
        stale = connection.callbacks.pop()
        server._release(connection)

        connection.parse(REQUEST)
        iterator = connection.iterator

        stale(connection)

        # the request that took the place of the previous one must survive
        # the stale callback, the guard not being skipped by an iterator
        # that no longer evaluates to true
        self.assertEqual(connection.iterator, iterator)
        self.assertNotEqual(connection.environ, None)

    def test__release_iterator(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)

        # the releasing of a connection with no iterator at all is a no
        # operation, so that no error is raised for it
        server._release_iterator(connection)
        self.assertEqual(hasattr(connection, "iterator"), False)

        connection.parse(REQUEST)
        iterator = connection.iterator
        server._release_iterator(connection)

        # the releasing of the iterator closes the generator of the
        # application and unsets it from the connection
        self.assertEqual(connection.iterator, None)
        self.assertRaises(StopIteration, next, iterator)

    def test__release_queue(self):
        server = self._make_server()
        connection = self._make_connection(server, deliver=False)

        # the releasing of a queue that does not exist and of an empty one
        # are both a no operation for the connection
        server._release_queue(connection)
        connection.queue = []
        server._release_queue(connection)

        connection.parse(REQUEST)
        connection.parse(REQUEST)
        self.assertEqual(len(connection.queue), 1)

        server._release_queue(connection)

        # the releasing of the queue empties it while keeping the original
        # list instance, so that the connection may still use it
        self.assertEqual(connection.queue, [])

    def _make_server(self, app=None, **kwargs):
        app = self._app_hello if app == None else app
        server = netius.servers.WSGIServer(app=app, **kwargs)
        self.servers.append(server)
        return server

    def _make_connection(
        self, server, encoding=netius.common.PLAIN_ENCODING, ssl=False, deliver=True
    ):
        # builds a connection without the underlying socket, creating by
        # hand the parser that the opening of it would otherwise create
        connection = netius.servers.http.HTTPConnection(
            owner=server,
            socket=None,
            address=("127.0.0.1", 5000),
            ssl=ssl,
            encoding=encoding,
        )
        connection.parser = netius.common.HTTPParser(
            connection, type=netius.common.REQUEST, store=True
        )
        connection.parser.bind("on_data", connection.on_data)

        # replaces both the sending and the closing operations by ones
        # that record their usage, as there's no socket to be used
        connection.data = []
        connection.callbacks = []
        connection.closed = False
        connection.send = lambda data, **kwargs: self._send(
            connection, data, deliver, **kwargs
        )
        connection.close = lambda **kwargs: self._close_c(connection)

        self.connections.append(connection)
        return connection

    def _send(self, connection, data, deliver, delay=True, callback=None, **kwargs):
        # accumulates the data that would otherwise be sent through the
        # socket, running the callback as if it had been delivered, unless
        # the connection is meant to hold the delivery of it
        connection.data.append(netius.legacy.bytes(data))
        if callback:
            if deliver:
                callback(connection)
            else:
                connection.callbacks.append(callback)
        return len(data) if data else 0

    def _deliver(self, connection):
        # runs the callbacks that were being held by the connection, as if
        # the data associated with them had just reached the client
        callbacks = list(connection.callbacks)
        del connection.callbacks[:]
        for callback in callbacks:
            callback(connection)

    def _close_c(self, connection):
        connection.closed = True

    def _data(self, connection):
        return b"".join(connection.data)

    def _app_length(self, environ, start_response):
        contents = "Hello World"
        headers = (
            ("Content-Length", len(contents)),
            ("Content-Type", "text/plain"),
        )
        start_response("200 OK", headers)
        return LengthIterator([contents])

    def _app_return(self, environ, start_response):
        contents = "Hello World"
        headers = (
            ("Content-Length", len(contents)),
            ("Content-Type", "text/plain"),
        )
        start_response("200 OK", headers)
        return ReturnIterator(contents)

    def _app_hello(self, environ, start_response):
        contents = "Hello World"
        headers = (
            ("Content-Length", len(contents)),
            ("Content-Type", "text/plain"),
        )
        start_response("200 OK", headers)
        yield contents
