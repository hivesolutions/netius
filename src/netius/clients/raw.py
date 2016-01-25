#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius

class RawClient(netius.StreamClient):

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)
        self.trigger("connect", self, connection)

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        self.trigger("data", self, connection, data)

    def on_connection_d(self, connection):
        netius.StreamClient.on_connection_d(self, connection)
        self.trigger("close", self, connection)

if __name__ == "__main__":
    def on_connect(client, connection):
        connection.send("GET / HTTP/1.0\r\n\r\n")

    def on_data(client, connection, data):
        print(data)

    def on_close(client, connection):
        client.close()

    client = RawClient()
    client.connect("localhost", 8080)
    client.bind("connect", on_connect)
    client.bind("close", on_close)
    client.bind("data", on_data)
