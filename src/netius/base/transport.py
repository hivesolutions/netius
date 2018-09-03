#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

from . import errors
from . import observer

class Transport(observer.Observable):
    """
    Decorator class to be used to add the functionality of a
    transport layer using a simplified and standard API.

    Allows adding the functionality to an internal netius
    connection (or equivalent) object.

    This approach is heavily influenced by the design of the
    asyncio Python infra-structure and should provide a mostly
    compatible interface.
    """

    def __init__(self, loop, connection, open = True):
        self._loop = loop
        self._connection = connection
        self._protocol = None
        self._extra_dict = None
        self._exhausted = False
        if open: self.open()

    def open(self):
        self.set_handlers()
        self.set_write_buffer_limits()
        self.set_extra_dict()

    def close(self):
        # in case the current transport is already closed or in the
        # process of closing returns immediately (avoids duplication)
        if self.is_closing(): return

        if self._connection: self._connection.close(flush = True)
        else: self._protocol = None

        self._connection = None
        self._exhausted = False

    def abort(self):
        # in case the current transport is already closed or in the
        # process of closing returns immediately (avoids duplication)
        if self.is_closing(): return

        # in case there's a connection set runs the (forced) close
        # operation so that no more interaction exists otherwise
        # unsets the protocol (notice that if the connection exists
        # the close operation will trigger the close protocol callback)
        if self._connection: self._connection.close()
        else: self._protocol = None

        # unsets the connection object (as it's no longer eligible
        # to be used) and unsets the current transport for exhausted
        # as it's considered to be the default/initials state
        self._connection = None
        self._exhausted = False

    def write(self, data):
        # verifies if the current connection is closing or in the process
        # of closing and if that's the case raises an error
        if self.is_closing(): raise errors.RuntimeError("Connection is closed")

        # runs the send operation on the underlying (and concrete)
        # connection object, notice that the delay flag is unset so
        # that the send flushing operation runs immediately (to provide
        # behaviour level compatibility with the asyncio library)
        self._connection.send(data, delay = False)

    def sendto(self, data, addr = None):
        # verifies if the current connection is closing or in the process
        # of closing and if that's the case raises an error
        if self.is_closing(): raise errors.RuntimeError("Connection is closed")

        # runs the send operation on the underlying (and concrete)
        # connection object, notice that the delay flag is unset so
        # that the send flushing operation runs immediately (to provide
        # behaviour level compatibility with the asyncio library)
        self._connection.send(data, address = addr, delay = False)

    def get_extra_info(self, name, default = None):
        callable = self._extra_dict.get(name, None)
        if callable: return callable()
        else: return default

    def get_write_buffer_size(self):
        return self._connection.pending_s

    def get_write_buffer_limits(self):
        return (
            self._connection.min_pending,
            self._connection.max_pending
        )

    def set_handlers(self):
        self._connection.bind("pend", self._buffer_touched)
        self._connection.bind("unpend", self._buffer_touched)

    def set_write_buffer_limits(self, high = None, low = None):
        """
        Sets the write buffer limits in the underlying connection
        object using the provided values.

        If the only one of the values is provided the other one is
        going to be calculated using an hardcoded ratio value.

        :type high: int
        :param high: The maximum number of bytes that can be set
        waiting in the connection internal buffer waiting to be sent
        before the connection becomes exhausted (sending blocked).
        :type low: int
        :param low: The maximum number of bytes waiting in the buffer
        before the connection send buffer is unblocked.
        """

        if high is None:
            if low == None: high = 65536
            else: high = 4 * low
        if low == None: low = high // 4
        if not high >= low >= 0:
            raise errors.RuntimeError("High must be larger than low")

        self._connection.max_pending = high
        self._connection.min_pending = low

    def set_extra_dict(self):
        self._extra_dict = dict(
            socket = lambda: self._connection.socket,
            peername = lambda: self._connection.socket.getpeername(),
            sockname = lambda: self._connection.socket.getsockname(),
            compression = lambda: self._connection.socket.compression(),
            cipher = lambda: self._connection.socket.cipher(),
            peercert = lambda: self._connection.socket.getpeercert(),
            sslcontext = lambda: self._connection.socket.context,
            ssl_object = lambda: self._connection.socket
        )

    def get_protocol(self):
        return self._protocol

    def set_protocol(self, protocol):
        self._set_protocol(protocol, mark = False)

    def is_closing(self):
        """
        Determines if the current transport/connection is closed
        or is in the process of being closed.

        A transport is considered closed in case the underlying
        connection object is not set.

        :rtype: bool
        :return: If the current transport is closed or in the process
        of being closed.
        """

        if not self._connection: return True
        if self._connection.is_closed(): return True
        return False

    def _on_data(self, connection, data):
        pass

    def _on_close(self, connection):
        self._cleanup()

    def _set_compat(self, protocol):
        self._set_binds()
        self._set_protocol(protocol)

    def _set_binds(self):
        self._connection.bind("data", self._on_data)
        self._connection.bind("close", self._on_close)

    def _set_protocol(self, protocol, mark = True):
        self._protocol = protocol
        if mark: self._protocol.connection_made(self)

    def _buffer_touched(self, connection):
        self._handle_flow()

    def _handle_flow(self):
        if not self._connection: return

        if self._exhausted:
            is_restored = self._connection.is_restored()
            if not is_restored: return
            self._exhausted = False
            self._protocol.resume_writing()
        else:
            is_exhausted = self._connection.is_exhausted()
            if not is_exhausted: return
            self._exhausted = True
            self._protocol.pause_writing()

    def _cleanup(self):
        # schedules the connection lost calling on on the
        # next available tick so that the associated transport
        # gets notified about the closing of the connection
        self._call_soon(self._call_connection_lost, None)

        # unsets the loop from the current transport as it's
        # not safe to interact with the owner loop anymore
        self._loop = None

        # unsets the connection from the current instance and
        # normalizes the value of the exhausted flag
        self._connection = None
        self._exhausted = False

        # unset the currently set extra dictionary that defines
        # a series of lambda functions to the current instance
        self._extra_dict = None

        # runs the destroy operation that will clean the
        # most basic structures associated with this object
        self.destroy()

    def _call_connection_lost(self, context):
        # verifies if there's a protocol instance currently
        # set and if that's the case calls the connection
        # lost method indicating that the transport is now
        # closed (no connection available)
        if not self._protocol == None:
            self._protocol.connection_lost(context)

        # forces the unset of the protocol as the proper
        # connection lost operation has been called and
        # there's no more logical association between
        # the transport and the protocol
        self._protocol = None

    def _call_soon(self, callback, *args):
        if hasattr(self._loop, "call_soon"):
            self._loop.call_soon(callback, *args)
        else:
            callable = lambda: callback(*args)
            self._loop.delay(callable, immediately = True)

class TransportDatagram(Transport):
    """
    Abstract class to be used when creating a datagram based
    (connectionless) transport.

    This implementation reflects the decisions made for the
    netius based transport abstraction, inspired by asyncio.
    """

    def _on_data(self, connection, data):
        data, address = data
        self._protocol.datagram_received(data, address)

    def _on_close(self, connection):
        self._cleanup()

class TransportStream(Transport):
    """
    Abstract class to be used when creating a stream based
    (connection) transport.

    This implementation reflects the decisions made for the
    netius based transport abstraction, inspired by asyncio.
    """

    def _on_data(self, connection, data):
        self._protocol.data_received(data)

    def _on_close(self, connection):
        if not self._protocol == None:
            self._protocol.eof_received()
        self._cleanup()
