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

class Server(Base):

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.socket = None
        self.host = None
        self.port = None
        self.type = None
        self.ssl = False

    def cleanup(self):
        Base.cleanup(self)

        # unsubscribes the current socket from all the position in
        # the current polling mechanism, required for coherence
        self.unsub_all(self.socket)

        # tries to close the service socket, as this is the one that
        # has no connection associated and is independent
        try: self.socket.close()
        except: pass

        # unsets the socket attribute as the socket should now be closed
        # and not able to be used for any kind of communication
        self.socket = None

    def info_dict(self):
        info = Base.info_dict(self)
        info["host"] = self.host
        info["port"] = self.port
        info["type"] = self.type
        info["ssl"] = self.ssl
        return info

    def serve(
        self,
        host = "127.0.0.1",
        port = 9090,
        type = TCP_TYPE,
        ssl = False,
        key_file = None,
        cer_file = None,
        start = True,
        env = False
    ):
        # processes the various default values taking into account if
        # the environment variables are meant to be processed for the
        # current context (default values are processed accordingly)
        host = os.environ.get("HOST", host) if env else host
        port = int(os.environ.get("PORT", port)) if env else port
        type = int(os.environ.get("TYPE", type)) if env else type
        ssl = bool(os.environ.get("SSL", ssl)) if env else ssl
        key_file = os.environ.get("KEY_FILE", key_file) if env else key_file
        cer_file = os.environ.get("CER_FILE", cer_file) if env else cer_file

        # updates the current service status to the configuration
        # stage as the next steps is to configure the service socket
        self.set_state(STATE_CONFIG)

        # populates the basic information on the currently running
        # server like the host the port and the (is) ssl flag to be
        # used latter for reference operations
        self.host = host
        self.port = port
        self.type = type
        self.ssl = ssl

        # defaults the provided ssl key and certificate paths to the
        # ones statically defined (dummy certificates), please beware
        # that using these certificates may create validation problems
        key_file = key_file or SSL_KEY_PATH
        cer_file = cer_file or SSL_CER_PATH

        # checks the type of service that is meant to be created and
        # creates a service socket according to the defined service
        if type == TCP_TYPE: self.socket = self.socket_tcp(ssl, key_file, cer_file)
        elif type == UDP_TYPE: self.socket = self.socket_udp()
        else: raise errors.NetiusError("Invalid server type provided '%d'" % type)

        # ensures that the current polling mechanism is correctly open as the
        # service socket is going to be added to it next
        self.poll.open()

        # adds the socket to all of the pool lists so that it's ready to read
        # write and handle error, this is the expected behavior of a service
        # socket so that it can handle all of the expected operations
        self.sub_all(self.socket)

        # binds the socket to the provided host and port and then start the
        # listening in the socket with the maximum backlog as possible
        self.socket.bind((host, port))
        if type == TCP_TYPE: self.socket.listen(5)

        # start the loading process of the base system so that the system should
        # be able to log some information that is going to be output
        self.load()

        # creates the string that identifies it the current service connection
        # is using a secure channel (ssl) and then prints an info message about
        # the service that is going to be started
        ssl_s = ssl and " using ssl" or ""
        self.info("Serving '%s' service on %s:%d%s ..." % (self.name, host, port, ssl_s))

        # starts the base system so that the event loop gets started and the
        # the servers gets ready to accept new connections (starts service)
        if start: self.start()

    def socket_tcp(self, ssl, key_file, cer_file):
        # creates the socket that it's going to be used for the listening
        # of new connections (server socket) and sets it as non blocking
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setblocking(0)

        # in case the server is meant to be used as ssl wraps the socket
        # in suck fashion so that it becomes "secured"
        if ssl: _socket = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            server = True
        )

        # sets the various options in the service socket so that it becomes
        # ready for the operation with the highest possible performance, these
        # options include the reuse address to be able to re-bind to the port
        # and address and the keep alive that drops connections after some time
        # avoiding the leak of connections (operative system managed)
        _socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._socket_keepalive(_socket)

        # returns the created tcp socket to the calling method so that it
        # may be used from this point on
        return _socket

    def socket_udp(self):
        # creates the socket that it's going to be used for the listening
        # of new connections (server socket) and sets it as non blocking
        _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _socket.setblocking(0)

        # sets the various options in the service socket so that it becomes
        # ready for the operation with the highest possible performance
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # returns the created udp socket to the calling method so that it
        # may be used from this point on
        return _socket

class DatagramServer(Server):

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.pending = []
        self.pending_lock = threading.RLock()

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

    def serve(self, type = TCP_TYPE, *args, **kwargs):
        Server.serve(self, type = type, *args, **kwargs)

    def on_read(self, _socket):
        try:
            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data, address = _socket.recvfrom(CHUNK_SIZE)
                self.on_data(address, data)
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
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
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
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

    def send(self, data, address, callback = None):
        if callback: data = (data, callback)
        data = (data, address)
        self.ensure_write()
        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

    def _send(self, _socket):
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
                    # in case there's an exception must add the data
                    # object to the list of pending data because the data
                    # has not been correctly sent
                    self.pending.append(data_o)
                    raise
                else:
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

class StreamServer(Server):

    def reads(self, reads):
        self.set_state(STATE_READ)
        for read in reads:
            if read == self.socket: self.on_read_s(read)
            else: self.on_read(read)

    def writes(self, writes):
        self.set_state(STATE_WRITE)
        for write in writes:
            if write == self.socket: self.on_write_s(write)
            else: self.on_write(write)

    def errors(self, errors):
        self.set_state(STATE_ERRROR)
        for error in errors:
            if error == self.socket: self.on_error_s(error)
            else: self.on_error(error)

    def serve(self, type = TCP_TYPE, *args, **kwargs):
        Server.serve(self, type = type, *args, **kwargs)

    def on_read_s(self, _socket):
        try:
            while True:
                socket_c, address = _socket.accept()
                try: self.on_socket_c(socket_c, address)
                except: socket_c.close(); raise
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
                self.warning(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.info(line)
        except BaseException, exception:
            self.warning(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.info(line)

    def on_write_s(self, _socket):
        pass

    def on_error_s(self, _socket):
        pass

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

    def on_data(self, connection, data):
        pass

    def on_socket_c(self, socket_c, address):
        if self.ssl: socket_c.pending = None

        socket_c.setblocking(0)
        socket_c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        socket_c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        if self.ssl: self._ssl_handshake(socket_c)

        connection = self.new_connection(socket_c, address, ssl = self.ssl)
        connection.open()

    def on_socket_d(self, socket_c):
        connection = self.connections_m.get(socket_c, None)
        if not connection: return
