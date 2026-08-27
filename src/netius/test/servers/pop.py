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

        self.assertEqual(message.startswith("3 messages"), True)
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0].startswith("0 "), True)

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
        self.sent = []
        connection.send_pop = lambda message="", lines=(), **kwargs: self.sent.append(
            (message, list(lines))
        )
        return connection

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
