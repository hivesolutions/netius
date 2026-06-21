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
import unittest

import netius.common
import netius.clients


class DHTRequestTest(unittest.TestCase):

    def test_request(self):
        request = netius.clients.DHTRequest(
            b"a" * 20, host="1.2.3.4", port=6881, type="get_peers", info_hash=b"b" * 20
        )

        data = request.request()
        info = netius.common.bdecode(data)

        self.assertEqual(info["y"], "q")
        self.assertEqual(info["q"], "get_peers")
        self.assertEqual(info["a"]["info_hash"], "b" * 20)

    def test_peer_id_length(self):
        request = netius.clients.DHTRequest(
            b"a" * 20, host="1.2.3.4", port=6881, type="ping"
        )

        # the node identifier sent in a query must be exactly the (20 byte)
        # peer identifier, otherwise nodes reject the query as invalid
        self.assertEqual(len(request._peer_id), 20)
        self.assertEqual(request.ping()["id"], b"a" * 20)


class DHTResponseTest(unittest.TestCase):

    def test_get_id(self):
        response = netius.clients.DHTResponse(b"")
        response.info = dict(t="42")

        self.assertEqual(response.get_id(), 42)

    def test_get_id_invalid(self):
        response = netius.clients.DHTResponse(b"")
        response.info = dict(t="\xe6\x12=.")

        # a binary (non numeric) transaction identifier should yield an
        # invalid value instead of raising so the response is just ignored
        self.assertEqual(response.get_id(), -1)

    def test_parse_malformed(self):
        response = netius.clients.DHTResponse(b"d1:ad2:id20:")

        # a malformed (truncated) datagram should raise an error that is
        # caught by the data handler so the response is silently ignored
        self.assertRaises(
            (netius.ParserError, IndexError, struct.error), response.parse
        )

    def test_get_nodes(self):
        nodes = _contact(b"a" * 20, "1.2.3.4", 6881)
        nodes += _contact(b"b" * 20, "5.6.7.8", 1234)

        response = netius.clients.DHTResponse(b"")
        response.info = dict(r=dict(nodes=nodes))

        result = response.get_nodes()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].peer_id, b"a" * 20)
        self.assertEqual(result[0].host, "1.2.3.4")
        self.assertEqual(result[0].port, 6881)
        self.assertEqual(result[1].peer_id, b"b" * 20)
        self.assertEqual(result[1].host, "5.6.7.8")
        self.assertEqual(result[1].port, 1234)

    def test_get_nodes_empty(self):
        response = netius.clients.DHTResponse(b"")
        response.info = dict(r=dict())

        result = response.get_nodes()

        self.assertEqual(result, [])

    def test_is_error(self):
        response = netius.clients.DHTResponse(b"")

        response.info = dict(y="e")
        self.assertEqual(response.is_error(), True)

        response.info = dict(y="r")
        self.assertEqual(response.is_error(), False)

    def test_is_response(self):
        response = netius.clients.DHTResponse(b"")

        response.info = dict(r=dict())
        self.assertEqual(response.is_response(), True)

        response.info = dict(y="e")
        self.assertEqual(response.is_response(), False)


class DHTNodeTest(unittest.TestCase):

    def test_unpack(self):
        data = _contact(b"a" * 20, "1.2.3.4", 6881)
        data += _contact(b"b" * 20, "5.6.7.8", 1234)

        nodes = netius.clients.DHTNode.unpack(data)

        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0].peer_id, b"a" * 20)
        self.assertEqual(nodes[0].host, "1.2.3.4")
        self.assertEqual(nodes[0].port, 6881)
        self.assertEqual(nodes[1].peer_id, b"b" * 20)
        self.assertEqual(nodes[1].host, "5.6.7.8")
        self.assertEqual(nodes[1].port, 1234)

    def test_unpack_partial(self):
        data = _contact(b"a" * 20, "1.2.3.4", 6881)

        nodes = netius.clients.DHTNode.unpack(data + b"trailing")

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].host, "1.2.3.4")
        self.assertEqual(nodes[0].port, 6881)

    def test_distance(self):
        node = netius.clients.DHTNode(b"\x00" * 20)

        result = node.distance(b"\x00" * 20)
        self.assertEqual(result, 0)

        result = node.distance(b"\x00" * 19 + b"\x01")
        self.assertEqual(result, 1)

        result = node.distance(b"\xff" + b"\x00" * 19)
        self.assertEqual(result, 0xFF << (19 * 8))

    def test_is_valid(self):
        node = netius.clients.DHTNode(b"a" * 20, host="1.2.3.4", port=6881)
        self.assertEqual(node.is_valid(), True)

        node = netius.clients.DHTNode(b"a" * 20, host="1.2.3.4", port=0)
        self.assertEqual(node.is_valid(), False)

        node = netius.clients.DHTNode(b"a" * 20, host="0.0.0.0", port=6881)
        self.assertEqual(node.is_valid(), False)


class DHTRoutingTableTest(unittest.TestCase):

    def test_add(self):
        routing = netius.clients.DHTRoutingTable(b"\x00" * 20)
        node = netius.clients.DHTNode(b"a" * 20, host="1.2.3.4", port=6881)

        result = routing.add(node)
        self.assertEqual(result, True)

        result = routing.add(node)
        self.assertEqual(result, False)

    def test_add_full(self):
        routing = netius.clients.DHTRoutingTable(b"\x00" * 20, bucket_size=1)

        first = netius.clients.DHTNode(b"\x00" * 19 + b"\x10")
        second = netius.clients.DHTNode(b"\x00" * 19 + b"\x11")

        result = routing.add(first)
        self.assertEqual(result, True)

        result = routing.add(second)
        self.assertEqual(result, False)

    def test_closest(self):
        routing = netius.clients.DHTRoutingTable(b"\x00" * 20)

        far = netius.clients.DHTNode(b"\xff" * 20, host="1.1.1.1")
        near = netius.clients.DHTNode(b"\x00" * 19 + b"\x01", host="2.2.2.2")

        routing.add(far)
        routing.add(near)

        result = routing.closest(b"\x00" * 20)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].host, "2.2.2.2")
        self.assertEqual(result[1].host, "1.1.1.1")

    def test_closest_count(self):
        routing = netius.clients.DHTRoutingTable(b"\x00" * 20)

        first = netius.clients.DHTNode(b"\x00" * 19 + b"\x01", host="1.1.1.1")
        second = netius.clients.DHTNode(b"\x00" * 19 + b"\x02", host="2.2.2.2")

        routing.add(first)
        routing.add(second)

        result = routing.closest(b"\x00" * 20, count=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].host, "1.1.1.1")


class DHTClientTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.client = _MockDHTClient()

    def test_routing(self):
        routing = self.client.routing(b"\x00" * 20)

        self.assertIsInstance(routing, netius.clients.DHTRoutingTable)

        # verifies that a second call returns the very same routing
        # table instance, meaning that it is correctly cached
        self.assertEqual(self.client.routing(b"\x00" * 20), routing)

    def test_bootstrap(self):
        nodes = (("1.2.3.4", 6881), ("5.6.7.8", 1234))

        self.client.bootstrap(b"\x00" * 20, nodes=nodes)

        self.assertEqual(len(self.client.queries), 2)
        self.assertEqual(self.client.queries[0]["host"], "1.2.3.4")
        self.assertEqual(self.client.queries[0]["port"], 6881)
        self.assertEqual(self.client.queries[0]["type"], "find_node")
        self.assertEqual(self.client.queries[0]["target"], b"\x00" * 20)

    def test_lookup(self):
        nodes = (("1.2.3.4", 6881),)

        self.client.lookup(b"\x00" * 20, b"\x01" * 20, nodes=nodes)

        self.assertEqual(len(self.client.queries), 1)
        self.assertEqual(self.client.queries[0]["host"], "1.2.3.4")
        self.assertEqual(self.client.queries[0]["target"], b"\x01" * 20)

    def test_lookup_get_peers(self):
        nodes = (("1.2.3.4", 6881),)

        self.client.lookup(b"\x00" * 20, b"\x01" * 20, type="get_peers", nodes=nodes)

        self.assertEqual(len(self.client.queries), 1)
        self.assertEqual(self.client.queries[0]["type"], "get_peers")
        self.assertEqual(self.client.queries[0]["info_hash"], b"\x01" * 20)

    def test_lookup_unique(self):
        nodes = (("1.2.3.4", 6881), ("1.2.3.4", 6881))

        self.client.lookup(b"\x00" * 20, b"\x01" * 20, nodes=nodes)

        # verifies that the same host is only queried once even when
        # it is present more than once in the initial set of nodes
        self.assertEqual(len(self.client.queries), 1)


class _MockDHTClient(netius.clients.DHTClient):

    def __init__(self):
        self.queries = []
        self._routing = None

    def query(self, host="127.0.0.1", port=9090, peer_id=None, type="ping", **kwargs):
        query = dict(host=host, port=port, peer_id=peer_id, type=type)
        query.update(kwargs)
        self.queries.append(query)

    def debug(self, object, *args, **kwargs):
        pass


def _contact(peer_id, host, port):
    addr = netius.common.ip4_to_addr(host)
    return peer_id + struct.pack("!LH", addr, port)
