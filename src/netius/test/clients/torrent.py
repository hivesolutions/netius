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

import struct
import hashlib
import unittest

import netius.common
import netius.clients


class TorrentConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.clients.TorrentClient(poll=netius.Poll, auto_close=False)
        self.client.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.cleanup()

    def test_init(self):
        connection = self._make_connection()

        # a connection starts in the handshake state and choked, with no
        # request of its own and nothing downloaded yet
        self.assertEqual(connection.state, netius.clients.torrent.HANDSHAKE_STATE)
        self.assertEqual(connection.choked, netius.clients.torrent.CHOKED)
        self.assertEqual(connection.max_requests, 50)
        self.assertEqual(connection.pend_requests, 0)
        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.messages, 0)
        self.assertEqual(connection.downloaded, 0)
        self.assertEqual(connection.metadata, [])

    def test_open(self):
        connection = self._make_connection()

        connection.open()

        # the opening builds the parser of the protocol, which is what
        # turns the bytes of the peer into the messages of it
        self.assertEqual(connection.is_open(), True)
        self.assertEqual(
            isinstance(connection.parser, netius.common.TorrentParser), True
        )

    def test_close(self):
        connection = self._make_connection()
        connection.open()
        connection.parser = _MockTorrentParser()

        connection.close()

        # the parser is released together with the connection, so that
        # nothing of it is left behind
        self.assertEqual(connection.is_closed(), True)
        self.assertEqual(connection.parser.destroyed, True)

    def test_on_close(self):
        connection = self._make_connection()
        connection.requests = [(0, 0), (1, 16384)]
        connection.pend_requests = 2

        connection.on_close(connection)

        # the closing gives the blocks that were asked for back to the
        # task, as this peer is no longer going to serve them
        self.assertEqual(connection.task.pushed, [(0, 0), (1, 16384)])
        self.assertEqual(connection.requests, [])

    def test_parse(self):
        connection = self._make_connection()
        connection.open()
        connection.parser = _MockTorrentParser()

        connection.parse(b"data")

        # the parsing is handed to the parser of the connection, which is
        # the one that knows the shape of the protocol
        self.assertEqual(connection.parser.parsed, [b"data"])

    def test_on_handshake(self):
        connection = _MockTorrentConnection()

        connection.on_handshake(b"BitTorrent protocol", 0, b"i" * 20, b"p" * 20)

        # the peer is remembered and the connection leaves the handshake,
        # announcing the interest and the unchoking of the peer
        self.assertEqual(connection.peer_id, b"p" * 20)
        self.assertEqual(connection.state, netius.clients.torrent.NORMAL_STATE)
        self.assertEqual(len(connection.sent), 2)

    def test_on_handshake_extended(self):
        connection = _MockTorrentConnection()

        connection.on_handshake(
            b"BitTorrent protocol",
            netius.clients.torrent.EXTENDED_RESERVED,
            b"i" * 20,
            b"p" * 20,
        )

        # a peer that announces the extension protocol is answered with the
        # extended handshake, as the metadata of the task is not there yet
        self.assertEqual(len(connection.sent), 3)

    def test_on_message(self):
        connection = _MockTorrentConnection()

        connection.on_message(2, "bitfield", b"\xff")

        # the message is routed to the handler of its type and counted, as
        # the count is what tells a connection that is alive apart
        self.assertEqual(connection.bitfield, [True] * 8)
        self.assertEqual(connection.messages, 1)

    def test_handle(self):
        connection = _MockTorrentConnection()

        connection.handle("bitfield", b"\x80")

        self.assertEqual(connection.bitfield[0], True)

        # a type that names no handler of the connection is dropped, so
        # that an unknown message never breaks the parsing
        connection.handle("unknown", b"data")

        self.assertEqual(connection.sent, [])

    def test_bitfield_t(self):
        connection = _MockTorrentConnection()

        connection.bitfield_t(b"\xa0")

        # every bit of the field stands for a piece that the peer holds,
        # the most significant one being the first of them
        self.assertEqual(
            connection.bitfield, [True, False, True, False, False, False, False, False]
        )

    def test_choke_t(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.UNCHOKED
        connection.requests = [(0, 0)]
        connection.pend_requests = 1

        connection.choke_t(b"")

        # the choking gives the blocks that were asked for back to the
        # task, as they are no longer going to be served
        self.assertEqual(connection.choked, netius.clients.torrent.CHOKED)
        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.task.pushed, [(0, 0)])
        self.assertEqual(connection.triggered[0][0], "choked")

    def test_choke_t_repeated(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.CHOKED

        connection.choke_t(b"")

        # a peer that is already choking is not choked again, so that no
        # event is triggered for a state that did not change
        self.assertEqual(connection.triggered, [])

    def test_unchoke_t(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.CHOKED

        connection.unchoke_t(b"")

        # the unchoking clears the requests that were pending and asks the
        # task for the blocks that are going to be requested next
        self.assertEqual(connection.choked, netius.clients.torrent.UNCHOKED)
        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.triggered[0][0], "unchoked")

    def test_unchoke_t_repeated(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.UNCHOKED

        connection.unchoke_t(b"")

        self.assertEqual(connection.triggered, [])

    def test_piece_t(self):
        connection = _MockTorrentConnection()
        connection.requests = [(1, 16384)]
        connection.pend_requests = 1

        data = struct.pack("!LL", 1, 16384) + b"payload"
        connection.piece_t(data)

        # the block reaches the task at the offset that the message names
        # and the request that it answers is no longer pending
        self.assertEqual(connection.task.data, [(b"payload", 1, 16384)])
        self.assertEqual(connection.downloaded, 7)
        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.pend_requests, 0)
        self.assertEqual(connection.triggered[0][0], "piece")

    def test_port_t(self):
        connection = _MockTorrentConnection()

        connection.port_t(struct.pack("!H", 6881))

        # the port of the DHT node of the peer is handed to the task, so
        # that the node may be reached later on
        self.assertEqual(connection.task.dht, (connection.address, 6881))

    def test_port_t_extra(self):
        connection = _MockTorrentConnection()

        # only the two bytes of the port are read, so a message that
        # carries more than that is still understood
        connection.port_t(struct.pack("!H", 6881) + b"extra")

        self.assertEqual(connection.task.dht, (connection.address, 6881))

    def test_extended_t(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict(ut_metadata=1)
        connection.metadata_size = 5
        connection.metadata = [None]

        # builds an extended handshake message (extended identifier zero)
        # and verifies that it is correctly dispatched and parsed
        message = netius.common.bencode(dict(m=dict(ut_metadata=1), metadata_size=5))
        data = struct.pack("!B", 0) + netius.legacy.bytes(message)
        connection.extended_t(data)

        self.assertEqual(connection.extensions, dict(ut_metadata=1))
        self.assertEqual(connection.metadata_size, 5)

    def test_extended_t_empty(self):
        connection = _MockTorrentConnection()

        # verifies that an empty extended message is ignored instead of
        # raising an error while trying to unpack the (missing) identifier
        connection.extended_t(b"")

        self.assertEqual(connection.sent, [])

    def test_on_extended_handshake(self):
        connection = _MockTorrentConnection()

        message = netius.common.bencode(
            dict(m=dict(ut_metadata=2), metadata_size=20000)
        )
        connection.on_extended_handshake(netius.legacy.bytes(message))

        self.assertEqual(connection.extensions, dict(ut_metadata=2))
        self.assertEqual(connection.metadata_size, 20000)

        # verifies that a metadata request was sent for each of the
        # (two) metadata pieces implied by the announced metadata size
        self.assertEqual(len(connection.metadata), 2)
        self.assertEqual(len(connection.sent), 2)

    def test_on_extended_handshake_unsupported(self):
        connection = _MockTorrentConnection()

        message = netius.common.bencode(dict(m=dict()))
        connection.on_extended_handshake(netius.legacy.bytes(message))

        # verifies that no metadata request is sent when the peer does
        # not announce support for the metadata extension
        self.assertEqual(connection.sent, [])

    def test_on_metadata(self):
        connection = _MockTorrentConnection()
        connection.metadata = [None]

        payload = b"hello world"
        header = netius.common.bencode(dict(msg_type=1, piece=0))
        data = netius.legacy.bytes(header) + payload
        connection.on_metadata(data)

        # verifies that the metadata buffer is complete and that the
        # assembled metadata was handed over to the associated task
        self.assertEqual(connection.task.metadata, payload)

    def test_on_metadata_reject(self):
        connection = _MockTorrentConnection()
        connection.metadata = [None]

        header = netius.common.bencode(dict(msg_type=2, piece=0))
        connection.on_metadata(netius.legacy.bytes(header))

        # verifies that a reject message does not store any data and
        # that the metadata is not (incorrectly) considered complete
        self.assertEqual(connection.metadata, [None])
        self.assertEqual(connection.task.metadata, None)

    def test_on_metadata_malformed(self):
        connection = _MockTorrentConnection()
        connection.metadata = [None]

        connection.on_metadata(b"malformed")

        # verifies that a malformed message is ignored instead of raising
        # and that the metadata is not (incorrectly) considered complete
        self.assertEqual(connection.metadata, [None])
        self.assertEqual(connection.task.metadata, None)

    def test_next(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.UNCHOKED
        connection.max_requests = 3
        connection.task.metadata = True
        connection.task.blocks = [(0, 0, 16384), (0, 16384, 16384)]

        connection.next()

        # a block is asked for the peer for as long as the task has them,
        # each of them being counted as a request that is pending
        self.assertEqual(len(connection.sent), 2)
        self.assertEqual(connection.requests, [(0, 0), (0, 16384)])
        self.assertEqual(connection.pend_requests, 2)

    def test_next_choked(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.CHOKED
        connection.task.metadata = True
        connection.task.blocks = [(0, 0, 16384)]

        connection.next()

        # a peer that is choking serves nothing, so no block is ever
        # asked for while that is the case
        self.assertEqual(connection.sent, [])

    def test_next_metadata(self):
        connection = _MockTorrentConnection()
        connection.choked = netius.clients.torrent.UNCHOKED
        connection.task.blocks = [(0, 0, 16384)]

        connection.next()

        # without the metadata of the task there is no piece to be asked
        # for, as the shape of the content is still unknown
        self.assertEqual(connection.sent, [])

    def test_add_request(self):
        connection = _MockTorrentConnection()

        connection.add_request((0, 0))

        self.assertEqual(connection.requests, [(0, 0)])
        self.assertEqual(connection.pend_requests, 1)

    def test_remove_request(self):
        connection = _MockTorrentConnection()
        connection.requests = [(0, 0)]
        connection.pend_requests = 1

        connection.remove_request((0, 0))

        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.pend_requests, 0)

        # a block that was never asked for is not removed, so that the
        # count of the pending ones is not thrown off by it
        connection.remove_request((1, 0))

        self.assertEqual(connection.pend_requests, 0)

    def test_reset(self):
        connection = _MockTorrentConnection()
        connection.requests = [(0, 0), (0, 16384)]
        connection.pend_requests = 2

        connection.reset()

        self.assertEqual(connection.requests, [])
        self.assertEqual(connection.pend_requests, 0)

    def test_release(self):
        connection = _MockTorrentConnection()
        connection.requests = [(0, 0), (1, 16384)]
        connection.pend_requests = 2

        connection.release()

        # the blocks that were asked for are given back to the task, so
        # that another peer may be asked for them instead
        self.assertEqual(connection.task.pushed, [(0, 0), (1, 16384)])
        self.assertEqual(connection.requests, [])

    def test_handshake(self):
        connection = _MockTorrentConnection()

        connection.handshake()

        data = connection.sent[0]

        # the handshake names the protocol, the reserved bits, the hash of
        # the task and the identifier of the local peer, in that order
        self.assertEqual(len(data), 68)
        self.assertEqual(data[0:1], struct.pack("!B", 19))
        self.assertEqual(data[1:20], b"BitTorrent protocol")
        self.assertEqual(
            data[20:28], struct.pack("!Q", netius.clients.torrent.EXTENDED_RESERVED)
        )
        self.assertEqual(data[28:48], b"i" * 20)
        self.assertEqual(data[48:68], b"netius-peer-id-00000")

    def test_keep_alive(self):
        connection = _MockTorrentConnection()

        connection.keep_alive()

        # the message that keeps a connection alive carries no payload at
        # all, only the length of zero that names it
        self.assertEqual(connection.sent, [struct.pack("!L", 0)])

    def test_choke(self):
        connection = _MockTorrentConnection()

        connection.choke()
        connection.unchoke()
        connection.interested()
        connection.not_interested()

        # the four messages of the state of a peer share a shape, only the
        # identifier of each of them telling them apart
        self.assertEqual(
            connection.sent,
            [
                struct.pack("!LB", 1, 0),
                struct.pack("!LB", 1, 1),
                struct.pack("!LB", 1, 2),
                struct.pack("!LB", 1, 3),
            ],
        )

    def test_have(self):
        connection = _MockTorrentConnection()

        connection.have(3)

        self.assertEqual(connection.sent, [struct.pack("!LBL", 5, 4, 3)])

    def test_request(self):
        connection = _MockTorrentConnection()

        connection.request(1, begin=16384, length=8192)

        # the request names the piece, the offset inside it and the amount
        # of data that is being asked for
        self.assertEqual(
            connection.sent, [struct.pack("!LBLLL", 13, 6, 1, 16384, 8192)]
        )

    def test_extended_handshake(self):
        connection = _MockTorrentConnection()

        connection.extended_handshake()

        self.assertEqual(len(connection.sent), 1)

        # verifies that the message has the proper extended type (20) and
        # the reserved extended handshake identifier (zero)
        length, type, extended = struct.unpack("!LBB", connection.sent[0][:6])
        self.assertEqual(type, 20)
        self.assertEqual(extended, 0)

    def test_request_metadata(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict(ut_metadata=3)

        connection.request_metadata(0)

        self.assertEqual(len(connection.sent), 1)

        # verifies that the message uses the extended identifier assigned
        # by the peer for the metadata extension (three in this case)
        length, type, extended = struct.unpack("!LBB", connection.sent[0][:6])
        self.assertEqual(type, 20)
        self.assertEqual(extended, 3)

    def test_request_metadata_unsupported(self):
        connection = _MockTorrentConnection()
        connection.extensions = dict()

        connection.request_metadata(0)

        # verifies that no message is sent when the peer has not assigned
        # an identifier for the metadata extension (not supported)
        self.assertEqual(connection.sent, [])

    def test_extended(self):
        connection = _MockTorrentConnection()

        connection.extended(5, b"data")

        (length,) = struct.unpack("!L", connection.sent[0][:4])
        self.assertEqual(length, 6)

    def test_metadata_pieces(self):
        connection = _MockTorrentConnection()

        connection.metadata_size = 16384
        self.assertEqual(connection._metadata_pieces(), 1)

        connection.metadata_size = 16385
        self.assertEqual(connection._metadata_pieces(), 2)

        connection.metadata_size = 40000
        self.assertEqual(connection._metadata_pieces(), 3)

    def test_is_alive(self):
        connection = self._make_connection(cls=_RecordTorrentConnection)
        connection.open()

        connection.messages = 1
        clojure = connection.is_alive(timeout=1.0)

        # a connection that keeps both the messages and the rate above the
        # limits is kept alive, being neither closed nor given up on
        connection.messages = 2
        connection.downloaded = int(netius.clients.torrent.SPEED_LIMIT) + 1
        clojure()

        self.assertEqual(connection.closes, [])

    def test_is_alive_silent(self):
        connection = self._make_connection(cls=_RecordTorrentConnection)
        connection.open()

        clojure = connection.is_alive(timeout=1.0)

        # a connection that carries no new message is a stale one, so it
        # is asked to close once the data that is pending is flushed
        clojure()

        self.assertEqual(connection.closes, [dict(flush=True)])

    def test_is_alive_slow(self):
        connection = self._make_connection(cls=_RecordTorrentConnection)
        connection.open()

        clojure = connection.is_alive(timeout=1.0)

        # the messages did move, but the amount of data that came with
        # them is below the limit, which closes the connection as well
        connection.messages = 1
        connection.downloaded = 1
        clojure()

        self.assertEqual(connection.closes, [dict(flush=True)])

    def test_is_alive_closed(self):
        connection = self._make_connection(cls=_RecordTorrentConnection)
        connection.open()

        clojure = connection.is_alive(timeout=1.0)

        connection.close()
        clojure()

        # a connection that is already closed is left alone, as there is
        # nothing left of it to be kept alive
        self.assertEqual(connection.is_closed(), True)
        self.assertEqual(len(connection.closes), 1)

    def _make_connection(self, cls=None):
        cls = cls or netius.clients.TorrentConnection
        connection = cls(owner=self.client, address=("10.0.0.1", 6881))
        connection.task = _MockTorrentTask()
        return connection


class TorrentClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = netius.clients.TorrentClient(poll=netius.Poll, auto_close=False)
        self.client.poll.open()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.client.cleanup()

    def test_peer(self):
        connection = netius.clients.TorrentConnection(
            owner=self.client, address=("10.0.0.1", 6881)
        )
        task = _MockTorrentTask()

        result = self.client.peer(task, "10.0.0.1", 6881, connection=connection)

        # the connection that is given is the one that is used, having the
        # task of it associated so that the blocks may be reached
        self.assertEqual(result, connection)
        self.assertEqual(connection.task, task)

    def test_on_acquire(self):
        connection = _MockTorrentConnection()

        self.client.on_acquire(connection)

        # the acquiring of a connection is what sends the handshake, as
        # that is the first thing a peer expects to receive
        self.assertEqual(len(connection.sent), 1)
        self.assertEqual(connection.sent[0][1:20], b"BitTorrent protocol")

    def test_on_data(self):
        connection = _MockTorrentConnection()
        connection.parser = _MockTorrentParser()

        self.client.on_data(connection, b"data")

        # the data of the peer is handed to the connection, which passes
        # it along to the parser of the protocol
        self.assertEqual(connection.parser.parsed, [b"data"])

    def test_build_connection(self):
        connection = self.client.build_connection(None, ("10.0.0.1", 6881))

        # the connections that the client builds are the ones of the
        # torrent protocol, carrying the client as their owner
        self.assertEqual(isinstance(connection, netius.clients.TorrentConnection), True)
        self.assertEqual(connection.owner, self.client)
        self.assertEqual(connection.address, ("10.0.0.1", 6881))


class _RecordTorrentConnection(netius.clients.TorrentConnection):
    """
    Variant of the connection that keeps the closings that
    are asked of it, together with the way they were asked.
    """

    def __init__(self, *args, **kwargs):
        netius.clients.TorrentConnection.__init__(self, *args, **kwargs)
        self.closes = []

    def close(self, *args, **kwargs):
        self.closes.append(dict(kwargs))
        netius.clients.TorrentConnection.close(self, *args, **kwargs)


class _MockTorrentParser(object):
    """
    Stand in for the parser of the protocol that keeps the
    data that reaches it and the release of itself.
    """

    def __init__(self):
        self.parsed = []
        self.destroyed = False

    def parse(self, data):
        self.parsed.append(data)

    def destroy(self):
        self.destroyed = True


class _MockTorrentConnection(netius.clients.TorrentConnection):

    def __init__(self):
        self.sent = []
        self.triggered = []
        self.extensions = {}
        self.metadata_size = 0
        self.metadata = []
        self.address = ("10.0.0.1", 6881)
        self.peer_id = None
        self.state = netius.clients.torrent.HANDSHAKE_STATE
        self.choked = netius.clients.torrent.CHOKED
        self.bitfield = b""
        self.messages = 0
        self.downloaded = 0
        self.max_requests = 50
        self.pend_requests = 0
        self.requests = []
        self.task = _MockTorrentTask()

    def send(self, data):
        self.sent.append(data)
        return data

    def trigger(self, name, *args, **kwargs):
        self.triggered.append((name, args))


class _MockTorrentTask(object):

    def __init__(self):
        self.metadata = None
        self.blocks = []
        self.pushed = []
        self.data = []
        self.dht = None
        self.info_hash = b"i" * 20
        self.owner = _MockTorrentOwner()

    def has_metadata(self):
        return True if self.metadata else False

    def set_metadata(self, metadata):
        self.metadata = metadata

    def set_data(self, data, index, begin):
        self.data.append((data, index, begin))

    def set_dht(self, address, port):
        self.dht = (address, port)

    def pop_block(self, bitfield):
        if not self.blocks:
            return None
        return self.blocks.pop(0)

    def push_block(self, index, begin):
        self.pushed.append((index, begin))


class _MockTorrentOwner(object):

    peer_id = "netius-peer-id-00000"
