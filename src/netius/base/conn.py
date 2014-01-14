#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import uuid
import types
import thread
import threading

OPEN = 1
""" The open status value, meant to be used in situations
where the status of the entity is open (opposite of d) """

CLOSED = 2
""" Closed status value to be used in entities which have
no pending structured opened and operations are limited """

PENDING = 3
""" The pending status used for transient states (eg created)
connections under this state must be used carefully """

CHUNK_SIZE = 4096
""" The size of the chunk to be used while received
data from the service socket """

class Connection(object):
    """
    Abstract connection object that should encapsulate
    a socket object enabling it to be accessed in much
    more "protected" way avoiding possible sync problems.

    It should also abstract the developer from all the
    select associated complexities adding and removing the
    underlying socket from the selecting mechanism for the
    appropriate operations.
    """

    def __init__(self, owner = None, socket = None, address = None, ssl = False):
        self.status = PENDING
        self.id = str(uuid.uuid4())
        self.connecting = False
        self.owner = owner
        self.socket = socket
        self.address = address
        self.ssl = ssl
        self.renable = True
        self.wready = True
        self.pending_s = 0
        self.pending = []
        self.pending_lock = threading.RLock()

    def open(self, connect = False):
        # in case the current status of the connection is already open
        # it does not make sense to proceed with the opening of the
        # connection as the connection is already open
        if self.status == OPEN: return

        # retrieves the reference to the owner object from the
        # current instance to be used to add the socket to the
        # proper pooling mechanisms (at least for reading)
        owner = self.owner

        # registers the socket for the proper reading mechanisms
        # in the polling infra-structure of the owner
        owner.sub_read(self.socket)
        owner.sub_error(self.socket)

        # adds the current connection object to the list of
        # connections in the owner and the registers it in
        # the map that associates the socket with the connection
        owner.connections.append(self)
        owner.connections_m[self.socket] = self

        # sets the status of the current connection as open
        # as all the internal structures have been correctly
        # updated and not it's safe to perform operations
        self.status = OPEN

        # in case the connect flag is set must set the current
        # connection as connecting indicating that some extra
        # steps are still required to complete the connection
        if connect: self.set_connecting()

        # calls the top level on connection creation handler so that the owner
        # object gets notified about the creation of the connection (open)
        owner.on_connection_c(self)

    def close(self, flush = False):
        # in case the current status of the connection is closes it does
        # nor make sense to proceed with the closing as the connection
        # is already in the closed state (nothing to be done)
        if self.status == CLOSED: return

        # in case the flush flag is set a different approach is taken
        # where all the pending data is flushed (as possible) before
        # the connection is effectively closed, this is only valid in
        # case the current connection status is open and not connecting
        if flush and self.status == OPEN and not self.connecting:
            return self.close_flush()

        # immediately sets the status of the connection as closed
        # so that no one else changed the current connection status
        # this is relevant to avoid any erroneous situation
        self.status = CLOSED

        # unsets the connecting flag this is for connections that
        # are under the connecting state and that must be reverted
        # to the original not connecting state
        self.connecting = False

        # unsets the write ready flag so that no more write operations
        # are performed as requested by specification (mandatory) this
        # should avoid extra erroneous write operations
        self.wready = False

        # resets the size of the data pending to be send and the clears
        # the list of pending information (invalidation the previous one)
        self.pending_s = 0
        self.pending = []

        # retrieves the reference to the owner object from the
        # current instance to be used to removed the socket from the
        # proper pooling mechanisms (at least for reading)
        owner = self.owner

        # removes the socket from all the polling mechanisms so that
        # interaction with it is no longer part of the selecting mechanism
        self.owner.unsub_all(self.socket)

        # removes the current connection from the list of connection in the
        # owner and also from the map that associates the socket with the
        # proper connection (also in the owner)
        if self in owner.connections: owner.connections.remove(self)
        if self.socket in owner.connections_m: del owner.connections_m[self.socket]

        # closes the socket, using the proper gracefully way so that
        # operations are no longer allowed in the socket, in case there's
        # an error in the operation fails silently (on purpose)
        try: self.socket.close()
        except: pass

        # calls the top level on connection delete handler so that the owner
        # object gets notified about the deletion of the connection (closed)
        owner.on_connection_d(self)

    def close_flush(self):
        self.send("", callback = self._close_callback)

    def set_connecting(self):
        self.connecting = True
        self.ensure_write()

    def set_connected(self):
        self.remove_write()
        self.connecting = False

    def ensure_write(self):
        # retrieves the identifier of the current thread and
        # checks if it's the same as the one defined in the
        # owner in case it's not then the operation is not
        # considered to be safe and must be delayed
        tid = thread.get_ident()
        is_safe = tid == self.owner.tid

        # in case the thread where this code is being executed
        # is not the same the operation is considered to be not
        # safe and so it must be delayed to be executed in the
        # next loop of the thread cycle, must return immediately
        # to avoid extra subscription operations
        if not is_safe: self.owner.delay(self.ensure_write); return

        # verifies if the status of the connection is open and
        # in case it's not returns immediately as there's no reason
        # to so it for writing
        if not self.status == OPEN: return

        # verifies if the owner object is already subscribed for the
        # write operation in case it is returns immediately in order
        # avoid any extra subscription operation
        if self.owner.is_sub_write(self.socket): return

        # adds the current socket to the list of write operations
        # so that it's going to be available for writing as soon
        # as possible from the poll mechanism
        self.owner.sub_write(self.socket)

    def remove_write(self):
        if not self.status == OPEN: return
        self.owner.unsub_write(self.socket)

    def enable_read(self):
        """
        Enables read operations for the current connection
        this will set the read enable flag and then subscribe
        to the read operations in case the underlying poll
        method is not of type edge (level based).

        This is a dangerous operation as it may cause the system
        to stall if misused.
        """

        if not self.status == OPEN: return
        if not self.renable == False: return
        self.renable = True
        self.owner.sub_read(self.socket)

    def disable_read(self):
        """
        Disables any read operation on the current socket, does that
        by disabling the current read enable and then unsubscribing
        the current connection from the read operation.

        This is an extremely dangerous operation and the correct knowledge
        of the event poll is required to avoid stalling.
        """

        if not self.status == OPEN: return
        if not self.renable == True: return
        self.renable = False
        self.owner.unsub_read(self.socket)

    def send(self, data, delay = False, callback = None):
        """
        The main send call to be used by a proxy connection and
        from different threads.

        In case the sending should be forced as delayed (next tick)
        the delay flag should be set and the sending will be delayed.

        An optional callback attribute may be sent and so that
        when the send is complete it's called with a reference
        to the data object.

        Calling this method should be done with care as this can
        create dead lock or socket corruption situations.

        @type data: String
        @param data: The buffer containing the data to be sent
        through this connection to the other endpoint.
        @type delay: bool
        @param delay: If the send operation should be delay until
        the next tick operation or if it should be performed as
        soon as possible (as defined in specification).
        @type callback: Function
        @param callback: Function to be called when the data set
        to be send is completely sent to the socket.
        """

        # calculates the size in bytes of the provided data so
        # that it may be used latter for the incrementing of
        # of the total size of pending bytes
        data_l = len(data)

        # verifies that the connection is currently in the open
        # state and then verifies if a callback exists if that's
        # the case the data tuple must be created with the data
        # and the callback as the contents (standard process)
        if not self.status == OPEN: return
        if callback: data = (data, callback)

        # retrieves the identifier of the current thread and then
        # verifies if it's the same as thread where the event loop
        # is being executed (safe execution) for options to be taken
        tid = thread.get_ident()
        is_safe = tid == self.owner.tid

        # acquires the pending lock and then insets the
        # data into the list of pending information to
        # sent to the client end point
        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

        # increments the size of the pending data to be sent by
        # the size of the inner data buffer to be added (as requested)
        self.pending_s += data_l

        # verifies if the write ready flag is set, for that
        # case the send flushing operation must be performed
        if self.wready:
            # checks if the safe flag is set and if it is runs
            # the send operation right way otherwise "waits" until
            # the next tick operation (delayed execution)
            if is_safe and not delay: self._flush_write()
            else: self.owner.delay(self._flush_write, verify = True)

        # otherwise the write stream is not ready and so the
        # connection must be ensure to be write ready, should
        # subscribe to the write events as soon as possible
        else: self.ensure_write()

    def recv(self, size = CHUNK_SIZE):
        return self._recv(size = size)

    def is_open(self):
        return self.status == OPEN

    def is_closed(self):
        return self.status == CLOSED

    def is_pending(self):
        return self.status == PENDING

    def _send(self):
        # sets the write ready flag so that any further request to
        # write operation will be immediately performed
        self.wready = True

        # acquires the pending lock so that no other access to the
        # the pending structure is made from a different thread
        self.pending_lock.acquire()

        try:
            # iterates continuously so that all the pending data to be
            # sent is correctly sent to the other peer if that's possible
            while True:
                # verifies if there's data pending to be sent in case
                # there's not returns immediately, because there's
                # nothing pending to be done for such case
                if not self.pending: break

                # retrieves the current data chunk to be send from the
                # list of pending things and then saves the data chunk
                # in an "original" object an tries to unpack it in case
                # the type of it is a tuple
                data = self.pending.pop()
                data_o = data
                callback = None
                if type(data) == types.TupleType:
                    data, callback = data
                data_l = len(data)

                try:
                    # tries to send the data through the socket and
                    # retrieves the number of bytes that were correctly
                    # sent through the socket, this number may not be
                    # the same as the size of the data in case only
                    # part of the data has been sent
                    count = self.socket.send(data)
                except:
                    # sets the current connection write ready flag to false
                    # so that a new level notification must be received
                    self.wready = False

                    # ensures that the write event is going to be triggered
                    # this is required for so that the remaining pending
                    # data is going to be correctly written
                    self.ensure_write()

                    # in case there's an exception must add the data
                    # object to the list of pending data because the data
                    # has not been correctly sent
                    self.pending.append(data_o)
                    raise
                else:
                    # decrements the size of the pending buffer by the number
                    # of bytes that were correctly send through the buffer
                    self.pending_s -= count

                    # verifies if the data has been correctly sent through
                    # the socket and for suck situations calls the callback
                    # object, otherwise creates a new data object with only
                    # the remaining (partial data) and the callback to be
                    # sent latter (only then the callback is called)
                    is_valid = count == data_l
                    if is_valid:
                        callback and callback(self)
                    else:
                        data_o = (data[count:], callback)
                        self.pending.append(data_o)
        finally:
            # releases the pending access lock so that no leaks
            # exists and no access to the pending is prevented
            self.pending_lock.release()

        # removes the current connection from the set of connection
        # that are monitored for any write event (no longer required)
        self.remove_write()

    def _recv(self, size):
        return self.socket.recv(size)

    def _close_callback(self, connection):
        connection.close()

    def _flush_write(self):
        """
        Flush operations to be called by the delaying controller
        (in ticks) that will trigger all the write operations
        pending for the current connection's socket.
        """

        self.owner.writes((self.socket,), state = False)
