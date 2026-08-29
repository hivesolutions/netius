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

import logging
import unittest

import netius
import netius.adapters
import netius.servers

from netius.servers import pop


class POPConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.POPServer(level=logging.CRITICAL)
        self.server.adapter = netius.adapters.MemoryAdapter()
        self.connection = self._make_connection()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        connection = pop.POPConnection(
            owner=self.server, socket=None, address=("127.0.0.1", 110)
        )

        # a connection starts with no message being served and with the tail
        # set to a newline, so that the first line of the body of a message
        # that is retrieved is taken as being at the start of a line
        self.assertEqual(connection.state, pop.INITIAL_STATE)
        self.assertEqual(connection.file, None)
        self.assertEqual(connection.tail, b"\r\n")

    def test_stat(self):
        self._populate()

        self.connection.stat()

        self.assertEqual(self.sent[-1][0], "3 60")

    def test_list(self):
        self._populate()

        self.connection.list()

        message, lines = self.sent[-1]

        # the order of a mailbox is the one of the adapter, so what is
        # asserted is the pairing of each index with its own size
        self.assertEqual(message, "3 messages (60 octets)")
        self.assertEqual(sorted(self.connection.sizes), [10, 20, 30])
        self.assertEqual(
            lines,
            [
                "%d %d" % (index, size)
                for index, size in enumerate(self.connection.sizes)
            ],
        )

    def test_list_no_stat(self):
        self._populate()

        # the listing is built from the sizes gathered by the command
        # itself, so a client that never issued a status still sees the
        # complete contents of the mailbox
        self.connection.list()

        message, lines = self.sent[-1]

        self.assertEqual(self.connection.count, 0)
        self.assertEqual(message, "3 messages (60 octets)")
        self.assertEqual(len(lines), 3)

    def test_uidl(self):
        self._populate()

        self.connection.uidl()

        message, lines = self.sent[-1]

        # only the number of messages is announced, as the command gathers
        # the identifiers and never the sizes that a total would need
        self.assertEqual(message, "3 messages")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].startswith("0 "), True)

    def test_uidl_no_stat(self):
        self._populate()

        # a listing that was never preceded by a status must neither be
        # empty nor announce a total that has not been measured
        self.connection.uidl()

        message, lines = self.sent[-1]

        self.assertEqual(self.connection.byte_c, 0)
        self.assertEqual(message, "3 messages")
        self.assertEqual(len(lines), 3)

    def test_retr(self):
        self._store(b"hello")
        self.connection.uidl()

        self.connection.retr(0)

        # a body that does not end with a newline gains one before the
        # terminator, so that the dot is alone in its own line
        self.assertEqual(self._data(), b"hello\r\n.\r\n")

    def test_retr_line(self):
        self._store(b"hello\r\n")
        self.connection.uidl()

        self.connection.retr(0)

        # a body that already ends with a newline must not gain an empty
        # line before the terminator of the message
        self.assertEqual(self._data(), b"hello\r\n.\r\n")

    def test_retr_stuffed(self):
        self._store(b"normal line\r\n.hidden\r\n")
        self.connection.uidl()

        self.connection.retr(0)

        # a line of the body that starts with a dot is stuffed with a second
        # one, otherwise the client would take it for the end of the message
        self.assertEqual(self._data(), b"normal line\r\n..hidden\r\n.\r\n")

    def test_retr_stuffed_first(self):
        self._store(b".hidden\r\n")
        self.connection.uidl()

        self.connection.retr(0)

        # the first line of the body is at the start of a line as well, so a
        # dot that opens it has to be stuffed the very same way
        self.assertEqual(self._data(), b"..hidden\r\n.\r\n")

    def test_retr_empty(self):
        self._store(b"")
        self.connection.uidl()

        self.connection.retr(0)

        # an empty body is served as the terminator alone, with no empty
        # line preceding it
        self.assertEqual(self._data(), b".\r\n")

    def test_retr_chunked(self):
        self._store(b"abc\r\n.x\r\n")
        self.connection.uidl()

        chunk_size = pop.CHUNK_SIZE
        pop.CHUNK_SIZE = 4
        try:
            self.connection.retr(0)
        finally:
            pop.CHUNK_SIZE = chunk_size

        # the newline that precedes the dot is split between two of the
        # reads, so the stuffing has to survive the boundary of the chunks
        self.assertEqual(self._data(), b"abc\r\n..x\r\n.\r\n")

    def test_stuff(self):
        # the body starts at the beginning of a line, so a dot that opens it
        # is stuffed, the same being true for the ones that follow a newline
        self.assertEqual(self.connection.stuff(b".a\r\n.b\r\n"), b"..a\r\n..b\r\n")

    def test_stuff_inner(self):
        # a dot that is not at the start of a line is left untouched, as it
        # cannot be taken for the terminator of the message
        self.assertEqual(self.connection.stuff(b"a.b\r\n"), b"a.b\r\n")

    def test_stuff_boundary(self):
        # the dot opens the chunk that follows the one ending with the
        # newline, so it's the context of the previous read that detects it
        self.assertEqual(self.connection.stuff(b"ab\r\n"), b"ab\r\n")
        self.assertEqual(self.connection.stuff(b".x\r\n"), b"..x\r\n")

    def test_stuff_boundary_split(self):
        # the newline itself is split between the two chunks, a case that a
        # single byte of context would not be able to detect
        self.assertEqual(self.connection.stuff(b"abc\r"), b"abc\r")
        self.assertEqual(self.connection.stuff(b"\n.x\r\n"), b"\n..x\r\n")

    def test_dele(self):
        self._populate()
        self.connection.uidl()

        self.connection.dele(0)

        self.assertEqual(self.sent[-1][0], "removed")
        self.assertEqual(self.server.adapter.count(owner="joe"), 2)

    def test_bye(self):
        self.connection.bye()

        self.assertEqual(self.sent[-1][0], "bye")

    def test_ok(self):
        self.connection.ok()

        self.assertEqual(self.sent[-1][0], "accepted")

    def test_on_line(self):
        self._populate()

        self.connection.on_line("STAT", "")

        self.assertEqual(self.sent[-1][0], "3 60")

    def test_on_line_unknown(self):
        # a code that the server does not handle must be rejected as a
        # protocol error instead of reaching any other method
        self.assertRaises(netius.ParserError, self.connection.on_line, "NOPE", "")

    def test_on_line_method(self):
        # the resolution of the handler is restricted to the commands, so
        # that a code that happens to match another method of the
        # connection is never able to reach it
        for code in ("LINE", "USER", "READY", "CLOSE", "PARSE"):
            self.assertRaises(netius.ParserError, self.connection.on_line, code, "")

    def _make_connection(self):
        connection = pop.POPConnection.__new__(pop.POPConnection)
        connection.owner = self.server
        connection.username = "joe"
        connection.count = 0
        connection.byte_c = 0
        connection.sizes = ()
        connection.keys = ()
        connection.size = 0
        connection.file = None
        connection.tail = b"\r\n"
        self.sent = []
        self.data = []
        connection.send_pop = lambda message="", lines=(), **kwargs: self.sent.append(
            (message, list(lines))
        )
        connection.send = lambda value, callback=None, **kwargs: self._send(
            connection, value, callback
        )
        return connection

    def _send(self, connection, value, callback):
        # accumulates the payload that would otherwise reach the socket and
        # runs the callback as if it had been delivered, which is what
        # drives the reading of the chunk that follows
        self.data.append(netius.legacy.bytes(value))
        if callback:
            callback(connection)

    def _data(self):
        return b"".join(self.data)

    def _store(self, contents):
        self.server.adapter.set(contents, owner="joe")

    def _populate(self):
        for index in range(3):
            self.server.adapter.set(b"x" * (10 * (index + 1)), owner="joe")


class POPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.POPServer(level=logging.CRITICAL)
        self.server.adapter = netius.adapters.MemoryAdapter()
        self.connection = pop.POPConnection.__new__(pop.POPConnection)
        self.connection.owner = self.server
        self.connection.username = "joe"
        for index in range(3):
            self.server.adapter.set(b"x" * (10 * (index + 1)), owner="joe")

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        server = netius.servers.POPServer(level=logging.CRITICAL)
        try:
            # the greeting hostname is part of the state of the server and
            # not of the serving, so that it's already available once the
            # on serve callback is reached from within the base
            self.assertEqual(server.host_g, "pop.localhost")
        finally:
            server.cleanup()

        server = netius.servers.POPServer(
            host="mail.example.com", level=logging.CRITICAL
        )
        try:
            # the hostname that a caller names replaces the default one
            self.assertEqual(server.host_g, "mail.example.com")
        finally:
            server.cleanup()

    def test_serve_env(self):
        original = netius.StreamServer.__dict__["serve"]

        def serve(self, *args, **kwargs):
            self.host = "127.0.0.1"
            self.env = True
            self.on_serve()

        netius.StreamServer.serve = serve
        try:
            with netius.conf_override("POP_HOST", "mail.example.com"):
                self.server.serve()
        finally:
            netius.StreamServer.serve = original

        # the base is replaced by one that reproduces its ordering, setting
        # the bind address and only then reaching the on serve callback, so
        # that the value the environment names survives the serving instead
        # of being replaced by the default once the loop returns
        self.assertEqual(self.server.host, "mail.example.com")

    def test_on_serve(self):
        self.server.host = "127.0.0.1"

        self.server.on_serve()

        # the greeting hostname replaces the bind address that the base has
        # set, so that it's the one announced to a client that connects
        self.assertEqual(self.server.host, "pop.localhost")

    def test_on_serve_env(self):
        self.server.host = "127.0.0.1"
        self.server.env = True

        with netius.conf_override("POP_HOST", "mail.example.com"):
            self.server.on_serve()

        # the environment is able to override the greeting hostname, which
        # was not possible while the value it resolved to was discarded
        self.assertEqual(self.server.host, "mail.example.com")

    def test_on_stat_pop(self):
        self.server.on_stat_pop(self.connection)

        self.assertEqual(self.connection.count, 3)
        self.assertEqual(self.connection.byte_c, 60)

    def test_on_list_pop(self):
        self.server.on_list_pop(self.connection)

        self.assertEqual(sorted(self.connection.sizes), [10, 20, 30])

    def test_on_uidl_pop(self):
        self.server.on_uidl_pop(self.connection)

        # the keys are indexed by the retrieval and the removal, so the
        # listing has to be a materialized sequence
        self.assertEqual(len(self.connection.keys), 3)
        self.assertEqual(self.connection.keys[0], self.server.adapter.list("joe")[0])

    def test_on_retr_pop(self):
        self.server.on_uidl_pop(self.connection)

        self.server.on_retr_pop(self.connection, 0)
        try:
            contents = self.connection.file.read()

            # the size that is announced to the client has to match the
            # payload that is served for the very same message
            self.assertEqual(self.connection.size, len(contents))
            self.assertEqual(contents, b"x" * self.connection.size)
        finally:
            self.connection.file.close()

    def test_on_dele_pop(self):
        self.server.on_uidl_pop(self.connection)

        self.server.on_dele_pop(self.connection, 0)

        self.assertEqual(self.server.adapter.count(owner="joe"), 2)
