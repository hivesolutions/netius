#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct

import netius.common

class DHTRequest(netius.Request):

    def __init__(
        self,
        peer_id,
        host = "127.0.0.1",
        port = 9090,
        type = "ping",
        callback = None,
        *args,
        **kwargs
    ):
        netius.Request.__init__(self, callback = callback)
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.type = type
        self.args = args,
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
        request = dict(
            t = str(self.id),
            y = "q",
            q = self.type,
            a = query
        )
        return netius.common.bencode(request)

    def ping(self):
        return dict(id = self._peer_id)

    def find_node(self):
        return dict(
            id = self._peer_id,
            target = self.kwargs["target"]
        )

    def get_peers(self):
        return dict(
            id = self._peer_id,
            info_hash = self.kwargs["info_hash"]
        )

    def announce_peer(self):
        return dict(
            id = self._peer_id,
            implied_port = self.kwargs["implied_port"],
            info_hash = self.kwargs["info_hash"],
            port = self.kwargs["port"],
            token = self.kwargs["token"]
        )

    def _get_peer_id(self):
        contact = DHTRequest.contact(self.host, self.port)
        peer_id = netius.legacy.bytes(self.peer_id)
        return peer_id + contact

class DHTResponse(netius.Response):

    def __init__(self, data):
        netius.Response.__init__(self, data)
        self.info = {}

    def parse(self):
        self.info = netius.common.bdecode(self.data)

    def get_id(self):
        t = self.info.get("t", -1)
        return int(t)

    def get_payload(self):
        return self.info.get("r", {})

    def is_error(self):
        return self.info("y", True)

    def is_response(self):
        return self.info("r", True)

class DHTClient(netius.DatagramClient):
    """
    Implementation of the DHT (Distributed hash table) for the torrent
    protocol as the defined in the official specification.

    This implementation is meant to be used in an asynchronous environment
    for maximum performance.

    :see: http://www.bittorrent.org/beps/bep_0005.html
    """

    def ping(self, host, port, peer_id, *args, **kwargs):
        return self.query(type = "ping", *args, **kwargs)

    def find_node(self, *args, **kwargs):
        return self.query(type = "find_node", *args, **kwargs)

    def get_peers(self, *args, **kwargs):
        return self.query(type = "get_peers", *args, **kwargs)

    def query(
        self,
        host = "127.0.0.1",
        port = 9090,
        peer_id = None,
        type = "ping",
        callback = None,
        *args,
        **kwargs
    ):
        request = DHTRequest(
            peer_id,
            host = host,
            port = port,
            type = type,
            callback = callback,
            *args,
            **kwargs
        )
        data = request.request()

        self.add_request(request)

        address = (host, port)
        self.send(data, address)

    def on_data(self, address, data):
        netius.DatagramClient.on_data(self, address, data)

        response = DHTResponse(data)
        response.parse()

        self.on_data_dht(address, response)

    def on_data_dht(self, address, response):
        request = self.get_request(response)
        response.request = request
        self.remove_request(request)

        if not request.callback: return
        request.callback(response)
