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

import os
import socket
import struct
import binascii

import netius.common

PEER_ID_SIZE = 20
""" The size in bytes of the node/peer identifier as defined
by the official DHT specification (BEP 0005) """

CONTACT_SIZE = 6
""" The size in bytes of the compact contact information (IPv4
address plus port) appended to a node identifier """

NODE_SIZE = PEER_ID_SIZE + CONTACT_SIZE
""" The size in bytes of a single compact node information entry
as found in the 'nodes' field of a find_node/get_peers response """

BUCKET_SIZE = 8
""" The maximum number of nodes that may be stored in a single
bucket of the routing table (the 'k' value in Kademlia) """

BOOTSTRAP_NODES = (
    ("router.bittorrent.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
)
""" The sequence of well known nodes that may be used to bootstrap
the routing table when no other contacts are available """


class DHTRequest(netius.Request):

    def __init__(
        self,
        peer_id,
        host="127.0.0.1",
        port=9090,
        type="ping",
        callback=None,
        *args,
        **kwargs
    ):
        netius.Request.__init__(self, callback=callback)
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.type = type
        self.args = (args,)
        self.kwargs = kwargs
        self._peer_id = self._get_peer_id()

    @classmethod
    def contact(cls, host, port):
        addr = netius.common.ip4_to_addr(host)
        return struct.pack("!LH", addr, port)

    def request(self):
        if not hasattr(self, self.type):
            raise netius.ParserError("Invalid type '%s'" % self.type)
        method = getattr(self, self.type)
        query = method()
        request = dict(t=str(self.id), y="q", q=self.type, a=query)
        return netius.common.bencode(request)

    def ping(self):
        return dict(id=self._peer_id)

    def find_node(self):
        return dict(id=self._peer_id, target=self.kwargs["target"])

    def get_peers(self):
        return dict(id=self._peer_id, info_hash=self.kwargs["info_hash"])

    def announce_peer(self):
        return dict(
            id=self._peer_id,
            implied_port=self.kwargs["implied_port"],
            info_hash=self.kwargs["info_hash"],
            port=self.kwargs["port"],
            token=self.kwargs["token"],
        )

    def _get_peer_id(self):
        # the node identifier sent in a query must be exactly the (20 byte)
        # peer identifier, no contact information should be appended to it
        # otherwise nodes reject the query with a "invalid value for 'id'"
        return netius.legacy.bytes(self.peer_id)


class DHTResponse(netius.Response):

    def __init__(self, data):
        netius.Response.__init__(self, data)
        self.info = {}

    def parse(self):
        self.info = netius.common.bdecode(self.data)

    def get_id(self):
        # tries to convert the transaction identifier into an integer
        # value, some (misbehaving) nodes echo back a binary transaction
        # identifier that cannot be parsed, in that case an invalid value
        # is returned so that the response is not matched to any request
        t = self.info.get("t", -1)
        try:
            return int(t)
        except (TypeError, ValueError):
            return -1

    def get_payload(self):
        return self.info.get("r", {})

    def get_nodes(self):
        payload = self.get_payload()
        nodes = payload.get("nodes", b"")
        return DHTNode.unpack(nodes)

    def is_error(self):
        return self.info("y", True)

    def is_response(self):
        return self.info("r", True)


class DHTNode(object):
    """
    Object representing a single node in the DHT network, the node
    is defined by its identifier and by the contact information (host
    and port) that allows the reaching of it through the network.

    A node may be considered an entry in the routing table and the
    distance between two nodes is defined by the bitwise XOR of their
    identifiers as the defined in the Kademlia specification.

    :see: http://www.bittorrent.org/beps/bep_0005.html
    """

    def __init__(self, peer_id, host="127.0.0.1", port=9090):
        self.peer_id = netius.legacy.bytes(peer_id)
        self.host = host
        self.port = port

    @classmethod
    def unpack(cls, data):
        # ensures that the compact information is a bytes object as it
        # may have been decoded into a (latin-1) string by the bdecode
        # operation, this is required for the struct unpacking to work
        data = netius.legacy.bytes(data)

        # starts the list that is going to store the various node
        # objects unpacked from the provided compact information data
        nodes = []

        # iterates over the complete set of node entries present in the
        # data buffer, each entry has a fixed size and is composed by
        # the node identifier followed by the compact contact information
        for index in range(0, len(data) - NODE_SIZE + 1, NODE_SIZE):
            entry = data[index : index + NODE_SIZE]
            peer_id = entry[:PEER_ID_SIZE]
            contact = entry[PEER_ID_SIZE:NODE_SIZE]
            addr, port = struct.unpack("!LH", contact)
            host = netius.common.addr_to_ip4(addr)
            nodes.append(cls(peer_id, host=host, port=port))

        # returns the final list of nodes unpacked from the compact
        # information data provided as the input of the method
        return nodes

    def distance(self, peer_id):
        peer_id = netius.legacy.bytes(peer_id)
        own = self._peer_id_int()
        other = netius.common.bytes_to_integer(peer_id)
        return own ^ other

    def is_valid(self):
        # verifies that the port is within the valid range, a zero (or out
        # of range) port is returned by some misbehaving nodes and cannot
        # be used as the target of a datagram
        if self.port <= 0 or self.port > 65535:
            return False

        # verifies that the host is a routable address, the unspecified
        # address cannot be used as the target of a datagram and would
        # otherwise raise an error at the socket level
        if self.host in ("0.0.0.0", ""):
            return False

        return True

    def _peer_id_int(self):
        return netius.common.bytes_to_integer(self.peer_id)


class DHTRoutingTable(object):
    """
    Structure that holds the complete set of nodes known by the
    client organized into buckets according to their distance to
    the local (owner) node identifier.

    Each bucket may store at most a fixed amount of nodes and is
    going to be used to provide the set of nodes closest to a given
    target identifier, as required by the iterative lookup operations.
    """

    def __init__(self, peer_id, bucket_size=BUCKET_SIZE):
        self.peer_id = netius.legacy.bytes(peer_id)
        self.bucket_size = bucket_size
        self.buckets = {}

    def add(self, node):
        # determines the index of the bucket associated with the node
        # and retrieves (creating if required) the proper bucket list
        index = self._bucket_index(node)
        bucket = self.buckets.setdefault(index, [])

        # in case the node is already present in the bucket returns
        # immediately as there's nothing remaining to be done
        if self._has_node(bucket, node):
            return False

        # in case the bucket is already full no new node may be added
        # to it and so the operation is ignored returning invalid
        if len(bucket) >= self.bucket_size:
            return False

        # adds the node to the proper bucket and returns valid indicating
        # that the node was correctly added to the routing table
        bucket.append(node)
        return True

    def closest(self, target, count=BUCKET_SIZE):
        # gathers the complete set of nodes stored in the various buckets
        # into a single sequence to be ordered by distance to the target
        nodes = []
        for bucket in self.buckets.values():
            nodes.extend(bucket)

        # sorts the nodes by the (XOR) distance of their identifier to the
        # target identifier so that the closest ones come first
        nodes.sort(key=lambda node: node.distance(target))

        # returns only the requested amount of nodes (the closest ones)
        # from the complete ordered sequence of nodes
        return nodes[:count]

    def _bucket_index(self, node):
        own = netius.common.bytes_to_integer(self.peer_id)
        distance = own ^ node._peer_id_int()
        if distance == 0:
            return 0
        return distance.bit_length() - 1

    def _has_node(self, bucket, node):
        for _node in bucket:
            if _node.peer_id == node.peer_id:
                return True
        return False


class DHTClient(netius.DatagramClient):
    """
    Implementation of the DHT (Distributed hash table) for the torrent
    protocol as the defined in the official specification.

    This implementation is meant to be used in an asynchronous environment
    for maximum performance.

    :see: http://www.bittorrent.org/beps/bep_0005.html
    """

    def ping(self, host, port, peer_id, *args, **kwargs):
        return self.query(type="ping", *args, **kwargs)

    def find_node(self, *args, **kwargs):
        return self.query(type="find_node", *args, **kwargs)

    def get_peers(self, *args, **kwargs):
        return self.query(type="get_peers", *args, **kwargs)

    def routing(self, peer_id):
        # verifies if a routing table is already associated with the
        # current client and if that's not the case creates a new one
        # bound to the provided (local) peer identifier
        if not hasattr(self, "_routing") or self._routing == None:
            self._routing = DHTRoutingTable(peer_id)
        return self._routing

    def bootstrap(self, peer_id, target=None, nodes=None, callback=None, **kwargs):
        # uses the provided target identifier or falls back to the local
        # peer identifier, this is the value around which the routing
        # table is going to be populated by the lookup operation
        target = target or peer_id

        # uses the provided sequence of bootstrap nodes or falls back to
        # the globally defined set of well known nodes, this is the entry
        # point for joining the network when no contacts are known
        nodes = nodes or BOOTSTRAP_NODES

        # runs an iterative find_node lookup around the target using the
        # bootstrap nodes as the initial set of contacts, this populates
        # the routing table with the nodes closest to the target
        return self.lookup(
            peer_id, target, type="find_node", nodes=nodes, callback=callback, **kwargs
        )

    def lookup(
        self, peer_id, target, type="find_node", nodes=None, callback=None, **kwargs
    ):
        # retrieves the routing table associated with the local peer
        # identifier and uses it (together with the provided nodes) to
        # build the initial set of contacts to be queried, falling back
        # to the well known bootstrap nodes in case no contacts exist yet
        routing = self.routing(peer_id)
        nodes = nodes or routing.closest(target) or self._bootstrap_nodes()

        # builds the set of nodes already queried (keyed by the contact
        # tuple) so that the same node is not queried twice and the list
        # that is going to aggregate the peers discovered by the lookup
        queried = set()
        peers = []

        def on_response(response):
            # in case the response is not valid (eg: timeout) returns
            # immediately as there's nothing remaining to be handled
            if not response:
                return

            # adds the eventual peers present in the response payload
            # to the aggregated list of peers discovered by the lookup
            payload = response.get_payload()
            nodes = response.get_nodes()
            peers.extend(payload.get("values", []))

            # prints a debug message about the response that has been
            # received (including the contact of the responding node)
            # providing some development/tracing capabilities
            request = response.request
            self.debug(
                "Received DHT response from %s:%d with %d nodes and %d peers"
                % (
                    request.host,
                    request.port,
                    len(nodes),
                    len(payload.get("values", [])),
                )
            )

            # in case a (user) callback is defined it's called with the
            # response so that the caller may inspect/handle it as the
            # iterative lookup operation makes progress
            if callback:
                callback(response)

            # folds the nodes returned by the response into the routing
            # table (for later reuse) and queries every one of them that
            # has not been queried yet, nodes return the contacts closest
            # to the target so this is what drives the lookup towards the
            # nodes that are responsible for (and hold) the peer values
            for node in nodes:
                routing.add(node)
                _query(node)

        def _query(node):
            # in case the node does not represent a valid (routable) contact
            # returns immediately as it cannot be used as a query target
            if not node.is_valid():
                return

            # in case the node has already been queried returns immediately
            # avoiding the querying of the same node more than once
            contact = (node.host, node.port)
            if contact in queried:
                return
            queried.add(contact)

            # prints a debug message about the node that is going to be
            # queried as part of the iterative lookup operation
            self.debug("Querying DHT node %s:%d" % (node.host, node.port))

            # determines the proper query argument according to the type
            # of lookup being performed (info_hash for get_peers, target
            # otherwise) and runs the query against the target node
            if type == "get_peers":
                extra = dict(info_hash=target)
            else:
                extra = dict(target=target)
            self.query(
                host=node.host,
                port=node.port,
                peer_id=peer_id,
                type=type,
                callback=on_response,
                **extra
            )

        # queries the initial set of nodes directly so that the iterative
        # lookup operation may be started, these contacts have an unknown
        # identifier and so are not folded into the routing table (which is
        # reserved for the proper nodes discovered through the responses)
        for node in nodes:
            if not isinstance(node, DHTNode):
                host, port = node
                node = DHTNode(peer_id, host=host, port=port)
            _query(node)

        # returns the (still being populated) list of peers so that the
        # caller may inspect it once the lookup operation is complete
        return peers

    def _bootstrap_nodes(self):
        # resolves the well known bootstrap nodes into their IPv4 address as
        # the contact information requires a dotted address instead of a name,
        # nodes that cannot be resolved are skipped (best effort operation)
        nodes = []
        for host, port in BOOTSTRAP_NODES:
            try:
                host = socket.gethostbyname(host)
            except socket.error:
                continue
            nodes.append((host, port))
        return nodes

    def query(
        self,
        host="127.0.0.1",
        port=9090,
        peer_id=None,
        type="ping",
        callback=None,
        *args,
        **kwargs
    ):
        request = DHTRequest(
            peer_id, host=host, port=port, type=type, callback=callback, *args, **kwargs
        )
        data = request.request()

        self.add_request(request)

        address = (host, port)
        self.send(data, address)

    def on_data(self, address, data):
        netius.DatagramClient.on_data(self, address, data)

        # creates the DHT response with the provided data stream and tries
        # to parse it, this operation is risky as the message may be
        # malformed (eg: foreign or corrupted datagram) in which case the
        # response is silently ignored as there's nothing to be handled
        response = DHTResponse(data)
        try:
            response.parse()
        except (netius.ParserError, IndexError, struct.error):
            return

        self.on_data_dht(address, response)

    def on_data_dht(self, address, response):
        # tries to retrieve the request associated with the current
        # response and in case none is found returns immediately as
        # there's nothing remaining to be done
        request = self.get_request(response)
        if not request:
            return

        # associates the request with the response and removes it from
        # the current request structures so that a callback is no longer
        # answered for the same response
        response.request = request
        self.remove_request(request)

        # in case no callback is not defined for the request returns
        # immediately as there's nothing else remaining to be done,
        # otherwise calls the proper callback with the response
        if not request.callback:
            return
        request.callback(response)


if __name__ == "__main__":
    netius.setup_logging()

    seen = dict(nodes=set(), peers=set())

    def on_response(response):
        # in case the response is not valid (eg: timeout) returns
        # immediately as there's nothing remaining to be handled
        if not response:
            print("Timeout in lookup")
            return

        # iterates over the complete set of nodes returned by the
        # response printing the contact information of the ones that
        # have not been printed yet (avoids duplicate output)
        for node in response.get_nodes():
            contact = (node.host, node.port)
            if contact in seen["nodes"]:
                continue
            seen["nodes"].add(contact)
            print("node %s:%d" % (node.host, node.port))

        # iterates over the eventual peers (values) returned by the
        # response, these are the actual peers sharing the info hash
        payload = response.get_payload()
        for value in payload.get("values", []):
            value = netius.legacy.bytes(value)
            addr, port = struct.unpack("!LH", value)
            contact = (netius.common.addr_to_ip4(addr), port)
            if contact in seen["peers"]:
                continue
            seen["peers"].add(contact)
            print("peer %s:%d" % contact)

    # retrieves the values of the configuration variables that are
    # going to be used to perform the DHT lookup, the info hash is
    # provided as an hexadecimal string and decoded into raw bytes
    info_hash = netius.conf("DHT_INFO_HASH", "d540fc48eb12f2833163eed6421d449dd8f1ce1f")
    info_hash = binascii.unhexlify(info_hash)

    # retrieves the interval (in seconds) between consecutive lookup
    # rounds, each round re-seeds the lookup from the bootstrap nodes
    interval = netius.conf("DHT_INTERVAL", 5, cast=int)

    # generates a random (local) peer identifier with the proper size
    # to be used as the origin of the various queries to be performed
    peer_id = os.urandom(PEER_ID_SIZE)

    # resolves the well known bootstrap nodes into their IPv4 address as
    # the contact information requires a dotted address instead of a name
    nodes = [(socket.gethostbyname(host), port) for host, port in BOOTSTRAP_NODES]

    # creates the DHT client that is going to be used for the running
    # of the various get_peers lookup rounds against the info hash
    client = DHTClient()

    def lookup_round():
        # in case at least one peer has already been found stops the
        # main loop as there's nothing else remaining to be done, this
        # is the termination condition of the lookup loop
        if seen["peers"]:
            print(
                "Found %d peer(s) and %d node(s), stopping"
                % (len(seen["peers"]), len(seen["nodes"]))
            )
            netius.compat_loop(client).stop()
            return

        # runs a new get_peers lookup round seeded from the bootstrap
        # nodes, the persistent routing table makes each round resume
        # from the closest nodes discovered by the previous ones
        print("Running lookup round (%d nodes known so far) ..." % len(seen["nodes"]))
        client.lookup(
            peer_id, info_hash, type="get_peers", nodes=nodes, callback=on_response
        )

        # schedules the next lookup round to be executed after the
        # configured interval keeping the loop running until peers
        # are found (or the process is interrupted by the user)
        client.delay(lookup_round, timeout=interval, safe=True)

    # runs the first lookup round, this also bootstraps the client's
    # main loop thread so that the process stays alive while running
    lookup_round()

    # joins the client's main loop thread so that the process stays
    # alive while the lookup rounds are being performed and answered
    client.join()
else:
    __path__ = []
