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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import uuid

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
        owner=None,
        transport=None,
        socket=None,
        host=None,
        port=None,
        ssl=False,
        receive_buffer_s=BUFFER_SIZE_S,
        send_buffer_s=BUFFER_SIZE_S,
        receive_buffer_c=BUFFER_SIZE_C,
        send_buffer_c=BUFFER_SIZE_C,
    ):
        observer.Observable.__init__(self)
        self.id = str(uuid.uuid4())
        self.owner = owner
        self.transport = transport
        self.socket = socket
        self.host = host
        self.port = port
        self.ssl = ssl
        self.receive_buffer_s = receive_buffer_s
        self.send_buffer_s = send_buffer_s
        self.receive_buffer_c = receive_buffer_c
        self.send_buffer_c = send_buffer_c

    def on_socket_c(self, socket_c, address):
        connection = self.owner.build_connection_client(
            socket_c,
            address,
            ssl=self.ssl,
            receive_buffer_c=self.receive_buffer_c,
            send_buffer_c=self.send_buffer_c,
        )
        self.transport = transport.TransportStream(self, connection)
        self.trigger("connection", connection)
