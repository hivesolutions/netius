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

from .base import Middleware

class ProxyMiddleware(Middleware):
    """
    Middleware that implements the PROXY protocol on creation
    of a new connection enabling the passing of information
    from the front-end server to a back-end server using a normal
    TCP connection. This protocol has been development originally
    for the integration of an HAProxy server with back-end servers.

    :see: http://www.haproxy.org/download/1.5/doc/proxy-protocol.txt
    """

    MAX_LENGTH = 118
    """ The maximum length that the base packet may have,
    this is a constant according to proxy send """

    def start(self):
        Middleware.start(self)
        self.owner.bind("connection_c", self.on_connection_c)

    def stop(self):
        Middleware.stop(self)
        self.owner.unbind("connection_c", self.on_connection_c)

    def on_connection_c(self, owner, connection):
        connection.add_starter(self._proxy_handshake)

    def _proxy_handshake(self, connection):
        cls = self.__class__

        # verifies if the connection is ssl based if that's the case
        # the safe (reading) mode is enabled
        safe = connection.ssl

        # selects the proper receive method to be used to retrieve bytes
        # from the client side taking into account if the connection is
        # secured with ssl or not, note that the "special" ssl receive method
        # allows one to receive raw information under an ssl socket/connection
        recv = connection._recv_ssl if connection.ssl else connection.recv

        # in case the safe (read) mode is enabled the unit of counting
        # for the receive operation is one (single byte reading) to
        # allow no return of data (required for some environment eg: ssl)
        count = 1 if safe else cls.MAX_LENGTH

        # verifies if there's a previously set proxy buffer defined
        # for the connection and if that's the case uses it otherwise
        # starts a new empty buffer from scratch
        has_buffer = hasattr(connection, "_proxy_buffer")
        if has_buffer: buffer = connection._proxy_buffer
        else: buffer = bytearray()

        # iterates continuously trying to retrieve the set of data that is
        # required to parse the PROXy protocol header information
        while True:
            # tries to receive the maximum size of data that is required
            # for the handling of the PROXY information
            data = self.owner.exec_safe(connection, recv, count)

            # in case the received data represents that of a closed connection
            # the connection is closed and the control flow returned
            if data == b"": connection.close(); return

            # in case the received value is false, that indicates that the
            # execution has failed due to an exception (expected or unexpected)
            if data == False: return

            # updates the "initial" buffer length taking into account
            # the current buffer and then appends the new data to it
            buffer_l = len(buffer)
            buffer += data

            # saves the "newly" created buffer as the proxy buffer for the
            # current connection (may be used latter)
            connection._proxy_buffer = buffer

            # verifies the end of line sequence is present in the buffer,
            # if that's the case we've reached a positive state
            is_ready = b"\r\n" in buffer

            # in case the ready state has been reached, the complete set of
            # data is ready to be parsed and the loop is stopped
            if is_ready: break

        # removes the proxy buffer reference from the connection as
        # its no longer going to be used
        del connection._proxy_buffer

        # determines the index/position of the end sequence in the
        # buffer and then uses it to calculate the base for the
        # calculus of the extra information in the data buffer
        buffer_i = buffer.index(b"\r\n")
        data_b = buffer_i - buffer_l + 2

        # extracts the line for parsing and the extra data value (to
        # be restored to connection) using the data base and the data
        line = buffer[:buffer_i]
        extra = data[data_b:]

        # in case there's valid extra data to be restored to the connection
        # performs the operation, effectively restoring it for receiving
        if extra: connection.restore(extra)

        # forces the "conversion" of the line into a string so that it may
        # be properly split into its components, note that first the value
        # is converted into a byte string and then into a proper string
        line = bytes(line)
        line = netius.legacy.str(line)

        # splits the line of the protocol around its components and uses them
        # to change the current connection information (as expected)
        header, protocol, source, destination, source_p, destination_p = line.split(" ")

        # prints a debug message about the proxy header received, so that runtime
        # debugging is possible (and expected for this is a sensible part)
        self.owner.debug(
            "Received header %s %s %s:%s => %s:%s" %
            (header, protocol, source, source_p, destination, destination_p)
        )

        # re-constructs the source address from the provided information, this is
        # the major and most important fix to be done
        connection.address = (source, int(source_p))

        # runs the end starter operation, indicating to the connection that
        # the proxy header has been properly parsed
        connection.end_starter()
