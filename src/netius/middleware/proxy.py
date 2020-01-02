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

import struct

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
    this is a constant according to PROXY send """

    HEADER_LENGTH_V2 = 16
    """ The length of the header message of the PROXY protocol
    under version 2 """

    HEADER_MAGIC_V2 = b"\x0d\x0a\x0d\x0a\x00\x0d\x0a\x51\x55\x49\x54\x0a"
    """ The magic byte string that starts the PROXY v2 protocol
    header, should be used for runtime verifications """

    TYPE_LOCAL_V2 = 0x0
    TYPE_PROXY_V2 = 0x1

    AF_UNSPEC_v2 = 0x0
    AF_INET_v2 = 0x1
    AF_INET6_v2 = 0x2
    AF_UNIX_v2 = 0x3

    PROTO_UNSPEC_v2 = 0x0
    PROTO_STREAM_v2 = 0x1
    PROTO_DGRAM_v2 = 0x2

    def __init__(self, owner, version = 1):
        Middleware.__init__(self, owner)
        self.version = version

    def start(self):
        Middleware.start(self)
        self.version = netius.conf("PROXY_VERSION", self.version, cast = int)
        self.owner.bind("connection_c", self.on_connection_c)

    def stop(self):
        Middleware.stop(self)
        self.owner.unbind("connection_c", self.on_connection_c)

    def on_connection_c(self, owner, connection):
        if self.version == 1: connection.add_starter(self._proxy_handshake_v1)
        elif self.version == 2: connection.add_starter(self._proxy_handshake_v2)
        else: raise netius.RuntimeError("Invalid PROXY version")

    def _proxy_handshake_v1(self, connection):
        cls = self.__class__

        # verifies if the connection is SSL based if that's the case
        # the safe (reading) mode is enabled
        safe = connection.ssl

        # selects the proper receive method to be used to retrieve bytes
        # from the client side taking into account if the connection is
        # secured with SSL or not, note that the "special" SSL receive method
        # allows one to receive raw information under an SSL socket/connection
        recv = connection._recv_ssl if connection.ssl else connection.recv

        # in case the safe (read) mode is enabled the unit of counting
        # for the receive operation is one (single byte reading) to
        # allow no return of data (required for some environment eg: SSL)
        count = 1 if safe else cls.MAX_LENGTH

        # verifies if there's a previously set PROXY buffer defined
        # for the connection and if that's the case uses it otherwise
        # starts a new empty buffer from scratch
        has_buffer = hasattr(connection, "_proxy_buffer")
        if has_buffer: buffer = connection._proxy_buffer
        else: buffer = bytearray()

        # saves the "newly" created buffer as the PROXY buffer for the
        # current connection (may be used latter)
        connection._proxy_buffer = buffer

        # iterates continuously trying to retrieve the set of data that is
        # required to parse the PROXY protocol header information
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

            # verifies the end of line sequence is present in the buffer,
            # if that's the case we've reached a positive state
            is_ready = b"\r\n" in buffer

            # in case the ready state has been reached, the complete set of
            # data is ready to be parsed and the loop is stopped
            if is_ready: break

        # removes the PROXY buffer reference from the connection as
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
        # performs the operation, effectively restoring it for latter
        # receiving operations (just like adding it back to the socket)
        if extra: connection.restore(extra)

        # forces the "conversion" of the line into a string so that it may
        # be properly split into its components, note that first the value
        # is converted into a byte string and then into a proper string
        line = bytes(line)
        line = netius.legacy.str(line)

        # splits the line of the protocol around its components and uses them
        # to change the current connection information (as expected)
        header, protocol, source, destination, source_p, destination_p = line.split(" ")

        # prints a debug message about the PROXY header received, so that runtime
        # debugging is possible (and expected for this is a sensible part)
        self.owner.debug(
            "Received header %s %s %s:%s => %s:%s" %
            (header, protocol, source, source_p, destination, destination_p)
        )

        # re-constructs the source address from the provided information, this is
        # the major and most important fix to be done
        connection.address = (source, int(source_p))

        # runs the end starter operation, indicating to the connection that
        # the PROXY header has been properly parsed
        connection.end_starter()

    def _proxy_handshake_v2(self, connection):
        import netius.common

        cls = self.__class__

        # verifies if there's a previously set PROXY buffer defined
        # for the connection and if that's the case uses it otherwise
        # starts a new empty buffer from scratch
        has_buffer = hasattr(connection, "_proxy_buffer")
        if has_buffer: buffer = connection._proxy_buffer
        else: buffer = bytearray()

        # saves the "newly" created buffer as the PROXY buffer for the
        # current connection (may be used latter)
        connection._proxy_buffer = buffer

        # verifies if a PROXY header was already parsed from the current connection
        # and if that was not the case runs its parsing
        header = connection._proxy_header if hasattr(connection, "_proxy_header") else None
        if not header:
            # tries to read the PROXY v2 header bytes to be able to parse
            # the body parts taking that into account
            header = self._read_safe(connection, buffer, cls.HEADER_LENGTH_V2)
            if not header: return

            # updates the reference to the proxy header in the connection
            # and clears the buffer as it's now going to be used to load
            # the data from the body part
            connection._proxy_header = header
            buffer[:] = b""

        # unpacks the PROXY v2 header into its components, notice that some of them
        # contain multiple values on higher and lower bits
        magic, version_type, address_protocol, body_size = struct.unpack("!12sBBH", header)

        # unpacks both the version (of the protocol) and the type (of message) by
        # unpacking the higher and the lower bits
        version = version_type >> 4
        type = version_type & 0x0f

        # unpacks the type of address to be communicated and the protocol family
        address = address_protocol >> 4
        protocol = address_protocol & 0x0f

        # runs a series of assertions on some of the basic promises of the protocol
        # (if they failed connection will be dropped)
        netius.verify(magic == cls.HEADER_MAGIC_V2)
        netius.verify(version == 2)

        # reads the body part of the PROXY message taking into account the advertised
        # size of the body (from header component)
        body = self._read_safe(connection, buffer, body_size)
        if not body: return

        if address == cls.AF_INET_v2:
            source, destination, source_p, destination_p = struct.unpack("!IIHH", body)
            source = netius.common.addr_to_ip4(source)
            destination = netius.common.addr_to_ip4(destination)
        elif address == cls.AF_INET6_v2:
            source_high,\
            source_low,\
            destination_high,\
            destination_low,\
            source_p,\
            destination_p = struct.unpack("!QQQQHH", body)
            source = (source_high << 64) + source_low
            destination = (destination_high << 64) + destination_low
            source = netius.common.addr_to_ip6(source)
            destination = netius.common.addr_to_ip6(destination)
        else:
            raise netius.RuntimeError("Unsupported or invalid PROXY header")

        # removes the PROXY buffer and header references from the connection
        # as they are no longer going to be used
        del connection._proxy_buffer
        del connection._proxy_header

        # prints a debug message about the PROXY header received, so that runtime
        # debugging is possible (and expected for this is a sensible part)
        self.owner.debug(
            "Received header v2 %d %s:%s => %s:%s" %
            (protocol, source, source_p, destination, destination_p)
        )

        # re-constructs the source address from the provided information, this is
        # the major and most important fix to be done
        connection.address = (source, int(source_p))

        # runs the end starter operation, indicating to the connection that
        # the PROXY header has been properly parsed
        connection.end_starter()

    def _read_safe(self, connection, buffer, count):
        """
        Reads a certain amount of data from a non blocking connection,
        in case the're a blocking operation then the error is raised
        and caught by the upper layers.

        This method also assumes that the buffer is stored on an abstract
        layer that can be used in the resume operation.

        :type connection: Connection
        :param connection: The connection from which the data is going
        to be read.
        :type buffer: bytearray
        :param bytearray: The byte array where the data is going to be store
        waiting for the processing.
        :type count: int
        :param count: The number of bytes that are going to be read from
        the target connection.
        :rtype: String
        :return: The bytes that were read from the connection or in alternative
        an invalid value meaning that the connection should be dropped.
        """

        cls = self.__class__

        # selects the proper receive method to be used to retrieve bytes
        # from the client side taking into account if the connection is
        # secured with SSL or not, note that the "special" SSL receive method
        # allows one to receive raw information under an SSL socket/connection
        recv = connection._recv_ssl if connection.ssl else connection.recv

        # iterates continuously trying to retrieve the set of data that is
        # required to parse the PROXY protocol header information
        while True:
            # determines the number of pending bytes in remaining to be read
            # in the buffer and if that's less or equal to zero breaks the
            # current loop (nothing pending to be read)
            pending = count - len(buffer)
            if pending <= 0: break

            # tries to receive the maximum size of data that is required
            # for the handling of the PROXY information
            data = self.owner.exec_safe(connection, recv, pending)

            # in case the received data represents that of a closed connection
            # the connection is closed and the control flow returned
            if data == b"": connection.close(); return None

            # in case the received value is false, that indicates that the
            # execution has failed due to an exception (expected or unexpected)
            if data == False: return None

            # adds the newly read data to the current buffer
            buffer += data

        # returns the valid partial value of the buffer as requested by
        # the call to this method, in normal circumstances the buffer
        # should only contain the requested amount of data
        return bytes(buffer[:count])
