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

from . import request

from .common import * #@UnusedWildImport

BUFFER_SIZE = None
""" The size of the buffer that is going to be used in the
sending and receiving of packets from the client, this value
may influence performance by a large factor """

GC_TIMEOUT = 30.0
""" The timeout to be used for the running of the garbage
collector of pending request in a datagram client, this
value will be used n the delay operation of the action """

class Client(Base):
    """
    Abstract client implementation, should provide the required
    mechanisms for basic socket client handling and thread starting
    and managing techniques. Proper and concrete implementation for
    the various socket types should inherit from this class.
    """

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
        self.thread = thread
        self.daemon = daemon
        self._thread = None

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
        Base.reads(self, reads, state = state)
        for read in reads:
            self.on_read(read)

    def writes(self, writes, state = True):
        Base.writes(self, writes, state = state)
        for write in writes:
            self.on_write(write)

    def errors(self, errors, state = True):
        Base.errors(self, errors, state = state)
        for error in errors:
            self.on_error(error)

    def ensure_loop(self, env = True):
        """
        Ensures that the proper main loop thread requested in the building
        of the entity is started if that was requested.

        This mechanism is required because the thread construction and
        starting should be deferred until an operation in the connection
        is requested (lazy thread construction).

        The call to this method should be properly inserted on the code so
        that it is only called when a main (polling) loop is required.

        :type env: bool
        :param env: If the environment variables should be used for the
        setting of some of the parameters of the new client/poll to be used.
        """

        # verifies if the (run in) thread flag is set and that the there's
        # not thread currently created for the client in case any of these
        # conditions fails the control flow is returned immediately to caller
        if not self.thread: return
        if self._thread: return

        # runs the various extra variable initialization taking into
        # account if the environment variable is currently set or not
        # please note that some side effects may arise from this set
        if env: self.level = self.get_env("LEVEL", self.level)
        if env: self.diag = self.get_env("CLIENT_DIAG", self.diag, cast = bool)
        if env: self.logging = self.get_env("LOGGING", self.logging)
        if env: self.poll_name = self.get_env("POLL", self.poll_name)
        if env: self.poll_timeout = self.get_env(
            "POLL_TIMEOUT",
            self.poll_timeout,
            cast = float
        )

        # prints a debug message about the new thread to be created for
        # the client infra-structure (required for execution)
        self.debug("Starting new thread for '%s' ..." % self.name)

        # in case the thread flag is set a new thread must be constructed
        # for the running of the client's main loop then, these thread
        # may or may not be constructed using a daemon approach
        self._thread = BaseThread(owner = self, daemon = self.daemon)
        self._thread.start()

    def join(self, timeout = None):
        # runs the join operation in the thread associated with the client
        # so that the current thread blocks until the other ends execution
        self._thread.join(timeout = timeout)

class DatagramClient(Client):

    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        self.socket = None
        self.renable = True
        self.wready = True
        self.pending_s = 0
        self.pending = collections.deque()
        self.requests = []
        self.requests_m = {}
        self.pending_lock = threading.RLock()

    def boot(self):
        Client.boot(self)
        self.keep_gc(timeout = GC_TIMEOUT, run = False)

    def cleanup(self):
        Client.cleanup(self)
        del self.requests[:]
        self.requests_m.clear()

    def on_read(self, _socket):
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("read", _socket)

        # verifies if the provided socket for reading is the same
        # as the one registered in the client if that's not the case
        # return immediately to avoid unwanted operations
        if not _socket == self.socket: return

        try:
            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data, address = _socket.recvfrom(CHUNK_SIZE)
                self.on_data(address, data)
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
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("write", _socket)

        # verifies if the provided socket for writing is the same
        # as the one registered in the client if that's not the case
        # return immediately to avoid unwanted operations
        if not _socket == self.socket: return

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
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("error", _socket)

        # verifies if the provided socket for error is the same
        # as the one registered in the client if that's not the case
        # return immediately to avoid unwanted operations
        if not _socket == self.socket: return

    def on_exception(self, exception):
        self.warning(exception)
        self.log_stack()

    def on_expected(self, exception):
        self.debug(exception)

    def on_data(self, connection, data):
        pass

    def keep_gc(self, timeout = GC_TIMEOUT, run = True):
        if run: self.gc()
        self.delay(self.keep_gc, timeout)

    def gc(self, callbacks = True):
        # in case there're no requests pending in the current client
        # there's no need to start the garbage collection logic, as
        # this would required some (minimal) resources
        if not self.requests: return

        # prints a message (for debug) about the garbage collection
        # operation that is going to be run
        self.debug("Running garbage collection ...")

        # retrieves the current time value and iterates over the
        # various request currently defined in the client (pending
        # and answer) to try to find the ones that have time out
        current = time.time()
        while True:
            # verifies if the requests structure (list) is empty and
            # if that's the case break the loop, nothing more remains
            # to be processed for the current garbage collection operation
            if not self.requests: break

            # retrieves the top level request (peek operation) and
            # verifies if the timeout value of it has exceed the
            # current time if that's the case removes it as it
            # should no longer be handled (time out)
            request = self.requests[0]
            if request.timeout > current: break
            self.remove_request(request)

            # in case the (call) callbacks flag is not set continues
            # the current loop, meaning that the associated callbacks
            # are not going to be called (as expected)
            if not callbacks: continue

            # extracts the callback method from the request and in
            # case it is defined and valid calls it with an invalid
            # argument meaning that an error has occurred, note that
            # the call is encapsulated in a safe manner meaning that
            # any exception raised will be gracefully caught
            callback = request.callback
            callback and self.call_safe(callback, args = [None])

    def add_request(self, request):
        # adds the current request object to the list of requests
        # that are pending a valid response, a garbage collector
        # system should be able to erase this request from the
        # pending list in case a timeout value has passed
        self.requests.append(request)
        self.requests_m[request.id] = request

    def remove_request(self, request):
        self.requests.remove(request)
        del self.requests_m[request.id]

    def get_request(self, id):
        is_response = isinstance(id, request.Response)
        if is_response: id = id.get_id()
        return self.requests_m.get(id, None)

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
        cthread = threading.current_thread()
        tid = cthread.ident or 0
        is_safe = tid == self.tid

        # in case the thread where this code is being executed
        # is not the same the operation is considered to be not
        # safe and so it must be delayed to be executed in the
        # next loop of the thread cycle, must return immediately
        # to avoid extra subscription operations
        if not is_safe: return self.delay(self.ensure_write, safe = True)

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

    def send(
        self,
        data,
        address,
        delay = True,
        ensure_loop = True,
        callback = None
    ):
        if ensure_loop: self.ensure_loop()

        data = legacy.bytes(data)
        data_l = len(data)

        if callback: data = (data, callback)
        data = (data, address)

        cthread = threading.current_thread()
        tid = cthread.ident or 0
        is_safe = tid == self.tid

        self.pending_lock.acquire()
        try: self.pending.appendleft(data)
        finally: self.pending_lock.release()

        self.pending_s += data_l

        if self.wready:
            if is_safe and not delay: self._flush_write()
            else: self.delay(
                self._flush_write,
                immediately = True,
                verify = True,
                safe = True
            )
        else:
            self.ensure_write()

    def _send(self, _socket):
        self.wready = True
        self.pending_lock.acquire()
        try:
            while True:
                # in case there's no pending data to be sent to the
                # server side breaks the current loop (queue empty)
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
                # going to be sent to the server
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

        self.ensure_socket()
        self.writes((self.socket,), state = False)

class StreamClient(Client):

    def __init__(self, *args, **kwargs):
        Client.__init__(self, *args, **kwargs)
        self.pendings = []
        self.free_map = {}
        self._pending_lock = threading.RLock()

    def cleanup(self):
        Client.cleanup(self)
        del self.pendings[:]
        self.free_map.clear()
        self._pending_lock = None

    def ticks(self):
        self.set_state(STATE_TICK)
        self._lid = (self._lid + 1) % 2147483647
        if self.pendings: self._connects()
        self._delays()

    def info_dict(self, full = False):
        info = Client.info_dict(self, full = full)
        if full: info.update(
            pendings = len(self.pendings),
            free_conn = sum([len(value) for value in legacy.values(self.free_map)])
        )
        return info

    def acquire_c(
        self,
        host,
        port,
        ssl = False,
        key_file = None,
        cer_file = None,
        validate = False,
        callback = None
    ):
        # sets the initial value of the connection instance variable
        # to invalid, this is going to be populated with a valid
        # connection from either the pool of connections or a new one
        connection = None

        # creates the tuple that is going to describe the connection
        # and tries to retrieve a valid connection from the map of
        # free connections (connection re-usage)
        connection_t = (host, port, ssl, key_file, cer_file)
        connection_l = self.free_map.get(connection_t, None)

        # iterates continuously trying to retrieve a valid and open
        # connection from the list of connection that compose the
        # pool of connections for the current client
        while connection_l:
            # retrieves the first connection in the list (pop) and
            # then validates it trying to determine if the connection
            # is still valid (open and ready), if that's not the case
            # unsets the connection variable
            connection = connection_l.pop()
            if validate and not self.validate_c(connection): connection = None

            # in case the connection has been invalidated (possible
            # disconnect) the current loop iteration is skipped and
            # a new connection from the list of connections in pool
            # is going to be searched and validated
            if not connection: continue

            # runs the connection acquire operation that should take
            # care of the proper acquisition notification process and
            # then breaks the cycle (valid connection found)
            self.acquire(connection)
            break

        # in case no connection is found a new one must be created by
        # establishing a connect operation, this operation is not going
        # to be performed immediately as it's going to be deferred to
        # the next execution cycle (delayed execution)
        if not connection:
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

    def validate_c(self, connection, close = True):
        # sets the original valid flag value as true so that the
        # basic/default assumption on the connection is that it's
        # valid (per basis a connection is valid)
        valid = True

        # tries to retrieve the value of the error options value of
        # the socket in case it's currently set unsets the valid flag
        error = connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if error: valid = False

        # iterates continuously trying to read any pending data from
        # the connection, some of this data may indicate that the
        # connection is no longer valid for usage
        while True:
            # verifies if the value of the valid flag is false and
            # if that's the case breaks the current loop immediately
            if not valid: break

            # tries to read/receive any set of pending data from
            # the connection in case there's an exception and it's
            # considered valid ignores the exceptions and considers
            # the connection valid (breaks loop) otherwise closes the
            # connection and sets it as invalid
            try:
                data = connection.recv()
                if not data: raise errors.NetiusError("EOF received")
                connection.send(b"")
            except ssl.SSLError as error:
                error_v = error.args[0] if error.args else None
                if error_v in SSL_VALID_ERRORS: break
                if close: connection.close()
                valid = False
            except socket.error as error:
                error_v = error.args[0] if error.args else None
                if error_v in VALID_ERRORS: break
                if close: connection.close()
                valid = False
            except BaseException:
                if close: connection.close()
                valid = False

        # returns the final value on the connection validity test
        # indicating if the connection is ready for usage or not
        return valid

    def connect(
        self,
        host,
        port,
        ssl = False,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        ssl_verify = False,
        family = socket.AF_INET,
        type = socket.SOCK_STREAM,
        ensure_loop = True,
        env = True
    ):
        # runs a series of pre-validations on the provided parameters, raising
        # exceptions in case they do not comply with expected values
        if not host: raise errors.NetiusError("Invalid host for connect operation")
        if not port: raise errors.NetiusError("Invalid port for connect operation")

        # tries to retrieve some of the environment variable related values
        # so that some of these values are accessible via an external environment
        # allowing extra configuration flexibility for the client
        key_file = self.get_env("KEY_FILE", key_file) if env else key_file
        cer_file = self.get_env("CER_FILE", cer_file) if env else cer_file
        ca_file = self.get_env("CA_FILE", ca_file) if env else ca_file
        ca_root = self.get_env("CA_ROOT", ca_root, cast = bool) if env else ca_root
        ssl_verify = self.get_env("SSL_VERIFY", ssl_verify, cast = bool) if env else ssl_verify
        key_file = self.get_env("KEY_DATA", key_file, expand = True) if env else key_file
        cer_file = self.get_env("CER_DATA", cer_file, expand = True) if env else cer_file
        ca_file = self.get_env("CA_DATA", ca_file, expand = True) if env else ca_file

        # ensures that a proper loop cycle is available for the current
        # client, otherwise the connection operation would become stalled
        # because there's no listening of events for it
        if ensure_loop: self.ensure_loop()

        # ensures that the proper socket family is defined in case the
        # requested host value is unix socket oriented, this step greatly
        # simplifies the process of created unix socket based clients
        family = socket.AF_UNIX if host == "unix" else family

        # verifies the kind of socket that is going to be used for the
        # connect operation that is going to be performed, note that the
        # unix type should be used with case as it does not exist in every
        # operative system and may raised an undefined exceptions
        is_unix = hasattr(socket, "AF_UNIX") and family == socket.AF_UNIX
        is_inet = family in (socket.AF_INET, socket.AF_INET6)

        # runs a series of default operation for the ssl related attributes
        # that are going to be used in the socket creation and wrapping
        key_file = key_file or SSL_KEY_PATH
        cer_file = cer_file or SSL_CER_PATH
        ca_file = ca_file or SSL_CA_PATH

        # determines if the ssl verify flag value is valid taking into account
        # the provided value and defaulting to false value if not valid
        ssl_verify = ssl_verify or False

        # creates the client socket value using the provided family and socket
        # type values and then sets it immediately as non blocking
        _socket = socket.socket(family, type)
        _socket.setblocking(0)

        if ssl: _socket = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            ssl_verify = ssl_verify,
            server = False
        )

        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if is_inet: _socket.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
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

        # constructs the address tuple taking into account if the
        # socket is unix based or if instead it represents a "normal"
        # one and the host and port must be used instead
        address = port if is_unix else (host, port)

        # creates the connection object using the typical constructor
        # and then sets the ssl host (for verification) if the verify
        # ssl option is defined (secured and verified connection)
        connection = self.new_connection(_socket, address, ssl = ssl)
        if ssl_verify: connection.ssl_host = host

        # acquires the pending lock so that it's safe to add an element
        # to the list of pending connection for connect, this lock is
        # then released in the final part of the operation
        self._pending_lock.acquire()
        try: self.pendings.append(connection)
        finally: self._pending_lock.release()

        # returns the "final" connection, that is now scheduled for connect
        # to the caller method, it may now be used for operations
        return connection

    def acquire(self, connection):
        acquire = lambda: self.on_acquire(connection)
        self.delay(acquire)

    def on_read(self, _socket):
        # tries to retrieve a possible callback registered for the socket
        # and if there's one calls it to be able to "append" extra operations
        # to the execution of the read operation in the socket
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("read", _socket)

        # retrieves the connection object associated with the
        # current socket that is going to be read in case there's
        # no connection available or the status is not open
        # must return the control flow immediately to the caller
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return
        if not connection.renable == True: return

        try:
            # in case the connection is under the connecting state
            # the socket must be verified for errors and in case
            # there's none the connection must proceed, for example
            # the ssl connection handshake must be performed/retried
            if connection.connecting: self._connectf(connection)

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
        # tries to retrieve a possible callback registered for the socket
        # and if there's one calls it to be able to "append" extra operations
        # to the execution of the read operation in the socket
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("write", _socket)

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
        callbacks = self.callbacks_m.get(_socket, None)
        if callbacks:
            for callback in callbacks: callback("error", _socket)

        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        connection.close()

    def on_exception(self, exception, connection):
        self.warning(exception)
        self.log_stack()
        connection.close()

    def on_expected(self, exception, connection):
        self.debug(exception)
        connection.close()

    def on_connect(self, connection):
        connection.set_connected()
        if hasattr(connection, "tuple"):
            self.on_acquire(connection)

    def on_upgrade(self, connection):
        connection.set_upgraded()

    def on_ssl(self, connection):
        # runs the connection host verification process for the ssl
        # meaning that in case an ssl host value is defined it is going
        # to be verified against the value in the certificate
        connection.ssl_verify_host()

        # runs the connection fingerprint verification the will try to
        # match the digest of the peer certificate against the one that
        # is expected from it (similar to host verification)
        connection.ssl_verify_fingerprint()

        # verifies if the connection is either connecting or upgrading
        # and calls the proper event handler for each event, this is
        # required because the connection workflow is probably dependent
        # on the calling of these event handlers to proceed
        if connection.connecting: self.on_connect(connection)
        elif connection.upgrading: self.on_upgrade(connection)

    def on_acquire(self, connection):
        pass

    def on_release(self, connection):
        pass

    def on_data(self, connection, data):
        connection.set_data(data)

    def _connectf(self, connection):
        """
        Finishes the process of connecting to the remote end-point
        this should be done in certain steps of the connection.

        The process of finishing the connecting process should include
        the ssl handshaking process.

        :type connection: Connection
        :param connection: The connection that should have the connect
        process tested for finishing.
        """

        # in case the ssl connection is still undergoing the handshaking
        # procedures (marked as connecting) ignores the call as this must
        # be a duplicated call to this method (to be ignored)
        if connection.ssl_connecting: return

        # verifies if there was an error in the middle of the connection
        # operation and if that's the case calls the proper callback and
        # returns the control flow to the caller method
        error = connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if error: self.on_error(connection.socket); return

        # checks if the current connection is ssl based and if that's the
        # case starts the handshaking process (async non blocking) otherwise
        # calls the on connect callback with the newly created connection
        if connection.ssl: connection.add_starter(self._ssl_handshake)
        else: self.on_connect(connection)

        # runs the starter process (initial kick-off) so that all the starters
        # registered for the connection may start to be executed, note that if
        # the ssl handshake starter has been registered its first execution is
        # going to be triggered by this call
        connection.run_starter()

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
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            if not error_v in SSL_VALID_ERRORS:
                self.warning(error)
                self.log_stack()
                self.trigger("error", self, connection, error)
                connection.close()
                return
        except socket.error as error:
            error_v = error.args[0] if error.args else None
            if not error_v in VALID_ERRORS:
                self.warning(error)
                self.log_stack()
                self.trigger("error", self, connection, error)
                connection.close()
                return
        except BaseException as exception:
            self.warning(exception)
            self.log_stack()
            self.trigger("error", self, connection, exception)
            connection.close()
            raise

        # otherwise the connect operation has finished correctly
        # and the finish connect method should be called indicating
        # that the connect operation has completed successfully
        else:
            self._connectf(connection)

        # in case the connection is not of type ssl the method
        # may return as there's nothing left to be done, as the
        # rest of the method is dedicated to ssl tricks
        if not connection.ssl: return

        # verifies if the current ssl object is a context oriented one
        # (newest versions) or a legacy oriented one, that does not uses
        # any kind of context object, this is relevant in order to make
        # decisions on how the ssl object may be re-constructed
        has_context = hasattr(_socket, "context")
        has_sock = hasattr(_socket, "_sock")

        # creates the ssl object for the socket as it may have been
        # destroyed by the underlying ssl library (as an error) because
        # the socket is of type non blocking and raises an error, note
        # that the creation of the socket varies between ssl versions
        if _socket._sslobj: return
        if has_context: _socket._sslobj = _socket.context._wrap_socket(
            _socket,
            _socket.server_side,
            _socket.server_hostname
        )
        else: _socket._sslobj = ssl._ssl.sslwrap(
            _socket._sock if has_sock else _socket,
            False,
            _socket.keyfile,
            _socket.certfile,
            _socket.cert_reqs,
            _socket.ssl_version,
            _socket.ca_certs
        )

        # verifies if the ssl object class is defined in the ssl module
        # and if that's the case an extra wrapping operation is performed
        # in order to comply with new indirection/abstraction methods
        if not hasattr(ssl, "SSLObject"): return
        _socket._sslobj = ssl.SSLObject(_socket._sslobj, owner = _socket)

    def _ssl_handshake(self, connection):
        Client._ssl_handshake(self, connection)

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
