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

from .common import * #@UnusedWildImport

BUFFER_SIZE_S = None
""" The size of both the send and receive buffers for
the socket representing the server, this socket is
responsible for the handling of the new connections """

BUFFER_SIZE_C = None
""" The size of the buffers (send and receive) that
is going to be set on the on the sockets created by
the server (client sockets), this is critical for a
good performance of the server (large value) """

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
        self.key_file = None
        self.cer_file = None
        self.ca_file = None
        self.env = False
        self.allowed = []

    def welcome(self):
        Base.welcome(self)

        self.info("Booting %s %s (%s) ..." % (NAME, VERSION, PLATFORM))

    def cleanup(self):
        Base.cleanup(self)

        # unsubscribes the current socket from all the positions in
        # the current polling mechanism, required for coherence
        self.unsub_all(self.socket)

        # tries to close the service socket, as this is the one that
        # has no connection associated and is independent
        try: self.socket.close()
        except: pass

        # unsets the socket attribute as the socket should now be closed
        # and not able to be used for any kind of communication
        self.socket = None

    def info_dict(self, full = False):
        info = Base.info_dict(self, full = full)
        info.update(
            host = self.host,
            port = self.port,
            type = self.type,
            ssl = self.ssl
        )
        return info

    def serve(
        self,
        host = None,
        port = 9090,
        type = TCP_TYPE,
        ipv6 = False,
        ssl = False,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        ssl_verify = False,
        ssl_host = None,
        ssl_fingerprint = None,
        ssl_dump = False,
        setuid = None,
        backlog = socket.SOMAXCONN,
        load = True,
        start = True,
        env = False
    ):
        # processes the various default values taking into account if
        # the environment variables are meant to be processed for the
        # current context (default values are processed accordingly)
        host = self.get_env("HOST", host) if env else host
        port = self.get_env("PORT", port, cast = int) if env else port
        type = self.get_env("TYPE", type, cast = int) if env else type
        ipv6 = self.get_env("IPV6", ipv6, cast = bool) if env else ipv6
        ssl = self.get_env("SSL", ssl, cast = bool) if env else ssl
        port = self.get_env("UNIX_PATH", port) if env else port
        key_file = self.get_env("KEY_FILE", key_file) if env else key_file
        cer_file = self.get_env("CER_FILE", cer_file) if env else cer_file
        ca_file = self.get_env("CA_FILE", ca_file) if env else ca_file
        ca_root = self.get_env("CA_ROOT", ca_root, cast = bool) if env else ca_root
        ssl_verify = self.get_env("SSL_VERIFY", ssl_verify, cast = bool) if env else ssl_verify
        ssl_host = self.get_env("SSL_HOST", ssl_host) if env else ssl_host
        ssl_fingerprint = self.get_env("SSL_FINGERPRINT", ssl_fingerprint) if env else ssl_fingerprint
        ssl_dump = self.get_env("SSL_DUMP", ssl_dump) if env else ssl_dump
        key_file = self.get_env("KEY_DATA", key_file, expand = True) if env else key_file
        cer_file = self.get_env("CER_DATA", cer_file, expand = True) if env else cer_file
        ca_file = self.get_env("CA_DATA", ca_file, expand = True) if env else ca_file
        setuid = self.get_env("SETUID", setuid, cast = int) if env else setuid
        backlog = self.get_env("BACKLOG", backlog, cast = int) if env else backlog

        # runs the various extra variable initialization taking into
        # account if the environment variable is currently set or not
        # please note that some side effects may arise from this set
        if env: self.level = self.get_env("LEVEL", self.level)
        if env: self.diag = self.get_env("DIAG", self.diag, cast = bool)
        if env: self.middleware = self.get_env("MIDDLEWARE", self.middleware, cast = list)
        if env: self.children = self.get_env("CHILD", self.children, cast = int)
        if env: self.children = self.get_env("CHILDREN", self.children, cast = int)
        if env: self.logging = self.get_env("LOGGING", self.logging)
        if env: self.poll_name = self.get_env("POLL", self.poll_name)
        if env: self.poll_timeout = self.get_env(
            "POLL_TIMEOUT",
            self.poll_timeout,
            cast = float
        )
        if env: self.keepalive_timeout = self.get_env(
            "KEEPALIVE_TIMEOUT",
            self.keepalive_timeout,
            cast = int
        )
        if env: self.keepalive_interval = self.get_env(
            "KEEPALIVE_INTERVAL",
            self.keepalive_interval,
            cast = int
        )
        if env: self.keepalive_count = self.get_env(
            "KEEPALIVE_COUNT",
            self.keepalive_count,
            cast = int
        )
        if env: self.allowed = self.get_env("ALLOWED", self.allowed, cast = list)

        # updates the current service status to the configuration
        # stage as the next steps is to configure the service socket
        self.set_state(STATE_CONFIG)

        # starts the loading process of the base system so that the system should
        # be able to log some information that is going to be output
        if load: self.load()

        # ensures the proper default address value, taking into account
        # the type of connection that is currently being used, this avoids
        # problems with multiple stack based servers (ipv4 and ipv6)
        if host == None: host = "::1" if ipv6 else "127.0.0.1"

        # defaults the provided ssl key and certificate paths to the
        # ones statically defined (dummy certificates), please beware
        # that using these certificates may create validation problems
        key_file = key_file or SSL_KEY_PATH
        cer_file = cer_file or SSL_CER_PATH
        ca_file = ca_file or SSL_CA_PATH

        # populates the basic information on the currently running
        # server like the host the port and the (is) ssl flag to be
        # used latter for reference operations
        self.host = host
        self.port = port
        self.type = type
        self.ssl = ssl
        self.ssl_host = ssl_host
        self.ssl_fingerprint = ssl_fingerprint
        self.ssl_dump = ssl_dump
        self.env = env

        # populates the key, certificate and certificate authority file
        # information with the values that have just been resolved, these
        # values are going to be used for runtime certificate loading
        self.key_file = key_file
        self.cer_file = cer_file
        self.ca_file = ca_file

        # determines if the client side certificate should be verified
        # according to the loaded certificate authority values or if
        # on the contrary no (client) validation should be performed
        ssl_verify = ssl_verify or False

        # verifies if the type of server that is going to be created is
        # unix or internet based, this allows the current infra-structure
        # to work under the much more latency free unix sockets
        is_unix = host == "unix"

        # checks the type of service that is meant to be created and
        # creates a service socket according to the defined service
        family = socket.AF_INET6 if ipv6 else socket.AF_INET
        family = socket.AF_UNIX if is_unix else family
        if type == TCP_TYPE: self.socket = self.socket_tcp(
            ssl,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            ssl_verify = ssl_verify,
            family = family
        )
        elif type == UDP_TYPE: self.socket = self.socket_udp()
        else: raise errors.NetiusError("Invalid server type provided '%d'" % type)

        # "calculates" the address "bind target", taking into account that this
        # server may be running under a unix based socket infra-structure and
        # if that's the case the target (file path) is also removed, avoiding
        # a duplicated usage of the socket (required for address re-usage)
        address = port if is_unix else (host, port)
        if is_unix and os.path.exists(address): os.remove(address)

        # binds the socket to the provided address value (per spec) and then
        # starts the listening in the socket with the provided backlog value
        # defaulting to the typical maximum backlog as possible if not provided
        self.socket.bind(address)
        if type == TCP_TYPE: self.socket.listen(backlog)

        # in case the set user id value the user of the current process should
        # be changed so that it represents the new (possibly unprivileged user)
        if setuid: os.setuid(setuid)

        # in case the selected port is zero based, meaning that a randomly selected
        # port has been assigned by the bind operation the new port must be retrieved
        # and set for the current server instance as the new port (for future reference)
        if self.port == 0: self.port = self.socket.getsockname()[1]

        # creates the string that identifies it the current service connection
        # is using a secure channel (ssl) and then prints an info message about
        # the service that is going to be started
        ipv6_s = " on ipv6" if ipv6 else ""
        ssl_s = " using ssl" if ssl else ""
        self.info("Serving '%s' service on %s:%s%s%s ..." % (self.name, host, port, ipv6_s, ssl_s))

        # runs the fork operation responsible for the forking of the
        # current process into the various child processes for multiple
        # process based parallelism, note that this must be done after
        # the master socket has been created (to be shared), note that
        # in case the result is not valid an immediate return is performed
        # as this represents a master based process (not meant to serve)
        result = self.fork()
        if not result: return

        # ensures that the current polling mechanism is correctly open as the
        # service socket is going to be added to it next, this overrides the
        # default behavior of the common infra-structure (on start)
        self.poll = self.build_poll()
        self.poll.open(timeout = self.poll_timeout)

        # adds the socket to all of the pool lists so that it's ready to read
        # write and handle error, this is the expected behavior of a service
        # socket so that it can handle all of the expected operations
        self.sub_all(self.socket)

        # calls the on serve callback handler so that underlying services may be
        # able to respond to the fact that the service is starting and some of
        # them may print some specific debugging information
        self.on_serve()

        # starts the base system so that the event loop gets started and the
        # the servers gets ready to accept new connections (starts service)
        if start: self.start()

    def socket_tcp(
        self,
        ssl = False,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        ssl_verify = False,
        family = socket.AF_INET,
        type = socket.SOCK_STREAM
    ):
        # verifies if the provided family is of type internet and if that's
        # the case the associated flag is set to valid for usage
        is_inet = family in (socket.AF_INET, socket.AF_INET6)

        # retrieves the proper string based type for the current server socket
        # and the prints a series of log message about the socket to be created
        type_s = "ssl" if ssl else ""
        self.debug("Creating server's tcp %s socket ..." % type_s)
        if ssl: self.debug("Loading '%s' as key file" % key_file)
        if ssl: self.debug("Loading '%s' as certificate file" % cer_file)
        if ssl and ca_file: self.debug("Loading '%s' as certificate authority file" % ca_file)
        if ssl and ssl_verify: self.debug("Loading with client ssl verification")

        # creates the socket that it's going to be used for the listening
        # of new connections (server socket) and sets it as non blocking
        _socket = socket.socket(family, type)
        _socket.setblocking(0)

        # in case the server is meant to be used as ssl wraps the socket
        # in suck fashion so that it becomes "secured"
        if ssl: _socket = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            ssl_verify = ssl_verify,
            server = True
        )

        # sets the various options in the service socket so that it becomes
        # ready for the operation with the highest possible performance, these
        # options include the reuse address to be able to re-bind to the port
        # and address and the keep alive that drops connections after some time
        # avoiding the leak of connections (operative system managed)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if is_inet: _socket.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
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

    def socket_udp(self, family = socket.AF_INET, type = socket.SOCK_DGRAM):
        # prints a small debug message about the udp socket that is going
        # to be created for the server's connection
        self.debug("Creating server's udp socket ...")

        # creates the socket that it's going to be used for the listening
        # of new connections (server socket) and sets it as non blocking
        _socket = socket.socket(family, type)
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
        Server.reads(self, reads, state = state)
        for read in reads:
            self.on_read(read)

    def writes(self, writes, state = True):
        Server.writes(self, writes, state = state)
        for write in writes:
            self.on_write(write)

    def errors(self, errors, state = True):
        Server.errors(self, errors, state = state)
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
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            error_m = error.reason if hasattr(error, "reason") else None
            if error_v in SSL_SILENT_ERRORS:
                self.on_expected(error)
            elif not error_v in SSL_VALID_ERRORS and\
                not error_m in SSL_VALID_REASONS:
                self.on_exception(error)
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if error_v in SILENT_ERRORS:
                self.on_expected(error)
            elif not error_v in VALID_ERRORS:
                self.on_exception(error)
        except BaseException as exception:
            self.on_exception(exception)

    def on_write(self, _socket):
        try:
            self._send(_socket)
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            error_m = error.reason if hasattr(error, "reason") else None
            if error_v in SSL_SILENT_ERRORS:
                self.on_expected(error)
            elif not error_v in SSL_VALID_ERRORS and\
                not error_m in SSL_VALID_REASONS:
                self.on_exception(error)
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if error_v in SILENT_ERRORS:
                self.on_expected(error)
            elif not error_v in VALID_ERRORS:
                self.on_exception(error)
        except BaseException as exception:
            self.on_exception(exception)

    def on_error(self, _socket):
        pass

    def on_exception(self, exception):
        self.warning(exception)
        self.log_stack()

    def on_expected(self, exception):
        self.debug(exception)

    def on_data(self, address, data):
        pass

    def ensure_write(self):
        # retrieves the identifier of the current thread and
        # checks if it's the same as the one defined in the
        # owner in case it's not then the operation is not
        # considered to be safe and must be delayed
        cthread = threading.current_thread()
        tid = cthread.ident or 0
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

    def send(self, data, address, delay = True, callback = None):
        data = legacy.bytes(data)
        data_l = len(data)

        if callback: data = (data, callback)
        data = (data, address)

        cthread = threading.current_thread()
        tid = cthread.ident or 0
        is_safe = tid == self.tid

        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

        self.pending_s += data_l

        if self.wready:
            if is_safe and not delay: self._flush_write()
            else: self.delay(
                self._flush_write,
                immediately = True,
                verify = True
            )
        else:
            self.ensure_write()

    def _send(self, _socket):
        self.wready = True
        self.pending_lock.acquire()
        try:
            while True:
                # in case there's no pending data to be sent to the
                # client side breaks the current loop (queue empty)
                if not self.pending: break

                # retrieves the current data from the pending list
                # of data to be sent and then saves the original data
                # object (for latter usage), sets the callback as not
                # defined and then unpacks the data into data and address
                data = self.pending.pop()
                data_o = data
                callback = None
                data, address = data

                # verifies if the data type of the data is a tuple and
                # if that's the case unpacks it as data and callback
                is_tuple = type(data) == tuple
                if is_tuple: data, callback = data

                # retrieves the length (in bytes) of the data that is
                # going to be sent to the client
                data_l = len(data)

                try:
                    # tries to send the data through the socket and
                    # retrieves the number of bytes that were correctly
                    # sent through the socket, this number may not be
                    # the same as the size of the data in case only
                    # part of the data has been sent
                    if data: count = _socket.sendto(data, address)
                    else: count = 0

                    # verifies if the current situation is that of a non
                    # closed socket and valid data, and if that's the case
                    # and no data has been sent the socket is considered to
                    # be in a would block situation and and such an error
                    # is raised indicating the issue (is going to be caught
                    # as a normal would block exception)
                    if data and count == 0: raise socket.error(errno.EWOULDBLOCK)
                except:
                    # sets the current connection write ready flag to false
                    # so that a new level notification must be received
                    self.wready = False

                    # ensures that the write event is going to be triggered
                    # this is required so that the remaining pending data is
                    # going to be correctly written on a new write event,
                    # triggered when the connection is ready for more writing
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

        self.writes((self.socket,), state = False)

class StreamServer(Server):

    def reads(self, reads, state = True):
        Server.reads(self, reads, state = state)
        for read in reads:
            if read == self.socket: self.on_read_s(read)
            else: self.on_read(read)

    def writes(self, writes, state = True):
        Server.writes(self, writes, state = state)
        for write in writes:
            if write == self.socket: self.on_write_s(write)
            else: self.on_write(write)

    def errors(self, errors, state = True):
        Server.errors(self, errors, state = state)
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
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            error_m = error.reason if hasattr(error, "reason") else None
            if error_v in SSL_SILENT_ERRORS:
                self.on_expected_s(error)
            elif not error_v in SSL_VALID_ERRORS and\
                not error_m in SSL_VALID_REASONS:
                self.on_exception_s(error)
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if error_v in SILENT_ERRORS:
                self.on_expected_s(error)
            elif not error_v in VALID_ERRORS:
                self.on_exception_s(error)
        except BaseException as exception:
            self.on_exception_s(exception)

    def on_write_s(self, _socket):
        pass

    def on_error_s(self, _socket):
        pass

    def on_read(self, _socket):
        # tries to retrieve the connection from the provided socket
        # object (using the associative map) in case there no connection
        # or the connection is not ready for return the control flow is
        # returned to the caller method (nothing to be done)
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return
        if not connection.renable == True: return

        try:
            # verifies if there's any pending operations in the
            # connection (eg: ssl handshaking) and performs it trying
            # to finish them, if they are still pending at the current
            # state returns immediately (waits for next loop)
            if self._pending(connection): return

            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data = connection.recv(CHUNK_SIZE)
                if data: self.on_data(connection, data)
                else: connection.close(); break
                if not connection.status == OPEN: break
                if not connection.renable == True: break
                if not connection.socket == _socket: break
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            error_m = error.reason if hasattr(error, "reason") else None
            if error_v in SSL_SILENT_ERRORS:
                self.on_expected(error, connection)
            elif not error_v in SSL_VALID_ERRORS and\
                not error_m in SSL_VALID_REASONS:
                self.on_exception(error, connection)
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if error_v in SILENT_ERRORS:
                self.on_expected(error, connection)
            elif not error_v in VALID_ERRORS:
                self.on_exception(error, connection)
        except BaseException as exception:
            self.on_exception(exception, connection)

    def on_write(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        try:
            connection._send()
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            error_m = error.reason if hasattr(error, "reason") else None
            if error_v in SSL_SILENT_ERRORS:
                self.on_expected(error, connection)
            elif not error_v in SSL_VALID_ERRORS and\
                not error_m in SSL_VALID_REASONS:
                self.on_exception(error, connection)
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if error_v in SILENT_ERRORS:
                self.on_expected(error, connection)
            elif not error_v in VALID_ERRORS:
                self.on_exception(error, connection)
        except BaseException as exception:
            self.on_exception(exception, connection)

    def on_error(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        connection.close()

    def on_exception(self, exception, connection):
        self.warning(exception)
        self.log_stack()
        connection.close()

    def on_exception_s(self, exception):
        self.warning(exception)
        self.log_stack()

    def on_expected(self, exception, connection):
        self.debug(exception)
        connection.close()

    def on_expected_s(self, exception):
        self.debug(exception)

    def on_upgrade(self, connection):
        connection.set_upgraded()

    def on_ssl(self, connection):
        # in case an ssl host verification value is defined for the server
        # the client connection is going to be verified against such host
        # to make sure the client represents the expected entity, note that
        # as a fallback the ssl verification process is performed with no
        # value defined, meaning that a possible (ssl) host value set in the
        # connection is going to be used instead for the verification
        if self.ssl_host: connection.ssl_verify_host(self.ssl_host)
        else: connection.ssl_verify_host()

        # in case the ssl fingerprint verification process is enabled for the
        # current server the client certificates are going to be verified for
        # their integrity using this technique, otherwise the default verification
        # process is going to be run instead
        if self.ssl_fingerprint: connection.ssl_verify_fingerprint(self.ssl_fingerprint)
        else: connection.ssl_verify_fingerprint()

        # in case the ssl dump flag is set the dump operation is performed according
        # to that flag, otherwise the default operation is performed, that in most
        # of the cases should prevent the dump of the information
        if self.ssl_dump: connection.ssl_dump_certificate(self.ssl_dump)
        else: connection.ssl_dump_certificate()

        # in case the current connection is under the upgrade
        # status calls the proper event handler so that the
        # connection workflow may proceed accordingly
        if connection.upgrading: self.on_upgrade(connection)

    def on_data(self, connection, data):
        pass

    def on_socket_c(self, socket_c, address):
        # verifies if the current address (host value) is present in
        # the currently defined allowed list and in case that's not
        # the case raises an exception indicating the issue
        host = address[0] if address else ""
        result = netius.common.assert_ip4(host, self.allowed)
        if not result: raise errors.NetiusError(
            "Address '%s' not present in allowed list" % host
        )

        # verifies a series of pre-conditions on the socket so
        # that it's ensured to be in a valid state before it's
        # set as a new connection for the server (validation)
        if self.ssl and not socket_c._sslobj: socket_c.close(); return

        # in case the ssl mode is enabled, "patches" the socket
        # object with an extra pending reference, that is going
        # to be to store pending callable operations in it
        if self.ssl: socket_c.pending = None

        # verifies if the socket is of type internet (either ipv4
        # of ipv6), this is going to be used for conditional setting
        # of some of the socket options
        is_inet = socket_c.family in (socket.AF_INET, socket.AF_INET6)

        # sets the socket as non blocking and then updated a series
        # of options in it, some of them taking into account if the
        # socket if of type internet (timeout values)
        socket_c.setblocking(0)
        socket_c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if is_inet: socket_c.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
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

        # the process creation is considered completed and a new
        # connection is created for it and opened, from this time
        # on a new connection is considered accepted/created for server
        connection = self.new_connection(socket_c, address, ssl = self.ssl)
        connection.open()

        # registers the ssl handshake method as a starter method
        # for the connection, so that the handshake is properly
        # performed on the initial stage of the connection (as expected)
        if self.ssl: connection.add_starter(self._ssl_handshake)

        # runs the initial try for the handshaking process, note that
        # this is an async process and further tries to the handshake
        # may come after this one (async operation) in case an exception
        # is raises the connection is closed (avoids possible errors)
        try: connection.run_starter()
        except: connection.close(); raise

    def on_socket_d(self, socket_c):
        connection = self.connections_m.get(socket_c, None)
        if not connection: return

    def _ssl_handshake(self, connection):
        Server._ssl_handshake(self, connection)

        # verifies if the socket still has finished the ssl handshaking
        # process (by verifying the appropriate flag) and then if that's
        # not the case returns immediately (nothing done)
        if not connection.ssl_handshake: return

        # prints a debug information notifying the developer about
        # the finishing of the handshaking process for the connection
        self.debug("SSL Handshaking completed for connection")

        # calls the proper callback on the connection meaning
        # that ssl is now enabled for that socket/connection and so
        # the communication between peers is now secured
        self.on_ssl(connection)
