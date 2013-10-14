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

import types
import threading

OPEN = 1
""" The open status value, meant to be used in situations
where the status of the entity is open (opposite of closed) """

CLOSED = 2
""" Closed status value to be used in entities which have
no pending structured opened and operations are limited """

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

    def __init__(self, owner, socket, address, ssl = False):
        self.status = CLOSED
        self.connecting = False
        self.owner = owner
        self.socket = socket
        self.address = address
        self.ssl = ssl
        self.pending = []
        self.pending_lock = threading.RLock()

    def open(self, connect = False):
        # in case the current status of the connection is not
        # closed does not make sense to open it as it should
        # already be open anyway (returns immediately)
        if not self.status == CLOSED: return

        # retrieves the reference to the owner object from the
        # current instance to be used to add the socket to the
        # proper pooling mechanisms (at least for reading)
        owner = self.owner

        # registers the socket for the proper reading mechanisms
        # in the polling infra-structure of the owner
        owner.read_l.append(self.socket)
        owner.error_l.append(self.socket)

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

    def close(self):
        # in case the current status of the connection is not open
        # doen't make sense to close as it's already closed
        if not self.status == OPEN: return

        # immediately sets the status of the connection as closed
        # so that no one else changed the current connection status
        # this is relevant to avoid any erroneous situation
        self.status = CLOSED

        # retrieves the reference to the owner object from the
        # current instance to be used to removed the socket from the
        # proper pooling mechanisms (at least for reading)
        owner = self.owner

        # removes the socket from all the polling mechanisms so that
        # interaction with it is no longer part of the selecting mechanism
        if self.socket in owner.read_l: owner.read_l.remove(self.socket)
        if self.socket in owner.write_l: owner.write_l.remove(self.socket)
        if self.socket in owner.error_l: owner.error_l.remove(self.socket)

        # removes the current connection from the list of connection in the
        # owner and also from the map that associates the socket with the
        # proper connection (also in the owner)
        if self in owner.connections: owner.connections.remove(self)
        if self.socket in owner.connections_m: del owner.connections_m[self.socket]

        # closes the socket, using the proper gracefully way so that
        # operations are no longer allowed in the socket, in case there's
        # an error in the operation fails silently (un purpose)
        try: self.socket.close()
        except: pass

    def set_connecting(self):
        self.connecting = True
        self.ensure_write()

    def set_connected(self):
        self.remove_write()
        self.connecting = False

    def ensure_write(self):
        if not self.status == OPEN: return
        if self.socket in self.owner.write_l: return
        self.owner.write_l.append(self.socket)

    def remove_write(self):
        if not self.status == OPEN: return
        if not self.socket in self.owner.write_l: return
        self.owner.write_l.remove(self.socket)

    def send(self, data, callback = None):
        """
        The main send call to be used by a proxy connection and
        from different threads.

        An optional callback attribute may be sent and so that
        when the send is complete it's called with a reference
        to the data object.

        Calling this method should be done with care as this can
        create dead lock or socket corruption situations.

        @type data: String
        @param data: The buffer containing the data to be sent
        through this connection to the other endpoint.
        @type callback: Function
        @param callback: Function to be called when the data set
        to be send is completely sent to the socket.
        """

        if callback: data = (data, callback)
        self.ensure_write()
        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

    def recv(self, size = CHUNK_SIZE):
        return self._recv(size = size)

    def is_open(self):
        return self.status == OPEN

    def is_closed(self):
        return self.status == CLOSED

    def _send(self):
        self.pending_lock.acquire()
        try:
            while True:
                if not self.pending: break
                data = self.pending.pop()
                data_o = data
                callback = None
                if type(data) == types.TupleType:
                    data, callback = data
                try: self.socket.send(data)
                except: self.pending.append(data_o)
                else: callback and callback(data)
        finally:
            self.pending_lock.release()

        self.remove_write()

    def _recv(self, size):
        return self.socket.recv(size)
