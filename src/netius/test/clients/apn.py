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
import struct
import unittest

import netius.clients

try:
    import unittest.mock as mock
except ImportError:
    mock = None

TOKEN = "00" * 32
""" The token of a device, which travels as a sequence of
hexadecimal digits and is thirty two bytes wide """


class APNProtocolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.protocol = _MockAPNProtocol()

    def test_init(self):
        # a protocol starts with no notification of its own and with the
        # sandbox as the environment that it targets
        self.assertEqual(self.protocol.host, None)
        self.assertEqual(self.protocol.port, None)
        self.assertEqual(self.protocol.token, None)
        self.assertEqual(self.protocol.message, None)
        self.assertEqual(self.protocol.badge, 0)
        self.assertEqual(self.protocol.sandbox, True)

    def test_send_notification(self):
        self.protocol.send_notification(TOKEN, "Hello World")

        data = self.protocol.sent[0][0]
        command, token_length = struct.unpack("!BH", data[:3])

        # the message starts with the simplified command and the length
        # of the token, which is the one of a device
        self.assertEqual(command, 0)
        self.assertEqual(token_length, 32)
        self.assertEqual(data[3:35], b"\x00" * 32)

        (payload_length,) = struct.unpack("!H", data[35:37])
        payload = json.loads(data[37:].decode("utf-8"))

        # the payload is the JSON of the alert, together with the sound
        # and the badge that come with it
        self.assertEqual(payload_length, len(data) - 37)
        self.assertEqual(payload["aps"]["alert"], "Hello World")
        self.assertEqual(payload["aps"]["sound"], "default")
        self.assertEqual(payload["aps"]["badge"], 0)

    def test_send_notification_values(self):
        self.protocol.send_notification(TOKEN, "Hello World", sound="chime", badge=3)

        data = self.protocol.sent[0][0]
        payload = json.loads(data[37:].decode("utf-8"))

        self.assertEqual(payload["aps"]["sound"], "chime")
        self.assertEqual(payload["aps"]["badge"], 3)

    def test_send_notification_close(self):
        self.protocol.send_notification(TOKEN, "Hello World")

        # without the closing being asked for the sending carries no
        # callback, so the connection is left as it is
        self.assertEqual(self.protocol.sent[0][1], None)

        self.protocol.send_notification(TOKEN, "Hello World", close=True)

        # with it the callback that comes with the sending is the one
        # that closes the connection once the message is out
        callback = self.protocol.sent[1][1]

        self.assertNotEqual(callback, None)

        callback(None)

        self.assertEqual(self.protocol.closed, 1)

    def test_set(self):
        self.protocol.set(
            TOKEN,
            "Hello World",
            sound="chime",
            badge=3,
            sandbox=False,
            key_file="key.pem",
            cer_file="cer.pem",
            _close=False,
        )

        # the values of the notification are kept for the moment that the
        # connection is made, which is when the message is sent
        self.assertEqual(self.protocol.token, TOKEN)
        self.assertEqual(self.protocol.message, "Hello World")
        self.assertEqual(self.protocol.sound, "chime")
        self.assertEqual(self.protocol.badge, 3)
        self.assertEqual(self.protocol.sandbox, False)
        self.assertEqual(self.protocol.key_file, "key.pem")
        self.assertEqual(self.protocol.cer_file, "cer.pem")
        self.assertEqual(self.protocol._close, False)

    def test_connection_made(self):
        self.protocol.set(TOKEN, "Hello World", _close=False)

        self.protocol.connection_made(None)

        # the making of the connection is what sends the notification,
        # built from the values that were set before it
        data = self.protocol.sent[0][0]
        payload = json.loads(data[37:].decode("utf-8"))

        self.assertEqual(payload["aps"]["alert"], "Hello World")

    def test_notify(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("netius.connect_stream") as connect_stream:
            loop, protocol = self.protocol.notify(TOKEN, message="Hello World")

        # the sandbox is the environment that a notification targets
        # unless the caller asks for the production one
        self.assertEqual(self.protocol.host, netius.clients.APNProtocol.SANDBOX_HOST)
        self.assertEqual(self.protocol.port, netius.clients.APNProtocol.SANDBOX_PORT)
        self.assertEqual(self.protocol.message, "Hello World")
        self.assertEqual(protocol, self.protocol)
        self.assertEqual(loop, connect_stream.return_value)

        # the connection towards the gateway is a secure one, as the
        # service is never spoken to in the clear
        self.assertEqual(connect_stream.call_args[1]["ssl"], True)
        self.assertEqual(
            connect_stream.call_args[1]["host"],
            netius.clients.APNProtocol.SANDBOX_HOST,
        )

    def test_notify_production(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("netius.connect_stream"):
            self.protocol.notify(TOKEN, sandbox=False, key_file="key.pem")

        # with the sandbox turned off the gateway of production is the
        # one that the notification is sent to
        self.assertEqual(self.protocol.host, netius.clients.APNProtocol.HOST)
        self.assertEqual(self.protocol.port, netius.clients.APNProtocol.PORT)
        self.assertEqual(self.protocol.key_file, "key.pem")


class APNClientTest(unittest.TestCase):

    def test_protocol(self):
        # the client answers with the protocol of the notifications,
        # which is the one that speaks to the gateway
        self.assertEqual(netius.clients.APNClient.protocol, netius.clients.APNProtocol)

    def test_notify_s(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch("netius.connect_stream"):
            _loop, protocol = netius.clients.APNClient.notify_s(
                TOKEN, message="Hello World"
            )

        # the client builds a protocol of its own for the notification,
        # which carries the values that it was given
        self.assertEqual(isinstance(protocol, netius.clients.APNProtocol), True)
        self.assertEqual(protocol.message, "Hello World")


class _MockAPNProtocol(netius.clients.APNProtocol):
    """
    Stand in for the protocol that keeps the messages that
    it sends instead of handing them to a transport.
    """

    def __init__(self, *args, **kwargs):
        netius.clients.APNProtocol.__init__(self, *args, **kwargs)
        self.sent = []
        self.closed = 0

    def connection_made(self, transport):
        netius.clients.APNProtocol.connection_made(self, transport)

    def send(self, data, callback=None):
        self.sent.append((data, callback))

    def close(self, *args, **kwargs):
        self.closed += 1
