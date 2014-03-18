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

import netius.common

HANDSHAKE_STATE = 1

NORMAL_STATE = 2

CHOCKED = 1

UNCHOCKED = 2

BLOCK_SIZE = 16384
""" The typical size of block that is going to be retrieved
using the current torrent infra-structure, this value conditions
most of the torrent operations and should be defined carefully """

class TorrentConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = netius.common.TorrentParser(self)
        self.task = None
        self.peer_id = None
        self.bitfield = b""
        self.state = HANDSHAKE_STATE
        self.chocked = CHOCKED

        self.parser.bind("on_handshake", self.on_handshake)
        self.parser.bind("on_message", self.on_message)

    def parse(self, data):
        self.parser.parse(data)

    def on_handshake(self, protocol, reserved, info_hash, peer_id):
        self.peer_id = peer_id
        self.state = NORMAL_STATE
        self.interested()
        self.unchoke()

    def on_message(self, length, type, data):
        self.owner.debug(type)
        self.handle(type, data)

    def handle(self, type, data):
        # constructs the name of the method that is going to be called
        # for the handle of the message from the provided type and verifies
        # if the method exists under the current instance
        method_name = "%s_t" % type
        if not hasattr(self, method_name): return

        # tries to retrieve the method for the current state in iteration
        # and then calls the retrieve method with (handler method)
        method = getattr(self, method_name)
        method(data)

    def bitfield_t(self, data):
        bitfield = netius.common.string_to_bits(data)
        self.bitfield = [True if value == "1" else False for value in bitfield]

    def choke_t(self, data):
        self.chocked = CHOCKED

    def unchoke_t(self, data):
        self.chocked = UNCHOCKED
        self.next()

    def piece_t(self, data):
        index, begin = struct.unpack("!LL", data[:8])
        data = data[8:]
        self.task.set_data(data, index, begin)
        self.next()

    def next(self):
        if not self.chocked == UNCHOCKED: return
        block = self.task.pop_block(self.bitfield)
        if not block: return
        index, begin = block
        self.request(index, begin = begin)

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

    def choke(self):
        data = struct.pack("!LB", 1, 0)
        data and self.send(data)

    def unchoke(self):
        data = struct.pack("!LB", 1, 1)
        data and self.send(data)

    def interested(self):
        data = struct.pack("!LB", 1, 2)
        data and self.send(data)

    def not_interested(self):
        data = struct.pack("!LB", 1, 3)
        data and self.send(data)

    def have(self, index):
        data = struct.pack("!LBL", 5, 4, index)
        data and self.send(data)

    def request(self, index, begin = 0, length = BLOCK_SIZE):
        data = struct.pack("!LBLLL", 13, 6, index, begin, length)
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
        connection.parse(data)

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
