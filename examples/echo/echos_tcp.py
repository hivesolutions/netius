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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius

import asyncio


class EchoServerClientProtocol(asyncio.Protocol):
    """
    Simple protocol implementation for an echo protocol
    that writes back the received message through the
    response pipeline. This implementation is inspired by
    the Python asyncio documentation example.

    :see: https://docs.python.org/3.6/library/asyncio-protocol.html#protocol-examples
    """

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        print("Connection from %s" % str(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print("Data received: %s" % message)

        print("Sending: %s" % message)
        self.transport.write(data)

        print("Closing the client socket")
        self.transport.close()


loop = netius.get_loop(_compat=True)

coro = loop.create_server(lambda: EchoServerClientProtocol(), "127.0.0.1", 8888)
server = loop.run_until_complete(coro)

print("Serving on %s" % (server.sockets[0].getsockname(),))

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
