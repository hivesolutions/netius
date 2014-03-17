#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import struct

import netius

class TorrentConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.task = None

    def handle(self, data):
        pass

    def handshake(self):
        data = struct.pack(
            "!B19sQ20s20s",
            19,
            "BitTorrent protocol",
            0,
            self.task.info["info_hash"],
            self.task.owner.peer_id
        )
        data and self.send(data)

class TorrentClient(netius.StreamClient):
    """
    Implementation of the torrent protocol, able to download
    and seed files across a peer to peer mesh network.

    The client provides a series of top level methods that
    provide the main interface with the system.

    The current implementation support both a torrent file
    (using trackers) strategy and also a DHT (distributed
    has table) strategy for completely decentralized usage.
    """

    def __init__(self, auto_close = False, *args, **kwargs):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.auto_close = auto_close

    def peer(self, task, host, port, ssl = False, connection = None):
        connection = connection or self.acquire_c(host, port, ssl = ssl)
        connection.task = task
        return connection

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)
        self.trigger("connect", self, connection)

    def on_acquire(self, connection):
        netius.StreamClient.on_acquire(self, connection)
        self.trigger("acquire", self, connection)
        connection.handshake()

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        print data
        #connection.parse(data)

    def on_connection_d(self, connection):
        netius.StreamClient.on_connection_d(self, connection)
        if not self.auto_close: return
        if self.connections: return
        self.close()

    def new_connection(self, socket, address, ssl = False):
        return TorrentConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )
