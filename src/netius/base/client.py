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

class Client(Base):

    def __init__(self, thread = True, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.free_map = {}
        self.pendings = []
        self._pending_lock = threading.RLock()

        if thread: BaseThread(self).start()

    def ticks(self):
        self.set_state(STATE_TICK)
        self._lid = (self._lid + 1) % 2147483647
        if self.pendings: self._connects()
        self._delays()

    def reads(self, reads):
        self.set_state(STATE_READ)
        for read in reads:
            self.on_read(read)

    def writes(self, writes):
        self.set_state(STATE_WRITE)
        for write in writes:
            self.on_write(write)

    def errors(self, errors):
        self.set_state(STATE_ERRROR)
        for error in errors:
            self.on_error(error)

    def acquire_c(self, host, port, ssl = False, key_file = None, cer_file = None, callback = None):
        connection_t = (host, port, ssl, key_file, cer_file)
        connection_l = self.free_map.get(connection_t, None)

        if connection_l:
            acquire = lambda: self.on_acquire(connection)
            connection = connection_l.pop()
            self.delay(acquire)
        else:
            connection = self.connect(
                host,
                port,
                ssl = ssl,
                key_file = key_file,
                cer_file = cer_file
            )
            connection.tuple = connection_t

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
        if connection in connection_l: connection_l.remove (connection)

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
        self._socket_keepalive(_socket)

        address = (host, port)

        connection = self.new_connection(_socket, address, ssl = ssl)

        self._pending_lock.acquire()
        try: self.pendings.append(connection)
        finally: self._pending_lock.release()

        return connection

    def on_read(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

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
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
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
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        if connection.connecting:
            if connection.ssl: self._ssl_handshake(connection.socket)
            else: self.on_connect(connection)

        try:
            connection._send()
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                connection.close()
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
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

    def _connects(self):
        self._pending_lock.acquire()
        try:
            while self.pendings:
                connection = self.pendings.pop()
                self._connect(connection)
        finally:
            self._pending_lock.release()

    def _connect(self, connection):
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
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
                self.trigger("error", self, connection, error)
                connection.close()
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)
            self.trigger("error", self, connection, exception)
            connection.close()
            raise

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
