#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius


class EchoProtocol(netius.StreamProtocol):

    def on_data(self, data):
        netius.StreamProtocol.on_data(self, data)
        self.send(data)

    def serve(self, host="127.0.0.1", port=8888, ssl=False, env=False, loop=None):
        loop = netius.serve_stream(
            lambda: self, host=host, port=port, ssl=ssl, loop=loop, env=env
        )
        return loop, self


class EchoServer(netius.ServerAgent):

    protocol = EchoProtocol

    @classmethod
    def serve_s(cls, **kwargs):
        protocol = cls.protocol()
        return protocol.serve(**kwargs)


if __name__ == "__main__":
    loop, _protocol = EchoServer.serve_s()
    loop.run_forever()
    loop.close()
else:
    __path__ = []
