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

import netius

class RawProtocol(netius.StreamProtocol):

    def send_basic(self):
        """
        Sends a basic HTTP 1.0 request, that can be used to
        run a simple operation on the raw protocol.
        """

        self.send("GET / HTTP/1.0\r\n\r\n")

class RawClient(netius.ClientAgent):

    protocol = RawProtocol

    @classmethod
    def run_s(
        cls,
        host,
        port = 8080,
        loop = None,
        *args,
        **kwargs
    ):
        protocol = cls.protocol()

        loop = netius.connect_stream(
            lambda: protocol,
            host = host,
            port = port,
            loop = loop,
            *args,
            **kwargs
        )

        return loop, protocol

if __name__ == "__main__":

    def on_open(protocol):
        protocol.send_basic()

    def on_data(protocol, data):
        print(data)

    def on_finsh(protocol):
        netius.compat_loop(loop).stop()

    loop, protocol = RawClient.run_s("localhost")

    protocol.bind("open", on_open)
    protocol.bind("data", on_data)
    protocol.bind("finish", on_finsh)

    loop.run_forever()
    loop.close()

else:
    __path__ = []
