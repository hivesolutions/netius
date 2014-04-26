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

import base64
import hashlib

import netius

class WSConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.handshake = False
        self.method = None
        self.path = None
        self.version = None
        self.buffer_l = []
        self.headers = {}

    def send_ws(self, data):
        encoded = self._encode(data)
        return self.send(encoded)

    def recv_ws(self, size = netius.CHUNK_SIZE):
        data = self.recv(size = size)
        decoded = self._decode(data)
        return decoded

    def add_buffer(self, data):
        self.buffer_l.append(data)

    def do_handshake(self):
        if self.handshake:
            raise netius.NetiusError("Handshake already done")

        buffer = b"".join(self.buffer_l)
        if not buffer[-4:] == b"\r\n\r\n":
            raise netius.DataError("Missing data for handshake")

        lines = buffer.split(b"\r\n")
        for line in lines[1:]:
            values = line.split(b":")
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
        self.method, self.path, self.version = first.split(" ")

        del self.buffer_l[:]
        self.handshake = True

    def accept_key(self):
        socket_key = self.headers.get("Sec-WebSocket-Key", None)
        if not socket_key:
            raise netius.NetiusError("No socket key found in headers")

        value = netius.bytes(socket_key + WSServer.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        accept_key = base64.b64encode(hash_digest)
        accept_key = netius.str(accept_key)
        return accept_key

    def get_buffer(self, delete = True):
        if not self.buffer_l: return b""
        buffer = b"".join(self.buffer_l)
        if delete: del self.buffer_l[:]
        return buffer

    def _encode(self, data):
        data = netius.bytes(data)
        data_l = len(data)

        encoded_l = list()
        encoded_l.append(netius.chr(129))

        if data_l <= 125:
            encoded_l.append(netius.chr(data_l))

        elif data_l >= 126 and data_l <= 65535:
            encoded_l.append(netius.chr(126))
            encoded_l.append(netius.chr((data_l >> 8) & 255))
            encoded_l.append(netius.chr(data_l & 255))

        else:
            encoded_l.append(netius.chr(127))
            encoded_l.append(netius.chr((data_l >> 56) & 255))
            encoded_l.append(netius.chr((data_l >> 48) & 255))
            encoded_l.append(netius.chr((data_l >> 40) & 255))
            encoded_l.append(netius.chr((data_l >> 32) & 255))
            encoded_l.append(netius.chr((data_l >> 24) & 255))
            encoded_l.append(netius.chr((data_l >> 16) & 255))
            encoded_l.append(netius.chr((data_l >> 8) & 255))
            encoded_l.append(netius.chr(data_l & 255))

        encoded_l.append(data)
        encoded = b"".join(encoded_l)
        return encoded

    def _decode(self, data):
        second_byte = data[1]

        length = netius.ord(second_byte) & 127

        index_mask_f = 2

        if length == 126:
            length = 0
            length += netius.ord(data[2]) << 8
            length += netius.ord(data[3])
            index_mask_f = 4

        elif length == 127:
            length = 0
            length += netius.ord(data[2]) << 56
            length += netius.ord(data[3]) << 48
            length += netius.ord(data[4]) << 40
            length += netius.ord(data[5]) << 32
            length += netius.ord(data[6]) << 24
            length += netius.ord(data[7]) << 16
            length += netius.ord(data[8]) << 8
            length += netius.ord(data[9])
            index_mask_f = 10

        # calculates the size of the raw data part of the message and
        # in case its smaller than the defined length of the data returns
        # immediately indicating that there's not enough data to complete
        # the decoding of the data (should be re-trying again latter)
        raw_size = len(data) - index_mask_f - 4
        if raw_size < length:
            raise netius.DataError("Not enough data available for parsing")

        # retrieves the masks part of the data that are going to be
        # used in the decoding part of the process
        masks = data[index_mask_f:index_mask_f + 4]

        # allocates the array that is going to be used
        # for the decoding of the data with the length
        # that was computed as the data length
        decoded_a = bytearray(length)

        # starts the initial data index and then iterates over the
        # range of decoded length applying the mask to the data
        # (decoding it consequently) to the created decoded array
        i = index_mask_f + 4
        for j in range(length):
            decoded_a[j] = netius.chri(netius.ord(data[i]) ^ netius.ord(masks[j % 4]))
            i += 1

        # converts the decoded array of data into a string and
        # and returns the "partial" string containing the data that
        # remained pending to be parsed
        decoded = bytes(decoded_a)
        return decoded, data[i:]

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

        if connection.handshake:
            while data:
                buffer = connection.get_buffer()
                try: decoded, data = connection._decode(buffer + data)
                except: connection.add_buffer(data); break
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

    def new_connection(self, socket, address, ssl = False):
        return WSConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def send_ws(self, connection, data):
        encoded = self._encode(data)
        connection.send(encoded)

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

        @type accept_key: String
        @param accept_key: The accept key to be used in the creation
        of the response message.
        @rtype: String
        @return: The response message contents generated according to
        the specification and the provided accept key.
        """

        data = "HTTP/1.1 101 Switching Protocols\r\n" +\
            "Upgrade: websocket\r\n" +\
            "Connection: Upgrade\r\n" +\
            "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key
        return data
