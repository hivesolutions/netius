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

import base64
import hashlib

import netius.common

class WSConnection(netius.Connection):
    """
    Connection based class for the websockets connection,
    should be able to implement the required encoding
    and decoding techniques in compliance with the websockets
    level 13 specification.

    :see: http://tools.ietf.org/html/rfc6455
    """

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.handshake = False
        self.method = None
        self.path = None
        self.version = None
        self.buffer_l = []
        self.headers = {}

    def send_ws(self, data):
        encoded = netius.common.encode_ws(data, mask = False)
        return self.send(encoded)

    def recv_ws(self, size = netius.CHUNK_SIZE):
        data = self.recv(size = size)
        decoded = netius.common.decode_ws(data)
        return decoded

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
        self.method, self.path, self.version = first.split(" ", 2)

        del self.buffer_l[:]
        self.handshake = True

        if remaining: self.add_buffer(remaining)

    def accept_key(self):
        socket_key = self.headers.get("Sec-WebSocket-Key", None)
        if not socket_key:
            raise netius.NetiusError("No socket key found in headers")

        value = netius.legacy.bytes(socket_key + WSServer.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        accept_key = base64.b64encode(hash_digest)
        accept_key = netius.legacy.str(accept_key)
        return accept_key

class WSServer(netius.StreamServer):
    """
    Base class for the creation of websocket server, should
    handle both the upgrading/handshaking of the connection
    and together with the associated connection class the
    encoding and decoding of the frames.
    """

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)

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

                # retrieves (and computes) the accept key value for
                # the current request and sends it as the handshake
                # response to the client side
                accept_key = connection.accept_key()
                response = self._handshake_response(accept_key)
                connection.send(response)

                # calls the on handshake event handler for the current
                # connection to notify the current object
                self.on_handshake(connection)

                # retrieves the current buffer value as the data that is still
                # pending to be parsed from the current connection, this is
                # required so that the complete client buffer is flushed
                data = connection.get_buffer()

    def new_connection(self, socket, address, ssl = False):
        return WSConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def send_ws(self, connection, data):
        encoded = netius.common.encode_ws(data, mask = False)
        return connection.send(encoded)

    def on_data_ws(self, connection, data):
        pass

    def on_handshake(self, connection):
        pass

    def _handshake_response(self, accept_key):
        """
        Returns the response contents of the handshake operation for
        the provided accept key.

        The key value should already be calculated according to the
        specification.

        :type accept_key: String
        :param accept_key: The accept key to be used in the creation
        of the response message.
        :rtype: String
        :return: The response message contents generated according to
        the specification and the provided accept key.
        """

        data = "HTTP/1.1 101 Switching Protocols\r\n" +\
            "Upgrade: websocket\r\n" +\
            "Connection: Upgrade\r\n" +\
            "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key
        return data
