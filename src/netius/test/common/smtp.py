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

import netius.common


class SMTPParserTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.lines = []
        self.parser = netius.common.SMTPParser(self)
        self.parser.bind("on_line", self._on_line)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.parser.destroy()

    def test_parse(self):
        count = self.parser.parse(b"250 ready\r\n")

        # the complete line is consumed and reported with the code and the
        # message split apart, a space naming the end of a response
        self.assertEqual(count, 11)
        self.assertEqual(self.lines, [("250", "ready", True)])

    def test_parse_multiple(self):
        self.parser.parse(b"250 first\r\n354 second\r\n")

        # a payload that carries more than one line reports each of them,
        # in the order in which they arrive
        self.assertEqual(self.lines, [("250", "first", True), ("354", "second", True)])

    def test_parse_partial(self):
        count = self.parser.parse(b"250 re")

        # a line that has not been terminated yet is buffered instead of
        # being reported, and none of its bytes are counted as parsed
        self.assertEqual(count, 0)
        self.assertEqual(self.lines, [])

        self.parser.parse(b"ady\r\n")

        # the remainder of the line completes it, the two reads being
        # joined into the single line that they form
        self.assertEqual(self.lines, [("250", "ready", True)])

    def test_parse_line_continuation(self):
        self.parser.parse(b"250-first\r\n250 last\r\n")

        # a dash in the place of the space marks a line that is continued,
        # so only the one that carries the space ends the response
        self.assertEqual(self.lines, [("250", "first", False), ("250", "last", True)])

    def test_parse_line_bare(self):
        self.parser.parse(b"250\r\n")

        # a line that carries no message at all is a final one, as it holds
        # no dash that would continue the response
        self.assertEqual(self.lines, [("250", "", True)])

    def _on_line(self, code, message, is_final=True):
        self.lines.append((code, message, is_final))
