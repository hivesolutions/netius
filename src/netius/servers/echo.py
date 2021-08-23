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

import os

import netius

class EchoProtocol(netius.StreamProtocol):

    def __init__(self, owner = None):
        netius.StreamProtocol.__init__(self, owner = owner)

        self.host = "0.0.0.0"
        self.port = 90
        self.ssl = False

    def on_data(self, data):
        netius.StreamProtocol.on_data(self, data)
        self.send(data)

    def serve(self, env = False, loop = None):
        loop = netius.serve_stream(
            lambda: self,
            host = self.host,
            port = self.port,
            ssl = self.ssl,
            loop = loop
        )
        return loop, self

class EchoServer(netius.ServerAgent):

    protocol = EchoProtocol

    @classmethod
    def serve_s(cls, env = False, loop = None):
        protocol = cls.protocol()
        return protocol.serve(env = env, loop = loop)

async def main_asyncio():
    # retrieves a reference to the event loop as we plan to use
    # low-level APIs, this should return the default event loop
    import asyncio
    loop = asyncio.get_running_loop()
    server = await loop.create_server(lambda: EchoProtocol(), "127.0.0.1", 8888)
    async with server:
        await server.serve_forever()

def run_native():
    loop, _protocol = EchoServer.serve_s()
    loop.run_forever()
    loop.close()

def run_asyncio():
    netius.run(main_asyncio())

if __name__ == "__main__":
    if os.environ.get("ASYNCIO", "0") == "1" or\
        os.environ.get("COMPAT", "0") == "1":
        run_asyncio()
    else:
        run_native()
else:
    __path__ = []
