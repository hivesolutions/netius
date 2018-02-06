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

import netius

import asyncio

class EchoServerClientProtocol(asyncio.Protocol):

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        print("Connection from %s" % peername)
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print("Data received: %s" % message)

        print("Send: %s" % message)
        self.transport.write(data)

        print("Close the client socket")
        self.transport.close()

loop = netius.get_loop(_compat = True)

coro = loop.create_server(EchoServerClientProtocol, "127.0.0.1", 8888)
server = loop.run_until_complete(coro)

print("Serving on {}".format(server.sockets[0].getsockname()))

try: loop.run_forever()
except KeyboardInterrupt: pass

server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
