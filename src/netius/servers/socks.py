#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct

import netius.common
import netius.clients

GRANTED = 0x5a
REJECTED = 0x5b
FAILED_CLIENT = 0x5c
FAILED_AUTH = 0x5d

GRANTED_EXTRA = 0x00

BUFFER_RATIO = 1.5
""" The ratio for the calculus of the internal socket
buffer size from the maximum pending buffer size """

MIN_RATIO = 0.8
""" The ration for the calculus of the minimum pending
value this is going to be used to re-enable the operation
and start the filling of the buffer again """

MAX_PENDING = 65536
""" The size in bytes considered to be the maximum
allowed in the sending buffer, this maximum value
avoids the starvation of the producer to consumer
relation that could cause memory problems """

class SOCKSConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open(): return
        self.parser = netius.common.SOCKSParser(self)
        self.parser.bind("on_data", self.on_data)
        self.parser.bind("on_auth", self.on_auth)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed(): return
        if self.parser: self.parser.destroy()

    def send_response(self, status = GRANTED):
        data = struct.pack("!BBHI", 0, status, 0, 0)
        return self.send(data)

    def send_response_extra(self, status = GRANTED_EXTRA):
        version = self.parser.version
        type = self.parser.type
        port = self.parser.port
        address = self.parser.get_address()
        format = "!BBBB%dsH" % len(address)
        data = struct.pack(format, version, status, 0, type, address, port)
        return self.send(data)

    def send_auth(self, version = None, method = 0x00):
        version = version or self.parser.version
        data = struct.pack("!BB", version, method)
        return self.send(data)

    def get_version(self):
        return self.parser.version

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_socks(self, self.parser)

    def on_auth(self):
        self.owner.on_auth_socks(self, self.parser)

class SOCKSServer(netius.ServerAgent):
    """
    SOCKS base server class to be used as an implementation of the
    RFC 1928 or SOCKSv5 and the SOCKSv4 protocols.

    There are some aspects of the implementation that may not be
    performant driven for readability purposes.
    """

    def __init__(self, rules = {}, throttle = True, max_pending = MAX_PENDING, *args, **kwargs):
        netius.ContainerServer.__init__(
            self,
            receive_buffer_c = int(max_pending * BUFFER_RATIO),
            send_buffer_c = int(max_pending * BUFFER_RATIO),
            *args,
            **kwargs
        ) # @todo how is this going to work (receive buffer control)
        self.rules = rules
        self.throttle = throttle
        self.max_pending = max_pending
        self.min_pending = int(max_pending * MIN_RATIO)
        self.conn_map = {}

        _loop, self.raw_protocol = netius.clients.RawClient.protocol()
        self.raw_protocol.bind("connect", self._on_raw_connect)
        self.raw_protocol.bind("data", self._on_raw_data)
        self.raw_protocol.bind("close", self._on_raw_close)

        #@todo this does not make sense
        self.add_base(self)
        self.add_base(self.raw_client)

    def cleanup(self):
        netius.ContainerServer.cleanup(self)
        self.raw_client.destroy()

    def on_data(self, connection, data):
        netius.ContainerServer.on_data(self, connection, data)

        # tries to retrieve the reference to the tunnel connection
        # currently set in the connection in case it does not exists
        # (initial handshake) runs the parse step on the data and then
        # returns immediately (not going to send it back)
        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c: connection.parse(data); return

        # verifies that the current size of the pending buffer is greater
        # than the maximum size for the pending buffer the read operations
        # if that the case the read operations must be disabled
        should_disable = self.throttle and tunnel_c.is_exhausted()
        if should_disable: connection.disable_read()

        # performs the sending operation on the data but uses the throttle
        # callback so that the connection read operations may be resumed if
        # the buffer has reached certain (minimum) levels
        tunnel_c.send(data, callback = self._throttle)

    def on_data_socks(self, connection, parser):
        host = parser.get_host()
        port = parser.port

        _connection = self.raw_client.connect(host, port)
        _connection.max_pending = self.max_pending
        _connection.min_pending = self.min_pending
        connection.tunnel_c = _connection
        self.conn_map[_connection] = connection

    def on_auth_socks(self, connection, parser):
        auth_methods = parser.auth_methods

        if not 0 in auth_methods:
            raise netius.ParserError("Authentication is not supported")

        connection.send_auth(method = 0)

    def on_connection_d(self, connection):
        netius.ContainerServer.on_connection_d(self, connection)

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c

        if tunnel_c: tunnel_c.close()

        setattr(connection, "tunnel_c", None)

    def new_connection(self, socket, address, ssl = False):
        return SOCKSConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            max_pending = self.max_pending,
            min_pending = self.min_pending
        )

    def _throttle(self, _connection):
        if not _connection.is_restored(): return
        connection = self.conn_map[_connection]
        if not connection.renable == False: return
        connection.enable_read()
        self.reads((connection.socket,), state = False)

    def _raw_throttle(self, connection):
        if not connection.is_restored(): return

        tunnel_c = hasattr(connection, "tunnel_c") and connection.tunnel_c
        if not tunnel_c: return
        if not tunnel_c.renable == False: return

        tunnel_c.enable_read()
        self.raw_client.reads((tunnel_c.socket,), state = False)

    def _on_raw_connect(self, client, _connection):
        connection = self.conn_map[_connection]
        version = connection.get_version()
        if version == 0x04: connection.send_response(status = GRANTED)
        elif version == 0x05: connection.send_response_extra(status = GRANTED_EXTRA)

    def _on_raw_data(self, client, _connection, data):
        connection = self.conn_map[_connection]
        should_disable = self.throttle and connection.is_exhausted()
        if should_disable: _connection.disable_read()
        connection.send(data, callback = self._raw_throttle)

    def _on_raw_close(self, client, _connection):
        connection = self.conn_map[_connection]
        connection.close(flush = True)
        del self.conn_map[_connection]

if __name__ == "__main__":
    import logging
    server = SOCKSServer(level = logging.INFO)
    server.serve(env = True)
else:
    __path__ = []
