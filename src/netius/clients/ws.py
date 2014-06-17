#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import uuid
import base64

import netius

class WSClient(netius.StreamClient):

    def __init__(self, *args, **kwargs):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.key = self._key()

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)
        data = "GET %s HTTP/1.1\r\n" % connection.path +\
            "Host: %s\r\n" % connection.address[0] +\
            "Connection: Upgrade\r\n" +\
            "Sec-WebSocket-Key: %s\r\n" % self.key +\
            "Sec-WebSocket-Protocol: any\r\n" +\
            "Sec-WebSocket-Version: 13\r\n\r\n"
        connection.send(data)

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        print(data)

    def connect_ws(self, url):
        parsed = netius.urlparse(url)
        ssl = parsed.scheme == "wss"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path
        connection = self.connect(host, port, ssl = ssl)
        connection.path = path

    def send_ws(self, data):
        pass

    def _key(self):
        seed = str(uuid.uuid4())
        return base64.b64encode(seed)

if __name__ == "__main__":
    def on_connect(client):
        client.send_ws("Hello World")

    def on_message(client, data):
        client.close()

    def on_close(client, connection):
        client.close()

    http_client = WSClient()
    http_client.connect_ws("ws://localhost:9090/")
    http_client.bind("connect", on_connect)
    http_client.bind("message", on_message)
    http_client.bind("close", on_close)
