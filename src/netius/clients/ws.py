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
import hashlib

import netius.common

class WSConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.handshake = False
        self.path = None
        self.key = None
        self.version = None
        self.code = None
        self.code_s = None
        self.buffer_l = []
        self.headers = {}

    def send_ws(self, data):
        encoded = netius.common.encode_ws(data, mask = True)
        return self.send(encoded)

    def add_buffer(self, data):
        self.buffer_l.append(data)

    def get_buffer(self, delete = True):
        if not self.buffer_l: return b""
        buffer = b"".join(self.buffer_l)
        if delete: del self.buffer_l[:]
        return buffer

    def do_handshake(self):
        if self.handshake:
            raise netius.NetiusError("Handshake already done")

        buffer = b"".join(self.buffer_l)
        if not buffer[-4:] == b"\r\n\r\n":
            raise netius.DataError("Missing data for handshake")

        lines = buffer.split(b"\r\n")
        for line in lines[1:]:
            values = line.split(b":", 1)
            values_l = len(values)
            if not values_l == 2: continue

            key, value = values
            key = key.strip()
            key = netius.str(key)
            value = value.strip()
            value = netius.str(value)
            self.headers[key] = value

        first = lines[0]
        first = netius.str(first)
        self.version, self.code, self.code_s = first.split(" ", 2)

        del self.buffer_l[:]
        self.handshake = True

    def validate_key(self):
        accept_key = self.headers.get("Sec-WebSocket-Accept", None)
        if not accept_key:
            raise netius.NetiusError("No accept key found in headers")

        value = netius.bytes(self.key + WSClient.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        _accept_key = base64.b64encode(hash_digest)
        _accept_key = netius.str(_accept_key)

        if not _accept_key == accept_key:
            raise netius.SecurityError("Invalid accept key provided")

class WSClient(netius.StreamClient):

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)
        data = "GET %s HTTP/1.1\r\n" % connection.path +\
            "Upgrade: websocket\r\n" +\
            "Connection: Upgrade\r\n" +\
            "Host: %s\r\n" % connection.address[0] +\
            "Origin: http://%s\r\n" % connection.address[0] +\
            "Sec-WebSocket-Key: %s\r\n" % connection.key +\
            "Sec-WebSocket-Version: 13\r\n\r\n"
        connection.send(data)

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)

        if connection.handshake:
            while data:
                buffer = connection.get_buffer()
                try: decoded, data = netius.common.decode_ws(buffer + data)
                except netius.DataError: connection.add_buffer(data); break
                self.on_data_ws(connection, decoded)

        else:
            # adds the current data to the internal connection
            # buffer to be processed latter, by the handshake
            connection.add_buffer(data)

            # tries to run the handshake operation for the
            # current connection in case it fails due to an
            # handshake error must delay the execution to the
            # next iteration (not enough data)
            try: connection.do_handshake()
            except netius.DataError: return

            # validates (and computes) the accept key value according
            # to the provided value, in case there's an error an exception
            # should be raised (finishing the connection)
            connection.validate_key()

            # calls the on handshake event handler for the current
            # connection to notify the current object
            self.on_handshake(connection)

    def on_data_ws(self, connection, data):
        self.trigger("message", self, connection, data)

    def on_handshake(self, connection):
        self.trigger("handshake", self, connection)

    def new_connection(self, socket, address, ssl = False):
        return WSConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def connect_ws(self, url):
        parsed = netius.urlparse(url)
        ssl = parsed.scheme == "wss"
        host = parsed.hostname
        port = parsed.port or (ssl and 443 or 80)
        path = parsed.path or "/"
        connection = self.connect(host, port, ssl = ssl)
        connection.path = path
        connection.key = self._key()
        return connection

    def _key(self, size = 16):
        seed = str(uuid.uuid4())
        seed = netius.bytes(seed)[:size]
        seed = base64.b64encode(seed)
        return netius.str(seed)

if __name__ == "__main__":
    def on_handshake(client, connection):
        connection.send_ws("Hello World")

    def on_message(client, connection, data):
        print(data)
        client.close()

    def on_close(client, connection):
        client.close()

    client = WSClient()
    client.connect_ws("ws://echo.websocket.org/")
    client.bind("handshake", on_handshake)
    client.bind("message", on_message)
    client.bind("close", on_close)
