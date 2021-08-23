#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import uuid
import socket

from . import observer
from . import transport

BUFFER_SIZE_S = None
""" The size of both the send and receive buffers for
the socket representing the server, this socket is
responsible for the handling of the new connections """

BUFFER_SIZE_C = None
""" The size of the buffers (send and receive) that
is going to be set on the on the sockets created by
the server (client sockets), this is critical for a
good performance of the server (large value) """

class Service(observer.Observable):
    """
    Top level class responsible for the single representation
    of the meta-data associated with a service.

    This is considered to be the equivalent to a connection object
    for the servers (as opposed to clients).

    This implementation takes inspiration from the asyncio stream
    and should be very compatible in terms of API.
    """

    def __init__(
        self,
        owner = None,
        transport = None,
        socket = None,
        ssl = False,
        receive_buffer_s = BUFFER_SIZE_S,
        send_buffer_s = BUFFER_SIZE_S,
        receive_buffer_c = BUFFER_SIZE_C,
        send_buffer_c = BUFFER_SIZE_C
    ):
        observer.Observable.__init__(self)
        self.id = str(uuid.uuid4())
        self.owner = owner
        self.transport = transport
        self.socket = socket
        self.ssl = ssl
        self.receive_buffer_s = receive_buffer_s
        self.send_buffer_s = send_buffer_s
        self.receive_buffer_c = receive_buffer_c
        self.send_buffer_c = send_buffer_c

    def on_socket_c(self, socket_c, address):
        connection = self.build_connection(socket_c, address)
        _transport = transport.TransportStream(self, connection)
        self.trigger("connection", connection)

    def build_connection(self, socket_c, address):
        # verifies a series of pre-conditions on the socket so
        # that it's ensured to be in a valid state before it's
        # set as a new connection for the server (validation)
        if self.ssl and not socket_c._sslobj: socket_c.close(); return

        # in case the SSL mode is enabled, "patches" the socket
        # object with an extra pending reference, that is going
        # to be to store pending callable operations in it
        if self.ssl: socket_c.pending = None

        # verifies if the socket is of type internet (either ipv4
        # of ipv6), this is going to be used for conditional setting
        # of some of the socket options
        is_inet = socket_c.family in (socket.AF_INET, socket.AF_INET6)

        # sets the socket as non blocking and then updated a series
        # of options in it, some of them taking into account if the
        # socket if of type internet (timeout values)
        socket_c.setblocking(0)
        socket_c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if is_inet: socket_c.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
        if self.receive_buffer_c: socket_c.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            self.receive_buffer_c
        )
        if self.send_buffer_c: socket_c.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            self.send_buffer_c
        )

        # the process creation is considered completed and a new
        # connection is created for it and opened, from this time
        # on a new connection is considered accepted/created for server
        connection = self.owner.build_connection(socket_c, address, ssl = self.ssl)
        connection.open()

        # registers the SSL handshake method as a starter method
        # for the connection, so that the handshake is properly
        # performed on the initial stage of the connection (as expected)
        if self.ssl: connection.add_starter(self._ssl_handshake)

        # runs the initial try for the handshaking process, note that
        # this is an async process and further tries to the handshake
        # may come after this one (async operation) in case an exception
        # is raises the connection is closed (avoids possible errors)
        try: connection.run_starter()
        except Exception: connection.close(); raise

        # in case there's extraneous data pending to be read from the
        # current connection's internal receive buffer it must be properly
        # handled on the risk of blocking the newly created connection
        if connection.is_pending_data(): self.on_read(connection.socket)

        # returns the connection that has been build already properly
        # initialized and ready to be used
        return connection
