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

import uuid
import base64
import hashlib

import netius.common

class WSProtocol(netius.StreamProtocol):
    """
    Abstract WebSockets protocol to be used for real-time bidirectional
    communication on top of the HTTP protocol.

    :see: https://tools.ietf.org/html/rfc6455
    """

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    @classmethod
    def _key(cls, size = 16):
        seed = str(uuid.uuid4())
        seed = netius.legacy.bytes(seed)[:size]
        seed = base64.b64encode(seed)
        return netius.legacy.str(seed)

    def __init__(self, *args, **kwargs):
        netius.StreamProtocol.__init__(self, *args, **kwargs)
        self.host = None
        self.port = None
        self.ssl = False
        self.path = None
        self.key = None
        self.version = None
        self.code = None
        self.code_s = None
        self.handshake = False
        self.buffer_l = []
        self.headers = {}

    def connection_made(self, transport):
        netius.StreamProtocol.connection_made(self, transport)
        data = "GET %s HTTP/1.1\r\n" % self.path +\
            "Upgrade: websocket\r\n" +\
            "Connection: Upgrade\r\n" +\
            "Host: %s\r\n" % self.host +\
            "Origin: http://%s\r\n" % self.host +\
            "Sec-WebSocket-Key: %s\r\n" % self.key +\
            "Sec-WebSocket-Version: 13\r\n\r\n"
        self.send(data)

    def on_data(self, data):
        netius.StreamProtocol.on_data(self, data)

        # iterates while there's still data pending to be parsed from the
        # current message received using the HTTP or WS protocols
        while data:
            if self.handshake:
                # retrieves the current (pending) buffer of data for the
                # protocol and tries to run the decoder of websockets
                # frame on the complete set of data pending in case there's
                # a problem the (pending) data is added to the buffer
                buffer = self.get_buffer()
                data = buffer + data
                try: decoded, data = netius.common.decode_ws(data)
                except netius.DataError: self.add_buffer(data); break

                # calls the callback method in the protocol notifying
                # it about the new (decoded) data that has been received
                self.receive_ws(decoded)

                # calls the proper callback handler for the data
                # that has been received with the decoded data
                self.on_data_ws(decoded)

            else:
                # adds the current data to the internal protocol
                # buffer to be processed latter, by the handshake
                self.add_buffer(data)

                # tries to run the handshake operation for the
                # current protocol in case it fails due to an
                # handshake error must delay the execution to the
                # next iteration (not enough data)
                try: self.do_handshake()
                except netius.DataError: return

                # validates (and computes) the accept key value according
                # to the provided value, in case there's an error an exception
                # should be raised (finishing the protocol)
                self.validate_key()

                # calls the on handshake event handler for the current
                # protocol to notify the current object
                self.on_handshake()

                # retrieves the current buffer value as the data that is still
                # pending to be parsed from the current protocol, this is
                # required so that the complete client buffer is flushed
                data = self.get_buffer()

    def on_data_ws(self, data):
        self.trigger("message", self, data)

    def on_handshake(self):
        self.trigger("handshake", self)

    def connect_ws(self, url, callback = None, loop = None):
        cls = self.__class__

        parsed = netius.legacy.urlparse(url)
        self.ssl = parsed.scheme == "wss"
        self.host = parsed.hostname
        self.port = parsed.port or (self.ssl and 443 or 80)
        self.path = parsed.path or "/"

        loop = netius.connect_stream(
            lambda: self,
            host = self.host,
            port = self.port,
            ssl = self.ssl,
            loop = loop
        )

        self.key = cls._key()

        if callback: self.bind("handshake", callback, oneshot = True)

        return loop, self

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

        value = netius.legacy.bytes(self.key + WSProtocol.MAGIC_VALUE)
        hash = hashlib.sha1(value)
        hash_digest = hash.digest()
        _accept_key = base64.b64encode(hash_digest)
        _accept_key = netius.legacy.str(_accept_key)

        if not _accept_key == accept_key:
            raise netius.SecurityError("Invalid accept key provided")

class WSClient(netius.ClientAgent):

    protocol = WSProtocol

    @classmethod
    def connect_ws_s(cls, url, callback = None, loop = None):
        protocol = cls.protocol()
        return protocol.connect_ws(url, callback = callback, loop = loop)

if __name__ == "__main__":
    def on_handshake(protocol):
        protocol.send_ws("Hello World")

    def on_message(protocol, data):
        print(data)
        protocol.close()

    def on_close(protocol):
        netius.compat_loop(loop).stop()

    url = netius.conf("WS_URL", "ws://echo.websocket.org/")

    loop, protocol = WSClient.connect_ws_s(url)

    protocol.bind("handshake", on_handshake)
    protocol.bind("message", on_message)
    protocol.bind("close", on_close)

    loop.run_forever()
    loop.close()
else:
    __path__ = []
