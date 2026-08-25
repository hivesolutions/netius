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

import netius

from netius.base import diag

try:
    import appier
except ImportError:
    appier = None


class DiagAppTest(unittest.TestCase):

    def test_list_connections_closed(self):
        if appier == None:
            self.skipTest("Skipping test: appier unavailable")

        app = diag.DiagApp(self._make_system())
        result = app.list_connections_closed()
        result = json.loads(netius.legacy.str(result))

        # the complete contents of the ring buffer must be reported, with
        # the most recently closed connection being the first one
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "second")
        self.assertEqual(result[1]["id"], "first")

        # the metadata that describes the closing must be preserved by the
        # serialization, as it's the reason for the endpoint to exist
        self.assertEqual(result[0]["close_reason"], netius.REASON_TIMEOUT)
        self.assertEqual(result[0]["close_paired"], "first")

    def _make_system(self):
        # builds a minimal system stand-in that reports a pair of closed
        # connections, mimicking the ring buffer of the diagnostics
        closed = [
            dict(id="second", close_reason=netius.REASON_TIMEOUT, close_paired="first"),
            dict(
                id="first",
                close_reason=netius.REASON_UPSTREAM_ERROR,
                close_paired="second",
            ),
        ]

        class System(object):

            def connections_closed_dict(self):
                return closed

        return System()
