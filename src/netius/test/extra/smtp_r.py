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

import netius.adapters
import netius.extra
import netius.servers

PRIVATE_KEY = b"MIICVwIAAoGAgRWSX07LB0VzpDy14taaO1b+juQVhQpyKy/fxaLupohy4UDOxHJU\
Iz7jzR6B8l93KXWqxG5UZK2CduL6TKJGQZ+jGkTk0YU3d3r5kwPNOX1o+qhICJF8\
tcWZcw1MUV816sxJ3hi6RTz7faRvJtj9J2SM2cY3eq0xQSM/dvD1fqUCAwEAAQKB\
gDaUp3qTN3fQnxAf94x9z2Mt6p8CxDKn8xRdvtGzjhNueJzUKVmZOghZLDtsHegd\
A6bNMTKzsA2N7C9W1B0ZNHkmc6cbUyM/gXPLzpErFF4c5sTYAaJGKK+3/3BrrliG\
6vgzTXt3KZRlInfrumZRo4h7yE/IokfmzBwjbyP7N3lhAkDpfTwLidRBTgYVz5yO\
/7j55vl2GN80xDk0IDfO17/O8qyQlt+J6pksE0ojTkAjD2N4rx3dL4kPgmx80r/D\
AdNNAkCNh4LBukRUMT+ulfngrnzQ4QDnCUXpANKpe3HZk4Yfysj1+zrlWFilzO3y\
t/RpGu4GtH1LUNQNjrp94CcBNPy5AkBW6KCTAuiYrjwhnjd+Gr11d33fcX6Tm35X\
Yq6jNTdWBooo/5+RLFt7RmrQHW5OHoo9/6C0Fd+EgF11UNTD90f5AkBBB6/0FgNJ\
cCujq7PaIjKlw40nm2ItEry5NUh1wcxSFVpLdDl2oiZxYH1BFndOSBpwqEQd9DDL\
Xfag2fryGge5AkCFPjggILI8jZZoEW9gJoyqh13fkf+WjtwL1mLztK2gQcrvlyUd\
/ddIy8ZEkmGRiHMcX0SGdsEprW/EpbhSdakC"

MESSAGE = b"Header: Value\r\n\r\nHello World"

RESULT = b"DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/simple; d=netius.hive.pt;\r\n\
 i=email@netius.hive.pt; l=13; q=dns/txt; s=20160523113052;\r\n\
 t=1464003802; h=Header; bh=sIAi0xXPHrEtJmW97Q5q9AZTwKC+l1Iy+0m8vQIc/DY=;\r\n\
 b=MzkFXsO3vyJg23JWaBdGOB8RFzF8eElLDrQKpq/wOK4rXCxueox5qqXWHXdPRS4CtFg5zCKl\r\n\
 cJ2h1k5Rsgb1O5ijO4jT+LTomare/IrlGBhDpxsbEnf7+flfRC3sRCqP6cqwWRTMonzFaMZr\r\n\
 YcHONgR8zeDAT/pu7Vx3ZkHB0tI=\r\nHeader: Value\r\n\r\nHello World"

REGISTRY = {
    "netius.hive.pt": dict(
        key_b64=PRIVATE_KEY, selector="20160523113052", domain="netius.hive.pt"
    )
}


class RelaySMTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.RelaySMTPServer()
        self.server.adapter = netius.adapters.MemoryAdapter()
        self.server.locals = ("local.com",)
        self.relayed = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_on_header_smtp(self):
        connection = self._make_connection()

        self.server.on_header_smtp(
            connection, ["FROM:<joe@local.com>"], ["TO:<mary@remote.com>"]
        )

        # the recipients that are not served locally are the ones that have
        # to be relayed, and the buffer that gathers the message starts empty
        self.assertEqual(connection.remotes, ["mary@remote.com"])
        self.assertEqual(connection.relay, [])

    def test_on_header_smtp_local(self):
        connection = self._make_connection()

        self.server.on_header_smtp(
            connection, ["FROM:<joe@local.com>"], ["TO:<mary@local.com>"]
        )

        # a recipient that is served locally is delivered rather than
        # relayed, so nothing is gathered for a relay operation
        self.assertEqual(connection.remotes, [])

    def test_on_data_smtp(self):
        connection = self._make_connection(remotes=["mary@remote.com"])

        self.server.on_data_smtp(connection, b"payload")

        # the payload is gathered for the relay, as it has to be sent onward
        # to the server that serves the recipient
        self.assertEqual(connection.relay, [b"payload"])

    def test_on_data_smtp_no_remotes(self):
        connection = self._make_connection()

        self.server.on_data_smtp(connection, b"payload")

        # with no recipient to relay to there is nothing to gather, the
        # message being delivered locally alone
        self.assertEqual(connection.relay, [])

    def test_on_message_smtp(self):
        connection = self._make_connection(remotes=["mary@remote.com"])
        connection.from_l = ["FROM:<joe@local.com>"]
        connection.relay = [b"Header: Value\r\n\r\nHello World\r\n.\r\n"]
        self._patch_relay()

        self.server.on_message_smtp(connection)

        # the termination sequence is stripped from the contents that are
        # relayed, as it belongs to the framing and not to the message
        self.assertEqual(len(self.relayed), 1)
        _connection, froms, tos, contents = self.relayed[0]
        self.assertEqual(froms, ["joe@local.com"])
        self.assertEqual(tos, ["mary@remote.com"])
        self.assertEqual(contents, b"Header: Value\r\n\r\nHello World")

    def test_on_message_smtp_no_remotes(self):
        connection = self._make_connection()
        self._patch_relay()

        self.server.on_message_smtp(connection)

        # a message with no recipient to relay to never reaches the relay,
        # so that no session is opened towards another server
        self.assertEqual(self.relayed, [])

    def test_relay_unauthenticated(self):
        connection = self._make_connection(remotes=["mary@remote.com"])

        # the relaying of a message towards another server requires an
        # authenticated user, so an anonymous session is refused instead of
        # being forwarded, which would make an open relay of the server
        self.assertRaises(
            netius.SecurityError,
            self.server.relay,
            connection,
            ["joe@local.com"],
            ["mary@remote.com"],
            b"",
        )

    def test_relay_not_allowed(self):
        connection = self._make_connection(remotes=["mary@remote.com"])
        connection.username = "joe"
        connection.auth_meta = dict(allowed_froms=["other@local.com"])

        # a user that is bound to a set of senders may not relay from one
        # that is outside of it, which would otherwise let it send as
        # somebody that it is not
        self.assertRaises(
            netius.SecurityError,
            self.server.relay,
            connection,
            ["joe@local.com"],
            ["mary@remote.com"],
            b"",
        )

    def test_date(self):
        result = self.server.date()

        # the date follows the format that the specification names for a
        # message, ending in the numeric offset of the zone
        self.assertEqual(result.endswith(" +0000"), True)
        self.assertEqual(len(result.split(" ")), 6)

    def test_message_id(self):
        result = self.server.message_id(email="joe@remote.com")

        # the identifier is enclosed in angle brackets and is bound to the
        # domain of the address that it is built for
        self.assertEqual(result.startswith("<"), True)
        self.assertEqual(result.endswith("@remote.com>"), True)

    def test_message_id_connection(self):
        connection = self._make_connection()
        connection.identifier = "abc"

        # a connection that carries an identifier of its own names the
        # message, so that the two may be correlated afterwards
        self.assertEqual(
            self.server.message_id(connection=connection, email="joe@remote.com"),
            "<abc@remote.com>",
        )

    def test_dkim(self):
        self.server.dkim = REGISTRY
        result = self.server.dkim_contents(
            MESSAGE, email="email@netius.hive.pt", creation=1464003802
        )

        self.assertEqual(result, RESULT)

    def test_dkim_absent(self):
        self.server.dkim = REGISTRY

        # a domain that carries no register is left unsigned, the contents
        # being served exactly as they were provided
        result = self.server.dkim_contents(MESSAGE, email="joe@other.com")
        self.assertEqual(result, MESSAGE)

    def test_dkim_no_key(self):
        self.server.dkim = dict(other=dict(selector="selector", domain="other.com"))

        # a register that names no key at all cannot sign anything, which is
        # reported instead of a message that travels unsigned
        self.assertRaises(
            netius.SecurityError,
            self.server.dkim_contents,
            MESSAGE,
            email="joe@other",
        )

    def _make_connection(self, remotes=None):
        # builds a connection stand-in that carries the state that the relay
        # looks at, without any of the socket that it would otherwise hold
        connection = netius.servers.smtp.SMTPConnection.__new__(
            netius.servers.smtp.SMTPConnection
        )
        connection.owner = self.server
        connection.keys = []
        connection.from_l = []
        connection.to_l = []
        connection.tail = b"\r\n"
        connection.identifier = None
        connection.remotes = [] if remotes == None else remotes
        connection.relay = []
        return connection

    def _patch_relay(self):
        # replaces the relaying by one that records the messages that reach
        # it, so that no session is opened towards another server
        self.server.relay = (
            lambda connection, froms, tos, contents: self.relayed.append(
                (connection, froms, tos, contents)
            )
        )
