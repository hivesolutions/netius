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
import netius.middleware


class FloodMiddlewareTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.Server(poll=netius.Poll)
        self.server.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_init(self):
        instance = netius.middleware.FloodMiddleware(self.server)

        # the limit is kept under a name of its own, as the blacklist is
        # only built once the middleware is started
        self.assertEqual(instance.conns_per_min, 600)
        self.assertEqual(instance.whitelist, [])

        instance = netius.middleware.FloodMiddleware(
            self.server, conns_per_min=10, whitelist=["10.0.0.1"]
        )

        self.assertEqual(instance.conns_per_min, 10)
        self.assertEqual(instance.whitelist, ["10.0.0.1"])

    def test_start(self):
        instance = self._register(conns_per_min=2)

        # the starting builds the structures that the counting needs and
        # keeps the limit that the constructor was given
        self.assertEqual(instance.conns_per_min, 2)
        self.assertEqual(instance.blacklist, [])
        self.assertEqual(instance.conn_map, {})

        # the handler is bound to the owner, so that every connection
        # that is created reaches the counting
        self.assertEqual(
            instance.on_connection_c in self.server.events["connection_c"], True
        )

    def test_start_conf(self):
        with netius.conf_override("CONNS_PER_MIN", "5"):
            instance = self._register(conns_per_min=2)

        # the configuration answers for the limit, taking precedence over
        # the value that the constructor was given
        self.assertEqual(instance.conns_per_min, 5)

    def test_stop(self):
        instance = self._register(conns_per_min=2)

        instance.stop()

        # the stopping releases the handler, so that no connection is
        # counted once the middleware is gone
        self.assertEqual(
            instance.on_connection_c in self.server.events["connection_c"], False
        )

    def test_on_connection_c(self):
        instance = self._register(conns_per_min=2)

        connection = self._make_connection("10.0.0.1")

        # the opening of a connection is what drives the counting, as the
        # handler is bound to the event of the owner
        self.assertEqual(instance.conn_map["10.0.0.1"], 1)

        # one that is within the limit is left alone, as there is nothing
        # to be defended against yet
        self.assertEqual(connection.is_closed(), False)

        self._make_connection("10.0.0.1")
        connection = self._make_connection("10.0.0.1")

        # the limit is passed by the third one, which is dropped together
        # with the ones that follow it
        self.assertEqual("10.0.0.1" in instance.blacklist, True)
        self.assertEqual(connection.is_closed(), True)

    def test_on_connection_c_whitelist(self):
        instance = self._register(conns_per_min=1, whitelist=["10.0.0.1"])

        for _index in range(3):
            connection = self._make_connection("10.0.0.1")

        # a host of the whitelist is never dropped, however many of the
        # connections it makes and whatever the blacklist says
        self.assertEqual("10.0.0.1" in instance.blacklist, True)
        self.assertEqual(connection.is_closed(), False)

    def test_on_connection_c_all(self):
        instance = self._register(conns_per_min=2)
        instance.blacklist.append("*")

        connection = self._make_connection("10.0.0.2")

        # the wildcard stands for every host, so one that was never seen
        # before is dropped as well
        self.assertEqual(connection.is_closed(), True)

    def test__update_flood(self):
        instance = self._register(conns_per_min=2)

        instance._update_flood("10.0.0.1")
        instance._update_flood("10.0.0.1")

        # the connections of the same minute add up, which is what allows
        # the limit to be reached at all
        self.assertEqual(instance.conn_map["10.0.0.1"], 2)
        self.assertEqual(instance.blacklist, [])

        instance._update_flood("10.0.0.1")

        self.assertEqual("10.0.0.1" in instance.blacklist, True)

        # the counting is the one of a minute, so the one that follows it
        # starts from nothing instead of carrying the previous count
        instance.minute -= 1
        instance._update_flood("10.0.0.2")

        self.assertEqual(instance.conn_map, dict({"10.0.0.2": 1}))

    def _register(self, **kwargs):
        return self.server.register_middleware(
            netius.middleware.FloodMiddleware, **kwargs
        )

    def _make_connection(self, host):
        connection = netius.Connection(owner=self.server, address=(host, 8080))
        connection.open()
        return connection
