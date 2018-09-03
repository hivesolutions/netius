#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import time

import netius

from .base import Middleware

class FloodMiddleware(Middleware):
    """
    Simple middleware implementation for avoiding flooding
    of connection from a certain address.
    """

    def __init__(self, owner, conns_per_min = 600, whitelist = None):
        Middleware.__init__(self, owner)
        self.blacklist = conns_per_min
        self.whitelist = whitelist or []

    def start(self):
        Middleware.start(self)
        self.conns_per_min = netius.conf("CONNS_PER_MIN", self.conns_per_min, cast = int)
        self.whitelist = netius.conf("WHITELIST", self.whitelist, cast = list)
        self.blacklist = []
        self.conn_map = dict()
        self.minute = int(time.time() // 60)
        self.owner.bind("connection_c", self.on_connection_c)

    def stop(self):
        Middleware.stop(self)
        self.owner.unbind("connection_c", self.on_connection_c)

    def on_connection_c(self, owner, connection):
        host = connection.address[0]
        self._update_flood(host)
        if not host in self.blacklist and not "*" in self.blacklist: return
        if host in self.whitelist: return
        self.owner.warning("Connection from '%s' dropped (flooding avoidance)" % host)
        connection.close()

    def _update_flood(self, host):
        minute = int(time.time() // 60)
        if minute == self.minute: self.conn_map.clear()
        self.minute = minute
        count = self.conn_map.get(host, 0)
        count += 1
        self.conn_map[host] = count
        if count > self.conns_per_min: self.blacklist.append(host)
