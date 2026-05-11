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


class WSGIFutureTest(unittest.TestCase):

    def test_future_cleanup_clears_callbacks(self):
        future = netius.Future()
        future.add_done_callback(lambda f: None)
        future.add_partial_callback(lambda f, v: None)
        future.add_ready_callback(lambda: None)
        future.add_closed_callback(lambda: None)

        self.assertEqual(len(future.done_callbacks), 1)
        self.assertEqual(len(future.partial_callbacks), 1)
        self.assertEqual(len(future.ready_callbacks), 1)
        self.assertEqual(len(future.closed_callbacks), 1)

        future.cleanup()

        self.assertEqual(len(future.done_callbacks), 0)
        self.assertEqual(len(future.partial_callbacks), 0)
        self.assertEqual(len(future.ready_callbacks), 0)
        self.assertEqual(len(future.closed_callbacks), 0)

    def test_future_cleanup_breaks_reference_cycle(self):
        future = netius.Future()

        class FakeConnection(object):
            def __init__(self):
                self.future = None

        connection = FakeConnection()
        connection.future = future

        # register callbacks that capture connection, simulating
        # the closure cycle in the WSGI server's _send_part
        future.add_done_callback(lambda f: setattr(connection, "future", None))
        future.add_partial_callback(lambda f, v: None)

        # after cleanup the callbacks should be cleared, breaking
        # the reference from future back to connection
        future.cleanup()

        self.assertEqual(len(future.done_callbacks), 0)
        self.assertEqual(len(future.partial_callbacks), 0)
