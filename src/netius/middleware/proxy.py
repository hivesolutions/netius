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

    MAX_LENGTH = 108
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

        # tries to receive the maximum size of data that is required
        # for the handling of the PROXY information, note that in case
        # the received value is false, that indicates that the execution
        # has failed due to an exception (expected or unexpected)
        data = self.owner.exec_safe(connection, connection.recv, cls.MAX_LENGTH)
        if data == False: return

        # tries to determine if a proxy buffer already exist for the
        # connection and if that's the case sets it as the initial
        # buffer value adding then the "received" data to it
        has_buffer = hasattr(connection, "_proxy_buffer")
        if has_buffer: buffer = connection._proxy_buffer
        else: buffer = b""
        buffer_l = len(buffer)
        buffer += data

        # saves the "newly" created buffer as the proxy buffer for the
        # current connection (may be used latter)
        connection._proxy_buffer = buffer

        # verifies the end of line sequence is present in the buffer,
        # if that's the case we've reached a positive state
        is_ready = b"\r\n" in buffer

        # in case no ready state has been reached, the buffer value
        # is saved for latter usage (as expected)
        if not is_ready: return

        # removes the proxy buffer reference from the connection as
        # its no longer going to be used
        del connection._proxy_buffer

        # determines the index/position of the end sequence in the
        # buffer and then "translates" it into the data index
        buffer_i = buffer.index(b"\r\n")
        data_i = buffer_i - buffer_l

        # extracts the line for parsing and the extra data value (to
        # be restored to connection) using the data index and the data
        line = data[:data_i]
        extra = data[data_i + 2:]

        # in case there's valid extra data to be restored to the connection
        # performs the operation, effectively restoring it for receiving
        if extra: connection.restore(extra)

        # forces the "conversion" of the line into a string so that it may
        # be properly split into its components
        line = netius.legacy.str(line)

        # splits the line of the protocol around its components and uses them
        # to change the current connection information (as expected)
        header, protocol, source, destination, source_p, destination_p = line.split(" ")

        # prints a debug message about the proxy header received, so that runtime
        # debugging is possible (and expected)
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
