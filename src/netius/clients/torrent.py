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

import math
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

EXTENDED_RESERVED = 0x100000
""" The reserved bits value that signals support for the extension
protocol (BEP 10) and that is set on the handshake message so that
the metadata exchange (BEP 9) may be negotiated with the peer """

METADATA_BLOCK_SIZE = 16384
""" The size of each of the metadata blocks that are exchanged
under the metadata extension protocol (BEP 9), this is the value
defined by the specification for the metadata piece division """

EXTENDED_TYPES = {0: "handshake", 1: "ut_metadata"}
""" The map associating the extended message type identifiers
with their internal string representations, the handshake one
is reserved by the specification and the remaining are local """

METADATA_REQUEST = 0

METADATA_DATA = 1

METADATA_REJECT = 2


class TorrentConnection(netius.Connection):

    def __init__(self, max_requests=50, *args, **kwargs):
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
        self.extensions = {}
        self.metadata_size = 0
        self.metadata = []

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open():
            return
        self.parser = netius.common.TorrentParser(self)
        self.bind("close", self.on_close)
        self.parser.bind("on_handshake", self.on_handshake)
        self.parser.bind("on_message", self.on_message)
        self.is_alive(timeout=ALIVE_TIMEOUT, schedule=True)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed():
            return
        if self.parser:
            self.parser.destroy()

    def on_close(self, connection):
        self.release()

    def on_handshake(self, protocol, reserved, info_hash, peer_id):
        self.peer_id = peer_id
        self.state = NORMAL_STATE
        self.interested()
        self.unchoke()

        # in case the peer has signaled support for the extension protocol
        # (BEP 10) sends the extended handshake so that the metadata exchange
        # (BEP 9) may be negotiated, this is only required when the metadata
        # for the task is not yet available (eg: magnet/info hash based task)
        if reserved & EXTENDED_RESERVED and not self.task.has_metadata():
            self.extended_handshake()

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
        if not hasattr(self, method_name):
            return

        # tries to retrieve the method for the current state in iteration
        # and then calls the retrieve method with (handler method)
        method = getattr(self, method_name)
        method(data)

    def bitfield_t(self, data):
        bitfield = netius.common.string_to_bits(data)
        self.bitfield = [True if value == "1" else False for value in bitfield]

    def choke_t(self, data):
        if self.choked == CHOKED:
            return
        self.choked = CHOKED
        self.release()
        self.trigger("choked", self)

    def unchoke_t(self, data):
        if self.choked == UNCHOKED:
            return
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
        (port,) = struct.unpack("!H", data[:8])
        self.task.set_dht(self.address, port)

    def extended_t(self, data):
        # retrieves the extended message identifier (first byte) so that
        # the proper handler may be selected, the zero identifier is the
        # reserved one for the extended handshake message (BEP 10)
        (extended,) = struct.unpack("!B", data[:1])
        data = data[1:]

        # in case the message is the extended handshake delegates its
        # handling to the proper method, otherwise the message is assumed
        # to be a metadata one and is handled as such (BEP 9)
        if extended == 0:
            self.on_extended_handshake(data)
        else:
            self.on_metadata(data)

    def on_extended_handshake(self, data):
        # decodes the bencoded payload of the extended handshake and stores
        # both the map of supported extensions and the metadata size that
        # are going to be used in the metadata exchange operation
        message = netius.common.bdecode(data)
        self.extensions = message.get("m", {})
        self.metadata_size = message.get("metadata_size", 0)

        # in case the peer does not support the metadata extension or does
        # not announce a valid metadata size there's nothing to be done
        if not self.extensions.get("ut_metadata", None):
            return
        if not self.metadata_size:
            return

        # initializes the metadata buffer with the proper number of (empty)
        # pieces according to the announced metadata size and then requests
        # each of the metadata pieces from the peer (BEP 9)
        count = self._metadata_pieces()
        self.metadata = [None for _index in range(count)]
        for index in range(count):
            self.request_metadata(index)

    def on_metadata(self, data):
        # splits the bencoded header from the trailing binary payload of the
        # metadata message, the header is decoded to retrieve both the type
        # and the index of the metadata piece being transferred
        index = data.index(b"ee") + 2
        message = netius.common.bdecode(data[:index])
        msg_type = message.get("msg_type", METADATA_REJECT)
        piece = message.get("piece", 0)

        # in case the message is not a metadata data one there's nothing to
        # be stored (eg: a reject message) and so the control flow returns
        if not msg_type == METADATA_DATA:
            return

        # in case the piece index is not a valid one for the current metadata
        # buffer returns immediately to avoid any erroneous storage
        if piece < 0 or piece >= len(self.metadata):
            return

        # stores the binary payload (metadata block) in the proper position
        # of the metadata buffer and verifies if the complete set of pieces
        # has already been received, only then the metadata is processed
        self.metadata[piece] = data[index:]
        if None in self.metadata:
            return
        self.set_metadata()

    def set_metadata(self):
        # joins the complete set of metadata pieces into a single buffer and
        # delegates the handling of it to the task, that is going to verify
        # the metadata against the info hash and load the proper structures
        metadata = b"".join(self.metadata)
        self.task.set_metadata(metadata)

    def next(self, count=None):
        if not self.choked == UNCHOKED:
            return
        if not self.task.has_metadata():
            return
        if count == None:
            count = self.max_requests - self.pend_requests
        for _index in range(count):
            block = self.task.pop_block(self.bitfield)
            if not block:
                return
            index, begin, length = block
            self.request(index, begin=begin, length=length)
            block_t = (index, begin)
            self.add_request(block_t)

    def add_request(self, block):
        self.requests.append(block)
        self.pend_requests += 1

    def remove_request(self, block):
        if not block in self.requests:
            return
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
            EXTENDED_RESERVED,
            self.task.info_hash,
            netius.legacy.bytes(self.task.owner.peer_id),
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

    def request(self, index, begin=0, length=BLOCK_SIZE):
        data = struct.pack("!LBLLL", 13, 6, index, begin, length)
        data and self.send(data)

    def extended_handshake(self):
        # builds the bencoded payload of the extended handshake announcing
        # the local support for the metadata extension (BEP 9) using the
        # reserved extended message identifier zero (BEP 10)
        message = dict(m=dict(ut_metadata=1))
        payload = netius.common.bencode(message)
        self.extended(0, payload)

    def request_metadata(self, piece):
        # retrieves the extended message identifier that the peer has
        # assigned to the metadata extension and in case it's not defined
        # returns immediately as the request cannot be performed
        extended = self.extensions.get("ut_metadata", None)
        if not extended:
            return

        # builds the bencoded metadata request message for the provided
        # piece index and sends it using the peer assigned identifier
        message = dict(msg_type=METADATA_REQUEST, piece=piece)
        payload = netius.common.bencode(message)
        self.extended(extended, payload)

    def extended(self, extended, payload):
        payload = netius.legacy.bytes(payload)
        data = struct.pack("!LBB", len(payload) + 2, 20, extended) + payload
        data and self.send(data)

    def is_alive(self, timeout=ALIVE_TIMEOUT, schedule=False):
        messages = self.messages
        downloaded = self.downloaded

        def clojure():
            if not self.is_open():
                return
            delta = self.downloaded - downloaded
            rate = float(delta) / float(timeout)
            if self.messages == messages:
                self.close(flush=True)
                return
            if rate < SPEED_LIMIT:
                self.close(flush=True)
                return
            callable = self.is_alive()
            self.owner.delay(callable, timeout)

        if schedule:
            self.owner.delay(clojure, timeout)
        return clojure

    def _metadata_pieces(self):
        count = math.ceil(float(self.metadata_size) / float(METADATA_BLOCK_SIZE))
        return int(count)


class TorrentClient(netius.StreamClient):
    """
    Implementation of the torrent protocol, able to download
    and seed files across a peer to peer mesh network.

    The client provides a series of top level methods that
    provide the main interface with the system.

    The current implementation support both a torrent file
    (using trackers) strategy and also a DHT (distributed
    has table) strategy for completely decentralized usage.

    :see: http://www.bittorrent.org/beps/bep_0003.html
    """

    def peer(self, task, host, port, ssl=False, connection=None):
        connection = connection or self.acquire_c(host, port, ssl=ssl)
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

    def build_connection(self, socket, address, ssl=False):
        return TorrentConnection(owner=self, socket=socket, address=address, ssl=ssl)


if __name__ == "__main__":
    import os
    import logging
    import binascii

    import netius.servers

    target_path = "~/Downloads"

    state = dict(next_print=0)

    def on_start(server):
        # retrieves the info hash from the configuration (as an hexadecimal
        # string) and decodes it into the raw bytes representation that is
        # going to be used as the reference for the DHT based download
        info_hash = netius.conf("TORRENT_INFO_HASH", None)
        info_hash = binascii.unhexlify(info_hash)

        # starts the downloading of the file associated with the info hash
        # using a DHT based strategy (no torrent file) and binds the events
        # that are going to provide some feedback about the download progress
        task = server.download(target_path, info_hash=info_hash, close=True)
        task.bind("metadata", on_metadata)
        task.bind("piece", on_piece)
        task.bind("complete", on_complete)

    def on_metadata(task):
        print("Metadata received, starting download")

    def on_piece(task, index):
        # throttles the printing of the status so that it's only done at
        # most once every print interval, avoiding excessive output
        if time.time() < state["next_print"]:
            return
        state["next_print"] = time.time() + 3.0

        percent = task.percent()
        speed_s = task.speed_s()
        left = task.left()
        percent = int(percent)
        print(task.info_string())
        print("[%d%%] - %d bytes (%s/s)" % (percent, left, speed_s))

    def on_complete(task):
        path = os.path.expanduser(target_path)
        path = os.path.normpath(path)
        print("Download completed to '%s'" % path)

    server = netius.servers.TorrentServer(level=logging.DEBUG)
    server.bind("start", on_start)
    server.serve(env=True)
else:
    __path__ = []
