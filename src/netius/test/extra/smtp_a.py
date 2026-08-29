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
import netius.extra

DECODED = b"Ol\xc3\xa1 Mundo".decode("utf-8")
""" The text that the encoded words of the tests carry, built from
the byte sequence of it so that the value is a unicode one under
both of the interpreters that are supported """


class ActivityRelaySMTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.ActivityRelaySMTPServer()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        # the tracking is an optional feature, so a server that is built
        # with no endpoint at all carries none of the values for it
        self.assertEqual(self.server.activity_url, None)
        self.assertEqual(self.server.activity_secret, None)

    def test_on_serve_env(self):
        self.server.env = True

        with netius.conf_override("SMTP_ACTIVITY_URL", "https://activity.example.com"):
            with netius.conf_override("SMTP_ACTIVITY_SECRET", "secret"):
                self.server.on_serve()

        # the endpoint of the tracking is named by the environment, which is
        # what enables the feature for a deployment
        self.assertEqual(self.server.activity_url, "https://activity.example.com")
        self.assertEqual(self.server.activity_secret, "secret")

    def test__decode_header(self):
        # a header that carries no encoded word at all is served as it is,
        # so that the common case is left untouched
        self.assertEqual(self.server._decode_header("Hello World"), "Hello World")

    def test__decode_header_encoded(self):
        # an encoded word is decoded into the text that it names, both for
        # the base 64 and for the quoted printable of the specification
        self.assertEqual(
            self.server._decode_header("=?utf-8?B?T2zDoSBNdW5kbw==?="), DECODED
        )
        self.assertEqual(
            self.server._decode_header("=?utf-8?Q?Ol=C3=A1_Mundo?="), DECODED
        )

    def test__decode_header_invalid(self):
        # a value that cannot be decoded falls back to the original one, so
        # that a malformed header never breaks the handling of a message
        self.assertEqual(
            self.server._decode_header("=?utf-8?B?not base 64?="),
            "=?utf-8?B?not base 64?=",
        )
