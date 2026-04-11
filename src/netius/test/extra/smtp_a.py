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

import json
import unittest

import netius.extra

try:
    import unittest.mock as mock
except ImportError:
    mock = None

MESSAGE = b"Subject: Test Subject\r\nMessage-ID: <test123@localhost>\r\n\r\nHello World"

MESSAGE_NO_SUBJECT = b"Message-ID: <test123@localhost>\r\n\r\nHello World"

MESSAGE_NO_ID = b"Subject: Test Subject\r\n\r\nHello World"


class ActivityRelaySMTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.ActivityRelaySMTPServer(
            activity_url="http://localhost:8080/api/activity",
            activity_secret="test-secret",
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        self.assertEqual(self.server.activity_url, "http://localhost:8080/api/activity")
        self.assertEqual(self.server.activity_secret, "test-secret")

    def test_init_defaults(self):
        server = netius.extra.ActivityRelaySMTPServer()
        self.assertEqual(server.activity_url, None)
        self.assertEqual(server.activity_secret, None)
        server.cleanup()

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_on_relay_smtp(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        smtp_client = mock.MagicMock()
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]

        with mock.patch.object(self.server, "_post_activity") as post_mock:
            self.server.on_relay_smtp(smtp_client, connection, froms, tos, MESSAGE)

        post_mock.assert_called_once_with(connection, froms, tos, MESSAGE, "delivered")
        smtp_client.close.assert_called_once()

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_on_relay_error_smtp(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        smtp_client = mock.MagicMock()
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]
        reply_to = "sender@localhost"
        context = dict(tos=tos, contents=MESSAGE)
        exception = Exception("Connection refused")

        with mock.patch.object(self.server, "_post_activity") as post_mock:
            with mock.patch.object(self.server, "relay_postmaster"):
                self.server.on_relay_error_smtp(
                    smtp_client,
                    connection,
                    froms,
                    tos,
                    MESSAGE,
                    reply_to,
                    context,
                    exception,
                )

        post_mock.assert_called_once_with(
            connection, froms, tos, MESSAGE, "failed", error="Connection refused"
        )
        smtp_client.close.assert_called_once()

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_disabled(self):
        server = netius.extra.ActivityRelaySMTPServer(activity_url=None)
        connection = mock.MagicMock()
        connection.username = "user@localhost"

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            server._post_activity(
                connection,
                ["sender@localhost"],
                ["recipient@localhost"],
                MESSAGE,
                "delivered",
            )

        method_mock.assert_not_called()
        server.cleanup()

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_delivered(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(connection, froms, tos, MESSAGE, "delivered")

        method_mock.assert_called_once()
        call_args = method_mock.call_args
        self.assertEqual(call_args[0][0], "POST")
        self.assertEqual(call_args[0][1], "http://localhost:8080/api/activity")

        data = json.loads(call_args[1]["data"])
        self.assertEqual(data["sender"], "sender@localhost")
        self.assertEqual(data["recipients"], ["recipient@localhost"])
        self.assertEqual(data["subject"], "Test Subject")
        self.assertEqual(data["message_id"], "<test123@localhost>")
        self.assertEqual(data["status"], "delivered")
        self.assertEqual(data["username"], "user@localhost")
        self.assertNotIn("error", data)

        headers = call_args[1]["headers"]
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["X-Activity-Secret"], "test-secret")

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_failed(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(
                connection, froms, tos, MESSAGE, "failed", error="Connection refused"
            )

        method_mock.assert_called_once()
        data = json.loads(method_mock.call_args[1]["data"])
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error"], "Connection refused")

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_headers(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(connection, froms, tos, MESSAGE, "delivered")

        data = json.loads(method_mock.call_args[1]["data"])
        self.assertIn("headers", data)
        self.assertEqual(data["headers"]["Subject"], "Test Subject")
        self.assertEqual(data["headers"]["Message-ID"], "<test123@localhost>")

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_contents(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"
        froms = ["sender@localhost"]
        tos = ["recipient@localhost"]

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(connection, froms, tos, MESSAGE, "delivered")

        data = json.loads(method_mock.call_args[1]["data"])
        self.assertIn("contents", data)
        self.assertIn("Hello World", data["contents"])
        self.assertIn("Subject: Test Subject", data["contents"])

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_no_subject(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(
                connection,
                ["sender@localhost"],
                ["recipient@localhost"],
                MESSAGE_NO_SUBJECT,
                "delivered",
            )

        data = json.loads(method_mock.call_args[1]["data"])
        self.assertEqual(data["subject"], "")

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_no_message_id(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            self.server._post_activity(
                connection,
                ["sender@localhost"],
                ["recipient@localhost"],
                MESSAGE_NO_ID,
                "delivered",
            )

        data = json.loads(method_mock.call_args[1]["data"])
        self.assertEqual(data["message_id"], "")

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_no_secret(self):
        server = netius.extra.ActivityRelaySMTPServer(
            activity_url="http://localhost:8080/api/activity"
        )
        connection = mock.MagicMock()
        connection.username = "user@localhost"

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            server._post_activity(
                connection,
                ["sender@localhost"],
                ["recipient@localhost"],
                MESSAGE,
                "delivered",
            )

        headers = method_mock.call_args[1]["headers"]
        self.assertNotIn("X-Activity-Secret", headers)
        server.cleanup()

    @unittest.skipIf(mock == None, "Skipping mock test")
    def test_post_activity_http_failure(self):
        connection = mock.MagicMock()
        connection.username = "user@localhost"

        with mock.patch("netius.clients.HTTPClient.method_s") as method_mock:
            method_mock.side_effect = Exception("Connection refused")
            self.server._post_activity(
                connection,
                ["sender@localhost"],
                ["recipient@localhost"],
                MESSAGE,
                "delivered",
            )

        method_mock.assert_called_once()
