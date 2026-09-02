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
import netius.servers

from netius.servers import ftp


class FTPConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.FTPServer(level=logging.CRITICAL)
        self.connection = ftp.FTPConnection.__new__(ftp.FTPConnection)
        self.connection.owner = self.server
        self.connection.cwd = "/"
        self.connection.mode = "ascii"
        self.sent = []
        self.connection.send_ftp = lambda code, message="", **kwargs: self.sent.append(
            (code, message)
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_on_user(self):
        self.connection.on_user("joe")

        self.assertEqual(self.connection.username, "joe")
        self.assertEqual(self.sent[-1][0], 200)

    def test_on_pwd(self):
        self.connection.on_pwd("")

        self.assertEqual(self.sent[-1], (257, '"/"'))

    def test_on_type(self):
        # the argument of the command selects the transfer mode, so a
        # binary transfer really has to switch the connection over to it
        self.connection.on_type("I")

        self.assertEqual(self.connection.mode, "binary")
        self.assertEqual(self.sent[-1][0], 200)

    def test_on_type_modes(self):
        for argument, mode in (
            ("A", "ascii"),
            ("E", "ebcdic"),
            ("I", "binary"),
            ("L", "local"),
        ):
            self.connection.on_type(argument)

            self.assertEqual(self.connection.mode, mode)

    def test_on_type_unknown(self):
        # an argument that names no known mode falls back to the textual
        # one, which is the mode a session starts at
        self.connection.on_type("Z")

        self.assertEqual(self.connection.mode, "ascii")

    def test_on_noop(self):
        self.connection.on_noop("")

        self.assertEqual(self.sent[-1][0], 200)

    def test_on_line(self):
        self.connection.on_line("PWD", "")

        self.assertEqual(self.sent[-1], (257, '"/"'))

    def test_on_line_unknown(self):
        # a code that the server does not handle must be rejected as a
        # protocol error instead of reaching any other method
        self.assertRaises(netius.ParserError, self.connection.on_line, "NOPE", "")

    def test_on_line_method(self):
        # the resolution of the handler is restricted to the commands, so
        # that a code that happens to match another method of the
        # connection is never able to reach it
        for code in ("LINE", "FLUSH_LIST", "FLUSH_RETR"):
            self.assertRaises(netius.ParserError, self.connection.on_line, code, "")
