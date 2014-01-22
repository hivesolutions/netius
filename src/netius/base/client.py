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

from common import * #@UnusedWildImport

BUFFER_SIZE = None
""" The size of the buffer that is going to be used in the
sending and receiving of packets from the client, this value
may influence performance by a large factor """

class Client(Base):

    _client = None
    """ The global static client meant to be reused by the
    various static clients that may be created, this client
    may leak creating blocking threads that will prevent the
    system from exiting correctly, in order to prevent that
    the cleanup method should be called """

    def __init__(self, thread = True, daemon = False, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.receive_buffer = kwargs.get("receive_buffer", BUFFER_SIZE)
        self.send_buffer = kwargs.get("send_buffer", BUFFER_SIZE)

        # in case the thread flag is set a new thread must be constructed
        # for the running of the client's main loop then, these thread
        # may or may not be constructed using a daemon approach
        if thread: BaseThread(self, daemon = daemon).start()

    @classmethod
    def get_client_s(cls, *args, **kwargs):
        if cls._client: return cls._client
        cls._client = cls(*args, **kwargs)
        return cls._client

    @classmethod
    def cleanup_s(cls):
        if not cls._client: return
        cls._client.close()

    def reads(self, reads, state = True):
        if state: self.set_state(STATE_READ)
        for read in reads:
            self.on_read(read)

    def writes(self, writes, state = True):
        if state: self.set_state(STATE_WRITE)
        for write in writes:
            self.on_write(write)

    def errors(self, errors, state = True):
        if state: self.set_state(STATE_ERRROR)
        for error in errors:
            self.on_error(error)

class DatagramClient(Client):

    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        self.socket = None
        self.renable = True
        self.wready = True
        self.pending_s = 0
        self.pending = []
        self.pending_lock = threading.RLock()

    def on_read(self, _socket):
        try:
            # verifies if there's any pending operations in the
            # socket (eg: ssl handshaking) and performs them trying
            # to finish them, in they are still pending at the current
            # state returns immediately (waits for next loop)
            if self._pending(_socket): return

            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data, address = _socket.recvfrom(CHUNK_SIZE)
                self.on_data(address, data)
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_SILENT_ERRORS:
                self.debug(error)
            elif not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except socket.error, error:
            error_v = error.args[0]
            if error_v in SILENT_ERRORS:
                self.debug(error)
            elif not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)

    def on_write(self, _socket):
        try:
            self._send(_socket)
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_SILENT_ERRORS:
                self.debug(error)
            elif not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except socket.error, error:
            error_v = error.args[0]
            if error_v in SILENT_ERRORS:
                self.debug(error)
            elif not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)

    def on_error(self, _socket):
        pass

    def on_data(self, connection, data):
        pass

    def ensure_socket(self):
        # in case the socket is already created and valid returns immediately
        # as nothing else remain to be done in the current method
        if self.socket: return

        # prints a small debug message about the udp socket that is going
        # to be created for the client's connection
        self.debug("Creating clients's udp socket ...")

        # creates the socket that it's going to be used for the listening
        # of new connections (client socket) and sets it as non blocking
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)

        # sets the various options in the service socket so that it becomes
        # ready for the operation with the highest possible performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # adds the socket to all of the pool lists so that it's ready to read
        # write and handle error, this is the expected behavior of a service
        # socket so that it can handle all of the expected operations
        self.sub_all(self.socket)

    def ensure_write(self):
        # retrieves the identifier of the current thread and
        # checks if it's the same as the one defined in the
        # owner in case it's not then the operation is not
        # considered to be safe and must be delayed
        tid = thread.get_ident()
        is_safe = tid == self.tid

        # in case the thread where this code is being executed
        # is not the same the operation is considered to be not
        # safe and so it must be delayed to be executed in the
        # next loop of the thread cycle, must return immediately
        # to avoid extra subscription operations
        if not is_safe: self.delay(self.ensure_write); return

        # adds the current socket to the list of write operations
        # so that it's going to be available for writing as soon
        # as possible from the poll mechanism
        self.sub_write(self.socket)

    def remove_write(self):
        self.unsub_write(self.socket)

    def enable_read(self):
        if not self.renable == False: return
        self.renable = True
        self.sub_read(self.socket)

    def disable_read(self):
        if not self.renable == True: return
        self.renable = False
        self.unsub_read(self.socket)

    def send(self, data, address, delay = False, callback = None):
        data_l = len(data)

        if callback: data = (data, callback)
        data = (data, address)

        tid = thread.get_ident()
        is_safe = tid == self.tid

        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

        self.pending_s += data_l

        if self.wready:
            if is_safe and not delay: self._flush_write()
            else: self.delay(self._flush_write, verify = True)
        else:
            self.ensure_write()

    def _send(self, _socket):
        self.wready = True
        self.pending_lock.acquire()
        try:
            while True:
                if not self.pending: break
                data = self.pending.pop()
                data_o = data
                callback = None
                data, address = data
                if type(data) == types.TupleType:
                    data, callback = data
                data_l = len(data)

                try:
                    # tries to send the data through the socket and
                    # retrieves the number of bytes that were correctly
                    # sent through the socket, this number may not be
                    # the same as the size of the data in case only
                    # part of the data has been sent
                    count = _socket.sendto(data, address)
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
                        data_o = ((data[count:], callback), address)
                        self.pending.append(data_o)
        finally:
            self.pending_lock.release()

        self.remove_write()

    def _flush_write(self):
        """
        Flush operations to be called by the delaying controller
        (in ticks) that will trigger all the write operations
        pending for the current connection's socket.
        """

        self.ensure_socket()
        self.writes((self.socket,), state = False)

class StreamClient(Client):

    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        self.pendings = []
        self.free_map = {}
        self._pending_lock = threading.RLock()

    def ticks(self):
        self.set_state(STATE_TICK)
        self._lid = (self._lid + 1) % 2147483647
        if self.pendings: self._connects()
        self._delays()

    def acquire_c(
        self,
        host,
        port,
        ssl = False,
        key_file = None,
        cer_file = None,
        callback = None
    ):
        # creates the tuple that is going to describe the connection
        # and tries to retrieve a valid connection from the map of
        # free connections (connection re-usage)
        connection_t = (host, port, ssl, key_file, cer_file)
        connection_l = self.free_map.get(connection_t, None)

        # in case the connection list was successfully retrieved a new
        # connection is re-used by acquiring the connection
        if connection_l:
            connection = connection_l.pop()
            self.acquire(connection)

        # otherwise a new connection must be created by establishing
        # a connection operation, this operation is not going to be
        # performed immediately as it's going to be deferred to the
        # next execution cycle (delayed execution)
        else:
            connection = self.connect(
                host,
                port,
                ssl = ssl,
                key_file = key_file,
                cer_file = cer_file
            )
            connection.tuple = connection_t

        # returns the connection object the caller method, this connection
        # is acquired and should be safe and ready to be used
        return connection

    def release_c(self, connection):
        if not hasattr(connection, "tuple"): return
        connection_t = connection.tuple
        connection_l = self.free_map.get(connection_t, [])
        connection_l.append(connection)
        self.free_map[connection_t] = connection_l
        self.on_release(connection)

    def remove_c(self, connection):
        if not hasattr(connection, "tuple"): return
        connection_t = connection.tuple
        connection_l = self.free_map.get(connection_t, [])
        if connection in connection_l: connection_l.remove(connection)

    def connect(self, host, port, ssl = False, key_file = None, cer_file = None):
        if not host: raise errors.NetiusError("Invalid host for connect operation")
        if not port: raise errors.NetiusError("Invalid port for connect operation")

        key_file = key_file or SSL_KEY_PATH
        cer_file = cer_file or SSL_CER_PATH

        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setblocking(0)

        if ssl: _socket = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            server = False
        )

        _socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if self.receive_buffer: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            self.receive_buffer
        )
        if self.send_buffer: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            self.send_buffer
        )
        self._socket_keepalive(_socket)

        address = (host, port)

        connection = self.new_connection(_socket, address, ssl = ssl)

        self._pending_lock.acquire()
        try: self.pendings.append(connection)
        finally: self._pending_lock.release()

        return connection

    def acquire(self, connection):
        acquire = lambda: self.on_acquire(connection)
        self.delay(acquire)

    def on_read(self, _socket):
        # retrieves the connection object associated with the
        # current socket that is going to be read in case there's
        # no connection available or the status is not open
        # must return the control flow immediately to the caller
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return
        if not connection.renable == True: return

        # in case the connection is under the connecting state
        # the socket must be verified for errors and in case
        # there's none the connection must proceed, for example
        # the ssl connection handshake must be performed/retried
        if connection.connecting: self._connectf(connection)

        try:
            # verifies if there's any pending operations in the
            # socket (eg: ssl handshaking) and performs them trying
            # to finish them, in they are still pending at the current
            # state returns immediately (waits for next loop)
            if self._pending(_socket): return

            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data = _socket.recv(CHUNK_SIZE)
                if data: self.on_data(connection, data)
                else: connection.close(); break
                if not connection.status == OPEN: break
                if not connection.renable == True: break
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_SILENT_ERRORS:
                self.debug(error)
                connection.close()
            elif not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except socket.error, error:
            error_v = error.args[0]
            if error_v in SILENT_ERRORS:
                self.debug(error)
                connection.close()
            elif not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)
            connection.close()

    def on_write(self, _socket):
        # retrieves the connection associated with the socket that
        # is ready for the write operation and verifies that it
        # exists and the current status of it is open (required)
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        # in case the connection is under the connecting state
        # the socket must be verified for errors and in case
        # there's none the connection must proceed, for example
        # the ssl connection handshake must be performed/retried
        if connection.connecting: self._connectf(connection)

        try:
            connection._send()
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_SILENT_ERRORS:
                self.debug(error)
                connection.close()
            elif not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except socket.error, error:
            error_v = error.args[0]
            if error_v in SILENT_ERRORS:
                self.debug(error)
                connection.close()
            elif not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)
            connection.close()

    def on_error(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        connection.close()

    def on_connect(self, connection):
        connection.set_connected()
        if hasattr(connection, "tuple"):
            self.on_acquire(connection)

    def on_acquire(self, connection):
        pass

    def on_release(self, connection):
        pass

    def on_data(self, connection, data):
        pass

    def _connectf(self, connection):
        """
        Finishes the process of connecting to the remote end-point
        this should be done in certain steps of the connection.

        The process of finishing the connecting process should include
        the ssl handshaking process.

        @type connection: Connection
        @param connection: The connection that should have the connect
        process tested for finishing.
        """

        error = connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if error: self.on_error(connection.socket); return

        if connection.ssl: self._ssl_handshake(connection.socket)
        else: self.on_connect(connection)

    def _connects(self):
        self._pending_lock.acquire()
        try:
            while self.pendings:
                connection = self.pendings.pop()
                self._connect(connection)
        finally:
            self._pending_lock.release()

    def _connect(self, connection):
        # in case the current connection has been closed meanwhile
        # the current connection is meant to be avoided and so the
        # method must return immediately to the caller method
        if connection.status == CLOSED: return

        # retrieves the socket associated with the connection
        # and calls the open method of the connection to proceed
        # with the correct operations for the connection
        _socket = connection.socket
        connection.open(connect = True)

        # tries to run the non blocking connection it should
        # fail and the connection should only be considered as
        # open when a write event is raised for the connection
        try: _socket.connect(connection.address)
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                self.trigger("error", self, connection, error)
                connection.close()
                return
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                self.trigger("error", self, connection, error)
                connection.close()
                return
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)
            self.trigger("error", self, connection, exception)
            connection.close()
            raise
        else:
            self._connectf(connection)

        # in case the connection is not of type ssl the method
        # may returns as there's nothing left to be done, as the
        # rest of the method is dedicated to ssl tricks
        if not connection.ssl: return

        # creates the ssl object for the socket as it may have been
        # destroyed by the underlying ssl library (as an error) because
        # the socket is of type non blocking and raises an error
        _socket._sslobj = _socket._sslobj or ssl._ssl.sslwrap(
            _socket._sock,
            False,
            _socket.keyfile,
            _socket.certfile,
            _socket.cert_reqs,
            _socket.ssl_version,
            _socket.ca_certs
        )

    def _ssl_handshake(self, _socket):
        Base._ssl_handshake(self, _socket)
        if _socket._pending: return
        connection = self.connections_m.get(_socket, None)
        connection and self.on_connect(connection)
