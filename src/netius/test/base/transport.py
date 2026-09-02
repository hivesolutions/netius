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

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class TransportTest(unittest.TestCase):

    def test_write_closing(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        self.assertEqual(transport._loop, None)
        self.assertEqual(transport._connection, connection)
        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(connection.is_closed(), False)

        connection.status = netius.CLOSED

        self.assertEqual(transport._loop, None)
        self.assertEqual(transport._connection, connection)
        self.assertEqual(transport.is_closing(), True)
        self.assertEqual(connection.is_closed(), True)

        transport.write(b"")

    def test_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        with mock.patch.object(connection, "close") as close:
            transport.close()

        # the closing of a transport is the closing of the connection that it
        # wraps, with the buffer of it flushed on the way out
        self.assertEqual(close.call_args[1]["flush"], True)
        self.assertEqual(transport._connection, None)
        self.assertEqual(transport._exhausted, False)

    def test_close_closing(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = netius.Connection()
        transport = netius.Transport(None, connection)
        transport._connection = None

        # a transport that is already closing has nothing left to be closed,
        # and asking for it again must not raise
        with mock.patch.object(connection, "close") as close:
            self.assertEqual(transport.close(), None)

        self.assertEqual(close.called, False)

    def test_get_extra_info(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        # the values of the description are resolved when they are asked for,
        # so that the cost of them is only paid by whoever reads them
        transport._extra_dict = dict(socket=lambda: "value")

        self.assertEqual(transport.get_extra_info("socket"), "value")

        # a name that the description does not carry gives back what the
        # caller named as the default one
        self.assertEqual(transport.get_extra_info("missing"), None)
        self.assertEqual(transport.get_extra_info("missing", default=1), 1)

    def test_set_write_buffer_limits(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        transport.set_write_buffer_limits()

        # with neither of the bounds named the defaults are used, the lower
        # one being a quarter of the upper one
        self.assertEqual(connection.max_pending, 65536)
        self.assertEqual(connection.min_pending, 16384)

        transport.set_write_buffer_limits(low=1024)

        # naming only the lower one settles the upper one at four times it,
        # which is the ratio that the infra-structure uses
        self.assertEqual(connection.max_pending, 4096)
        self.assertEqual(connection.min_pending, 1024)

        transport.set_write_buffer_limits(high=2048)

        self.assertEqual(connection.max_pending, 2048)
        self.assertEqual(connection.min_pending, 512)

        # a pair that is not ordered would leave the connection unable to
        # ever recover from being exhausted, so it is refused
        self.assertRaises(
            netius.RuntimeError,
            transport.set_write_buffer_limits,
            high=1024,
            low=2048,
        )

    def test__handle_flow(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        connection = netius.Connection()
        protocol = mock.MagicMock()
        transport = netius.Transport(None, connection)
        transport._protocol = protocol

        with mock.patch.object(connection, "is_exhausted", return_value=False):
            transport._handle_flow()

        # a buffer that still has room asks nothing of the protocol, as there
        # is no back-pressure to be relayed to it
        self.assertEqual(transport._exhausted, False)
        self.assertEqual(protocol.pause_writing.called, False)

        with mock.patch.object(connection, "is_exhausted", return_value=True):
            transport._handle_flow()

        # once it fills up the protocol is told to stop writing, which is what
        # the flow control of the specification asks for
        self.assertEqual(transport._exhausted, True)
        self.assertEqual(protocol.pause_writing.called, True)

        with mock.patch.object(connection, "is_restored", return_value=False):
            transport._handle_flow()

        # it stays that way until the buffer has drained, so that the writing
        # is not resumed for every byte that leaves it
        self.assertEqual(transport._exhausted, True)
        self.assertEqual(protocol.resume_writing.called, False)

        with mock.patch.object(connection, "is_restored", return_value=True):
            transport._handle_flow()

        self.assertEqual(transport._exhausted, False)
        self.assertEqual(protocol.resume_writing.called, True)

    def test__handle_flow_untied(self):
        transport = netius.Transport(None, None, open=False)

        # a transport that no longer wraps a connection has no flow to be
        # handled, and asking for it must not raise
        self.assertEqual(transport._handle_flow(), None)

    def test_is_closing_no_connection(self):
        transport = netius.Transport(None, None, open=False)

        self.assertEqual(transport._connection, None)
        self.assertEqual(transport.is_closing(), True)

    def test_is_closing_open_connection(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(connection.is_closed(), False)

    def test_is_closing_closed_connection(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        connection.status = netius.CLOSED

        self.assertEqual(transport.is_closing(), True)
        self.assertEqual(connection.is_closed(), True)

    def test_is_closing_protocol_closing(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        protocol = netius.Protocol()
        protocol._open = True
        transport._protocol = protocol

        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(protocol.is_closing(), False)

        protocol._closing = True

        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(protocol.is_closing(), True)

    def test_is_closing_protocol_not_closing(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        protocol = netius.Protocol()
        protocol._open = True
        transport._protocol = protocol

        self.assertEqual(transport.is_closing(), False)
        self.assertEqual(protocol.is_open(), True)
        self.assertEqual(protocol.is_closing(), False)

    def test_is_closing_no_protocol(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        self.assertEqual(transport._protocol, None)
        self.assertEqual(transport.is_closing(), False)

    def test_is_closing_protocol_no_is_closing(self):
        connection = netius.Connection()
        transport = netius.Transport(None, connection)

        transport._protocol = object()

        self.assertEqual(transport.is_closing(), False)
