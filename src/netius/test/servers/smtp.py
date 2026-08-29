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

from netius.servers import smtp


class SMTPConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.SMTPServer(level=logging.CRITICAL)
        self.connection = smtp.SMTPConnection.__new__(smtp.SMTPConnection)
        self.connection.owner = self.server
        self.connection.state = smtp.HELO_STATE
        self.connection.tail = b"\r\n"
        self.sent = []
        self.connection.send_smtp = lambda code, message="", **kwargs: self.sent.append(
            (code, message)
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_unstuff(self):
        # the body starts at the beginning of a line, so the extra dot of a
        # line that opens with one is removed, the same being true for the
        # lines that follow a newline
        self.assertEqual(self.connection.unstuff(b"..a\r\n..b\r\n"), b".a\r\n.b\r\n")

    def test_unstuff_inner(self):
        # a pair of dots that is not at the start of a line was never stuffed
        # by the client, so it has to be left untouched
        self.assertEqual(self.connection.unstuff(b"a..b\r\n"), b"a..b\r\n")

    def test_unstuff_boundary(self):
        # the stuffed dots open the chunk that follows the one ending with
        # the newline, so it's the context of the previous read that allows
        # them to be detected
        self.assertEqual(self.connection.unstuff(b"ab\r\n"), b"ab\r\n")
        self.assertEqual(self.connection.unstuff(b"..x\r\n"), b".x\r\n")

    def test_unstuff_boundary_split(self):
        # the stuffed sequence is itself split between the two chunks, the
        # first of the dots ending one and the second opening the next
        self.assertEqual(self.connection.unstuff(b"ab\r\n."), b"ab\r\n.")
        self.assertEqual(self.connection.unstuff(b".x\r\n"), b"x\r\n")

    def test_unstuff_boundary_newline(self):
        # the newline that precedes the stuffed dots is split between the
        # chunks, a case that a shorter context would not be able to detect
        self.assertEqual(self.connection.unstuff(b"abc\r"), b"abc\r")
        self.assertEqual(self.connection.unstuff(b"\n..x\r\n"), b"\n.x\r\n")

    def test_on_line(self):
        self.connection.on_line("HELO", "client.localhost")

        self.assertEqual(self.sent[-1][0], 250)

    def test_on_line_unknown(self):
        # a code that the server does not handle must be rejected as a
        # protocol error instead of reaching any other method
        self.assertRaises(netius.ParserError, self.connection.on_line, "NOPE", "")

    def test_on_line_state(self):
        # the handlers of the internal states are not commands, so a client
        # must never be able to reach them by naming them as a verb, which
        # would otherwise walk the authentication forward without an auth
        for code in ("USERNAME", "PASSWORD", "RAW_DATA", "LINE"):
            self.assertRaises(netius.ParserError, self.connection.on_line, code, "")

        self.assertEqual(hasattr(self.connection, "_username"), False)
        self.assertEqual(self.connection.state, smtp.HELO_STATE)


class SMTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.SMTPServer(level=logging.CRITICAL)
        self.server.adapter = netius.adapters.MemoryAdapter()
        self.server.locals = ("example.com",)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_on_data_smtp(self):
        connection = smtp.SMTPConnection.__new__(smtp.SMTPConnection)
        connection.owner = self.server
        connection.keys = [self.server.adapter.reserve(owner="joe")]
        connection.tail = b"\r\n"

        # the body arrives from the connection as a byte sequence and so
        # the reserved value must be able to take it
        self.server.on_data_smtp(connection, b"Hello World\r\n")

        self.assertEqual(
            self.server.adapter.get(connection.keys[0]), b"Hello World\r\n"
        )

    def test_on_data_smtp_stuffed(self):
        connection = smtp.SMTPConnection.__new__(smtp.SMTPConnection)
        connection.owner = self.server
        connection.keys = [self.server.adapter.reserve(owner="joe")]
        connection.tail = b"\r\n"

        # the client stuffs the line of the body that starts with a dot, so
        # the message is stored with that extra dot removed, otherwise the
        # stuffing that the POP server applies to it would double it
        self.server.on_data_smtp(connection, b"normal line\r\n..hidden\r\n")

        self.assertEqual(
            self.server.adapter.get(connection.keys[0]),
            b"normal line\r\n.hidden\r\n",
        )

    def test__emails(self):
        result = self.server._emails(["TO:<joe@example.com>"])

        self.assertEqual(result, ["joe@example.com"])

    def test__emails_bare(self):
        # the path of an address is only optionally surrounded by angle
        # brackets, so an address without them must be kept untouched
        result = self.server._emails(["TO:postmaster"])

        self.assertEqual(result, ["postmaster"])

    def test__emails_prefix(self):
        result = self.server._emails(["FROM:<joe@example.com>"], prefix="from")

        self.assertEqual(result, ["joe@example.com"])

    def test__users(self):
        result = self.server._users(["joe@example.com"])

        self.assertEqual(result, ["joe"])

    def test__is_local(self):
        self.assertEqual(self.server._is_local("joe@example.com"), True)
        self.assertEqual(self.server._is_local("joe@other.com"), False)

    def test__is_local_bare(self):
        # an address that carries no domain may not be matched against the
        # local ones, so it's taken as a remote one instead of raising
        self.assertEqual(self.server._is_local("postmaster"), False)
