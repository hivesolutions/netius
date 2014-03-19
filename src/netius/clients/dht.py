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

IDENTIFIER = 0x0000
""" The global class identifier value that is going to
be used when assigning new values to the request """

class DHTResponse(object):

    def __init__(self, data):
        self.data = data
        self.info = {}

    def parse(self):
        self.info = netius.common.bdecode(self.data)

class DHTRequest(object):

    def __init__(
        self,
        host,
        port,
        peer_id,
        type = "ping",
        callback = None,
        *args,
        **kwargs
    ):
        self.id = self._generate_id()
        self.host = host
        self.port = port
        self.peer_id = peer_id
        self.type = type
        self.callback = callback
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
        request = method()
        request["t"] = str(self.id)
        request["y"] = "q"
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

    def get_peer_id(self):
        contact = DHTRequest.contact(self.host, self.port)
        return self.pee_id + contact

    def _generate_id(self):
        global IDENTIFIER
        IDENTIFIER = (IDENTIFIER + 1) & 0xffff
        return IDENTIFIER

class DHTClient(netius.DatagramClient):
    """
    Implementation of the DHT (Distributed hash table) for the torrent
    protocol as the defined in the official specification.

    This implementation is meant to be used in an asynchronous environment
    for maximum performance.

    @see: http://www.bittorrent.org/beps/bep_0005.html
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
            type = type,
            callback = callback,
            *args,
            **kwargs
        )
        data = request.request()

        address = (host, port)
        print "SENT-> %s" % data
        self.send(data, address)

    def on_data(self, address, data):
        netius.DatagramClient.on_data(self, address, data)

        response = DHTResponse(data)
        response.parse()

        self.on_data_dht(address, response)

    def on_data_dht(self, address, response):
        print response.info
