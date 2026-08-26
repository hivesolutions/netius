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

import os
import shutil
import tempfile
import unittest

import netius.clients
import netius.sh.smtp

try:
    import unittest.mock as mock
except ImportError:
    mock = None

MESSAGE = b"Subject: Hello\r\n\r\nHello World"

SENDER = "sender@netius.hive.pt"

RECEIVER = "receiver@netius.hive.pt"


class SHSMTPTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.message_path = os.path.join(self.base_path, "message.eml")
        file = open(self.message_path, "wb")
        try:
            file.write(MESSAGE)
        finally:
            file.close()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base_path)

    def test_send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(netius.clients, "SMTPClient") as smtp_client:
            netius.sh.smtp.send(self.message_path, SENDER, RECEIVER)

        args, kwargs = smtp_client.return_value.message.call_args

        # the client closes itself as soon as the message has been handed
        # off, so that the shell tool is able to terminate on its own
        self.assertEqual(smtp_client.call_args[1], dict(auto_close=True))

        # both the sender and the receiver are sent as sequences, as the
        # client is able to deliver a message to more than one address
        self.assertEqual(args[0], [SENDER])
        self.assertEqual(args[1], [RECEIVER])
        self.assertEqual(args[2], MESSAGE)
        self.assertEqual(kwargs["host"], None)
        self.assertEqual(kwargs["port"], 25)
        self.assertEqual(kwargs["username"], None)
        self.assertEqual(kwargs["password"], None)
        self.assertEqual(kwargs["stls"], True)

    def test_send_arguments(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(netius.clients, "SMTPClient") as smtp_client:
            netius.sh.smtp.send(
                self.message_path,
                SENDER,
                RECEIVER,
                host="netius.hive.pt",
                port=587,
                username="username",
                password="password",
                stls=False,
            )

        kwargs = smtp_client.return_value.message.call_args[1]

        self.assertEqual(kwargs["host"], "netius.hive.pt")
        self.assertEqual(kwargs["port"], 587)
        self.assertEqual(kwargs["username"], "username")
        self.assertEqual(kwargs["password"], "password")
        self.assertEqual(kwargs["stls"], False)
