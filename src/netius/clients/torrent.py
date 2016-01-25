#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import time
import struct

import netius.common

HANDSHAKE_STATE = 1

NORMAL_STATE = 2

CHOKED = 1

UNCHOKED = 2

ALIVE_TIMEOUT = 45.0
""" The timeout that is going to be used in the operation of
keep alive the connection that are active, any connections that
does not send a message with an interval less than this timeout
is going to be disconnected """

SPEED_LIMIT = 10240
""" The minimum download speed limit from which a connection will
be disconnected if does not fulfill such limit, this is going to
optimize the connection in competition for blocks """

BLOCK_SIZE = 16384
""" The typical size of block that is going to be retrieved
using the current torrent infra-structure, this value conditions
most of the torrent operations and should be defined carefully """

class TorrentConnection(netius.Connection):

    def __init__(self, max_requests = 50, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.max_requests = max_requests
        self.pend_requests = 0
        self.task = None
        self.peer_id = None
        self.bitfield = b""
        self.state = HANDSHAKE_STATE
        self.choked = CHOKED
        self.start = time.time()
        self.messages = 0
        self.downloaded = 0
        self.requests = []

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.TorrentParser(self)
        self.bind("close", self.on_close)
        self.parser.bind("on_handshake", self.on_handshake)
        self.parser.bind("on_message", self.on_message)
        self.is_alive(timeout = ALIVE_TIMEOUT, schedule = True)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()

    def on_close(self, connection):
        self.release()

    def on_handshake(self, protocol, reserved, info_hash, peer_id):
        self.peer_id = peer_id
        self.state = NORMAL_STATE
        self.interested()
        self.unchoke()

    def on_message(self, length, type, data):
        self.handle(type, data)
        self.messages += 1

    def parse(self, data):
        self.parser.parse(data)

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
        if self.choked == CHOKED: return
        self.choked = CHOKED
        self.release()
        self.trigger("choked", self)

    def unchoke_t(self, data):
        if self.choked == UNCHOKED: return
        self.choked = UNCHOKED
        self.reset()
        self.next()
        self.trigger("unchoked", self)

    def piece_t(self, data):
        block = struct.unpack("!LL", data[:8])
        index, begin = block
        data = data[8:]
        self.task.set_data(data, index, begin)
        self.downloaded += len(data)
        self.remove_request(block)
        self.next()
        self.trigger("piece", self, data, index, begin)

    def port_t(self, data):
        port, = struct.unpack("!H", data[:8])
        self.task.set_dht(self.address, port)

    def next(self, count = None):
        if not self.choked == UNCHOKED: return
        if count == None: count = self.max_requests - self.pend_requests
        for _index in range(count):
            block = self.task.pop_block(self.bitfield)
            if not block: return
            index, begin, length = block
            self.request(index, begin = begin, length = length)
            block_t = (index, begin)
            self.add_request(block_t)

    def add_request(self, block):
        self.requests.append(block)
        self.pend_requests += 1

    def remove_request(self, block):
        if not block in self.requests: return
        self.requests.remove(block)
        self.pend_requests -= 1

    def reset(self):
        del self.requests[:]
        self.pend_requests = 0

    def release(self):
        for index, begin in self.requests:
            self.task.push_block(index, begin)
        self.reset()

    def handshake(self):
        data = struct.pack(
            "!B19sQ20s20s",
            19,
            b"BitTorrent protocol",
            1,
            self.task.info_hash,
            netius.legacy.bytes(self.task.owner.peer_id)
        )
        data and self.send(data)

    def keep_alive(self):
        data = struct.pack("!L", 0)
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

    def is_alive(self, timeout = ALIVE_TIMEOUT, schedule = False):
        messages = self.messages
        downloaded = self.downloaded

        def clojure():
            if not self.is_open(): return
            delta = self.downloaded - downloaded
            rate = float(delta) / float(timeout)
            if self.messages == messages: self.close(flush = True); return
            if rate < SPEED_LIMIT: self.close(flush = True); return
            callable = self.is_alive()
            self.owner.delay(callable, timeout)

        if schedule: self.owner.delay(clojure, timeout)
        return clojure

class TorrentClient(netius.StreamClient):
    """
    Implementation of the torrent protocol, able to download
    and seed files across a peer to peer mesh network.

    The client provides a series of top level methods that
    provide the main interface with the system.

    The current implementation support both a torrent file
    (using trackers) strategy and also a DHT (distributed
    has table) strategy for completely decentralized usage.

    @see: http://www.bittorrent.org/beps/bep_0003.html
    """

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

    def new_connection(self, socket, address, ssl = False):
        return TorrentConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )
