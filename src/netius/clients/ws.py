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

    def send_ws(self, data, callback = None):
        encoded = netius.common.encode_ws(data, mask = True)
        return self.send(encoded, callback = callback)

    def receive_ws(self, decoded):
        pass

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
        end_index = buffer.find(b"\r\n\r\n")
        if end_index == -1: raise netius.DataError("Missing data for handshake")

        data = buffer[:end_index + 4]
        remaining = buffer[end_index + 4:]

        lines = data.split(b"\r\n")
        for line in lines[1:]:
            values = line.split(b":", 1)
            values_l = len(values)
            if not values_l == 2: continue

            key, value = values
            key = key.strip()
            key = netius.legacy.str(key)
            value = value.strip()
            value = netius.legacy.str(value)
            self.headers[key] = value

        first = lines[0]
        first = netius.legacy.str(first)
        self.version, self.code, self.code_s = first.split(" ", 2)

        del self.buffer_l[:]
        self.handshake = True

        if remaining: self.add_buffer(remaining)

    def validate_key(self):
        accept_key = self.headers.get("Sec-WebSocket-Accept", None)
        if not accept_key:
            raise netius.NetiusError("No accept key found in headers")

        value = netius.legacy.bytes(self.key + WSClient.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        _accept_key = base64.b64encode(hash_digest)
        _accept_key = netius.legacy.str(_accept_key)

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

        # iterates while there's still data pending to be parsed from the
        # current message received using the http or ws protocols
        while data:
            if connection.handshake:
                # retrieves the current (pending) buffer of data for the
                # connection and tries to run the decoder of websockets
                # frame on the complete set of data pending in case there's
                # a problem the (pending) data is added to the buffer
                buffer = connection.get_buffer()
                data = buffer + data
                try: decoded, data = netius.common.decode_ws(data)
                except netius.DataError: connection.add_buffer(data); break

                # calls the callback method in the connection notifying
                # it about the new (decoded) data that has been received
                connection.receive_ws(decoded)

                # calls the proper callback handler for the data
                # that has been received with the decoded data
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

                # retrieves the current buffer value as the data that is still
                # pending to be parsed from the current connection, this is
                # required so that the complete client buffer is flushed
                data = connection.get_buffer()

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
        parsed = netius.legacy.urlparse(url)
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
        seed = netius.legacy.bytes(seed)[:size]
        seed = base64.b64encode(seed)
        return netius.legacy.str(seed)

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
