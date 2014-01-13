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

BUFFER_SIZE_S = None
""" The size of both the send and receive buffers for
the socket representing the server, this socket is
responsible for the handling of the new connections """

BUFFER_SIZE_C = None
""" The size of the buffers (send and receive) that
is going to be set on the on the sockets created by
the server (client sockets), this is critical for a
good performance of the server (large value) """

from common import * #@UnusedWildImport

class Server(Base):

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.receive_buffer_s = kwargs.get("receive_buffer_s", BUFFER_SIZE_S)
        self.send_buffer_s = kwargs.get("send_buffer_s", BUFFER_SIZE_S)
        self.receive_buffer_c = kwargs.get("receive_buffer_c", BUFFER_SIZE_C)
        self.send_buffer_c = kwargs.get("send_buffer_c", BUFFER_SIZE_C)
        self.socket = None
        self.host = None
        self.port = None
        self.type = None
        self.ssl = False
        self.env = False

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
        host = self.get_env("HOST", host) if env else host
        port =  self.get_env("PORT", port, cast = int) if env else port
        type = self.get_env("TYPE", type, cast = int) if env else type
        ssl = self.get_env("SSL", ssl, cast = bool) if env else ssl
        key_file = self.get_env("KEY_FILE", key_file) if env else key_file
        cer_file = self.get_env("CER_FILE", cer_file) if env else cer_file

        # runs the various extra variable initialization taking into
        # account if the environment variable is currently set or not
        # please note that some side effects may arise from this set
        if env: self.level = os.environ.get("LEVEL", self.level)

        # updates the current service status to the configuration
        # stage as the next steps is to configure the service socket
        self.set_state(STATE_CONFIG)

        # start the loading process of the base system so that the system should
        # be able to log some information that is going to be output
        self.load()

        # populates the basic information on the currently running
        # server like the host the port and the (is) ssl flag to be
        # used latter for reference operations
        self.host = host
        self.port = port
        self.type = type
        self.ssl = ssl
        self.env = env

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

        # creates the string that identifies it the current service connection
        # is using a secure channel (ssl) and then prints an info message about
        # the service that is going to be started
        ssl_s = ssl and " using ssl" or ""
        self.info("Serving '%s' service on %s:%d%s ..." % (self.name, host, port, ssl_s))

        # calls the on serve callback handler so that underlying services may be
        # able to respond to the fact that the service is starting and some of
        # them may print some specific debugging information
        self.on_serve()

        # starts the base system so that the event loop gets started and the
        # the servers gets ready to accept new connections (starts service)
        if start: self.start()

    def socket_tcp(self, ssl, key_file, cer_file):
        # retrieves the proper string based type for the current server socket
        # and the prints a series of log message about the socket to be created
        type_s = ssl and "ssl" or ""
        self.debug("Creating server's tcp %s socket ..." % type_s)
        if ssl: self.debug("Loading '%s' as key file" % key_file)
        if ssl: self.debug("Loading '%s' as certificate file" % cer_file)

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
        if self.receive_buffer_s: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            self.receive_buffer_s
        )
        if self.send_buffer_s: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            self.send_buffer_s
        )
        self._socket_keepalive(_socket)

        # returns the created tcp socket to the calling method so that it
        # may be used from this point on
        return _socket

    def socket_udp(self):
        # prints a small debug message about the udp socket that is going
        # to be created for the server's connection
        self.debug("Creating server's udp socket ...")

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

    def on_serve(self):
        pass

class DatagramServer(Server):

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.renable = True
        self.wready = True
        self.pending_s = 0
        self.pending = []
        self.pending_lock = threading.RLock()

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

    def serve(self, type = UDP_TYPE, *args, **kwargs):
        Server.serve(self, type = type, *args, **kwargs)

    def on_read(self, _socket):
        # in case the read enabled flag is not currently set
        # must return immediately because the read operation
        # is not currently being allowed
        if not self.renable == True: return

        try:
            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly, note that if the
            # read enabled flag changed in the middle of the read handler
            # the loop is stop as no more read operations are allowed
            while True:
                data, address = _socket.recvfrom(CHUNK_SIZE)
                self.on_data(address, data)
                if not self.renable == True: break
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
        tid = thread.get_ident()
        is_safe = tid == self.tid

        data_l = len(data)

        if callback: data = (data, callback)
        data = (data, address)

        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

        self.pending_s += data_l

        if self.wready:
            send = lambda: self.writes(
                (self.socket,),
                state = False
            )
            if is_safe and not delay: send()
            else: self.delay(send)
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

class StreamServer(Server):

    def reads(self, reads, state = True):
        if state: self.set_state(STATE_READ)
        for read in reads:
            if read == self.socket: self.on_read_s(read)
            else: self.on_read(read)

    def writes(self, writes, state = True):
        if state: self.set_state(STATE_WRITE)
        for write in writes:
            if write == self.socket: self.on_write_s(write)
            else: self.on_write(write)

    def errors(self, errors, state = True):
        if state: self.set_state(STATE_ERRROR)
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

    def on_write_s(self, _socket):
        pass

    def on_error_s(self, _socket):
        pass

    def on_read(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return
        if not connection.renable == True: return

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
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

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

    def on_data(self, connection, data):
        pass

    def on_socket_c(self, socket_c, address):
        if self.ssl: socket_c.pending = None

        socket_c.setblocking(0)
        socket_c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        socket_c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if self.receive_buffer_c: socket_c.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            self.receive_buffer_c
        )
        if self.send_buffer_c: socket_c.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            self.send_buffer_c
        )

        if self.ssl: self._ssl_handshake(socket_c)

        connection = self.new_connection(socket_c, address, ssl = self.ssl)
        connection.open()

    def on_socket_d(self, socket_c):
        connection = self.connections_m.get(socket_c, None)
        if not connection: return
