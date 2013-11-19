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
import netius.clients

GRANTED = 0x5a
REJECTED = 0x5b
FAILED_CLIENT = 0x5c
FAILED_AUTH = 0x5d

GRANTED_EXTRA = 0x00

class SOCKSConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.SOCKSParser(self)

        self.parser.bind("on_data", self.on_data)
        self.parser.bind("on_auth", self.on_auth)

    def send_response(self, status = GRANTED):
        data = struct.pack("!BBHI", 0, status, 0, 0)
        self.send(data)

    def send_response_extra(self, status = GRANTED_EXTRA):
        version = self.parser.version
        type = self.parser.type
        port = self.parser.port
        address = self.parser.get_address()
        format = "!BBBB%dsH" % len(address)
        data = struct.pack(format, version, status, 0, type, address, port)
        self.send(data)

    def send_auth(self, version = None, method = 0x00):
        version = version or self.parser.version
        data = struct.pack("!BB", version, method)
        self.send(data)

    def get_version(self):
        return self.parser.version

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_socks(self, self.parser)

    def on_auth(self):
        self.owner.on_auth_socks(self, self.parser)

class SOCKSServer(netius.StreamServer):

    def __init__(self, rules = {}, *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.rules = rules
        self.conn_map = {}

        self.raw_client = netius.clients.RawClient(
            thread = False,
            *args,
            **kwargs
        )
        self.raw_client.bind("connect", self._on_raw_connect)
        self.raw_client.bind("data", self._on_raw_data)
        self.raw_client.bind("close", self._on_raw_close)

        self.container = netius.Container(*args, **kwargs)
        self.container.add_base(self)
        self.container.add_base(self.raw_client)

    def start(self):
        self.raw_client.load()
        self.container.start()

    def stop(self):
        self.container.stop()

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.send(data)
        else: connection.parse(data)

    def on_data_socks(self, connection, parser):
        host = parser.get_host()
        port = parser.port

        _connection = self.raw_client.connect(host, port)
        connection.tunnel_c = _connection
        self.conn_map[_connection] = connection

    def on_auth_socks(self, connection, parser):
        auth_methods = parser.auth_methods

        if not 0 in auth_methods:
            raise netius.ParserError("Authentication is not supported")

        connection.send_auth(method = 0)

    def on_connection_d(self, connection):
        netius.StreamServer.on_connection_d(self, connection)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.close()

    def new_connection(self, socket, address, ssl = False):
        return SOCKSConnection(self, socket, address, ssl = ssl)

    def _on_raw_connect(self, client, _connection):
        connection = self.conn_map[_connection]
        version = connection.get_version()
        if version == 0x04: connection.send_response(status = GRANTED)
        elif version == 0x05: connection.send_response_extra(status = GRANTED_EXTRA)

    def _on_raw_data(self, client, _connection, data):
        connection = self.conn_map[_connection]
        connection.send(data)

    def _on_raw_close(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.close(flush = True)
        del self.conn_map[_connection]

if __name__ == "__main__":
    import logging
    server = SOCKSServer(level = logging.INFO)
    server.serve(env = True)
