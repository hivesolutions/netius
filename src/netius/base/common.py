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

import os
import ssl
import copy
import json
import errno
import heapq
import socket
import logging
import traceback

import errors
import observer

from conn import * #@UnusedWildImport
from poll import * #@UnusedWildImport

NAME = "netius"
""" The global infra-structure name to be used in the
identification of both the clients and the services this
value may be prefixed or suffixed """

VERSION = "0.8.23"
""" The version value that identifies the version of the
current infra-structure, all of the services and clients
may share this value """

WSAEWOULDBLOCK = 10035
""" The wsa would block error code meant to be used on
windows environments as a replacement for the would block
error code that indicates the failure to operate on a non
blocking connection """

WSAECONNABORTED = 10053
""" Error code meant to be raised when a connection is aborted
from the other peer meaning that that client or a server in the
as abruptly dropped the connection """

WSAECONNRESET = 10054
""" Code that is used when a connection is reset meaning that
the connection as been disconnected using a graceful approach
and without raising any extraneous problems """

POLL_ORDER = (
    EpollPoll,
    KqueuePoll,
    PollPoll,
    SelectPoll
)
""" The order from which the poll methods are going to be
selected from the fastest to the slowest, in case no explicit
poll method is defined for a base service they are selected
based on this list testing them for acceptance first """

SILENT_ERRORS = (
    errno.ECONNABORTED,
    errno.ECONNRESET,
    WSAECONNABORTED,
    WSAECONNRESET
)
""" List that contain the various connection error states that
should not raise any extra logging information because even though
they should drop the connection they are expected """

VALID_ERRORS = (
    errno.EWOULDBLOCK,
    errno.EAGAIN,
    errno.EPERM,
    errno.ENOENT,
    errno.EINPROGRESS,
    WSAEWOULDBLOCK
)
""" List containing the complete set of error that represent
non ready operations in a non blocking socket """

SSL_SILENT_ERRORS = (
    ssl.SSL_ERROR_EOF,
)
""" The list containing the errors that should be silenced
while still making the connection dropped as they are expected
to occur and should not be considered an exception """

SSL_VALID_ERRORS = (
    ssl.SSL_ERROR_WANT_READ,
    ssl.SSL_ERROR_WANT_WRITE
)
""" The list containing the valid error in the handshake
operation of the ssl connection establishment """

TCP_TYPE = 1
""" The type enumeration value that represents the tcp (stream)
based communication protocol, for various usages in the base
netius communication infra-structure """

UDP_TYPE = 2
""" The datagram based udp protocol enumeration value to be used
in static references to this kind of socket usage """

STATE_STOP = 1
""" The stop state value, this value is set when the service
is either in the constructed stage or when the service has been
stop normally or with an error """

STATE_START = 2
""" The start state set when the service is in the starting
stage and running, normal state """

STATE_CONFIG = 3
""" The configuration state that is set when the service is
preparing to become started and the configuration attributes
are being set according to pre-determined indications """

STATE_POLL = 4
""" State to be used when the service is in the polling part
of the loop, this is the most frequent state in an idle service
as the service "spends" most of its time in it """

STATE_TICK = 5
""" Tick state representative of the situation where the loop
tick operation is being started and all the pre tick handlers
are going to be called for pre-operations """

STATE_READ = 6
""" Read state that is set when the connection are being read
and the on data handlers are being called, this is the part
where all the logic driven by incoming data is being called """

STATE_WRITE = 7
""" The write state that is set on the writing of data to the
connections, this is a pretty "fast" state as no logic is
associated with it """

STATE_ERRROR = 8
""" The error state to be used when the connection is processing
any error state coming from its main select operation and associated
with a certain connection (very rare) """

STATE_STRINGS = (
    "STOP",
    "START",
    "CONFIG",
    "POLL",
    "TICK",
    "READ",
    "WRITE",
    "ERROR"
)
""" Sequence that contains the various strings associated with
the various states for the base service, this may be used to
create an integer to string resolution mechanism """

KEEPALIVE_TIMEOUT = 300
""" The amount of time in seconds that a connection is set as
idle until a new refresh token is sent to it to make sure that
it's still online and not disconnected, make sure that this
value is high enough that it does not consume to much bandwidth """

KEEPALIVE_COUNT = 3
""" The amount of times the "ping" packet is re-sent until the
connection is considered to be offline and is dropped """

KEEPALIVE_INTERVAL = int(KEEPALIVE_TIMEOUT / 10)
""" The time between the retrying of "ping" packets, this value
does not need to be too large and should not be considered too
important (may be calculated automatically) """

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
""" The format that is going to be used by the logger of the
netius infra-structure for debugging purposes it should allow
and end developer to dig into the details of the execution """

# initializes the various paths that are going to be used for
# the base files configuration in the complete service infra
# structure, these should include the ssl based files
BASE_PATH = os.path.dirname(__file__)
EXTRAS_PATH = os.path.join(BASE_PATH, "extras")
SSL_KEY_PATH = os.path.join(EXTRAS_PATH, "net.key")
SSL_CER_PATH = os.path.join(EXTRAS_PATH, "net.cer")

class Base(observer.Observable):
    """
    Base network structure to be used by all the network
    capable infra-structures (eg: servers and clients).

    Should handle all the nonblocking event loop so that
    the read and write operations are easy to handle.
    """

    def __init__(self, name = None, handlers = None, *args, **kwargs):
        observer.Observable.__init__(self, *args, **kwargs)
        poll = Base.test_poll()
        self.name = name or self.__class__.__name__
        self.handler_stream = logging.StreamHandler()
        self.handlers = handlers or (self.handler_stream,)
        self.level = kwargs.get("level", logging.DEBUG)
        self.tid = None
        self.logger = None
        self.poll = kwargs.get("poll", poll)()
        self.poll_name = self.poll.name()
        self.poll_timeout = kwargs.get("poll_timeout", POLL_TIMEOUT)
        self.connections = []
        self.connections_m = {}
        self._uuid = uuid.uuid4()
        self._lid = 0
        self._running = False
        self._loaded = False
        self._delayed = []
        self._delayed_o = []
        self.set_state(STATE_STOP);

    def __del__(self):
        self.close()

    @classmethod
    def test_poll(cls, preferred = None):
        # sets the initial selected variable with the unselected
        # (invalid) value so that at lease one selection must be
        # done in order for this method to succeed
        selected = None

        # iterates over all the poll classes ordered by preference
        # (best first) and tries to find the one that better matched
        # the current situation, either the preferred poll method or
        # the most performant one in case it's not possible
        for poll in POLL_ORDER:
            if not poll.test(): continue
            if not selected: selected = poll
            if not preferred: break
            name = poll.name()
            if not name == preferred: continue
            selected = poll
            break

        # in case no polling method was selected must raise an exception
        # indicating that no valid polling mechanism is available
        if not selected: raise errors.NetiusError(
            "No valid poll mechanism available"
        )

        # returns the selected polling mechanism class to the caller method
        # as expected by the current method
        return selected

    def delay(self, callable, timeout = None, verify = False):
        # creates the original target value with a zero value (forced
        # execution in next tick) in case the timeout value is set the
        # value is incremented to the current time, then created the
        # callable original tuple with the target (time) and the callable
        target = 0
        if timeout: target = time.time() + timeout
        callable_o = (target, callable)

        # in case the verify flag is set, must verify id the callable
        # is already inserted in the list of delayed operations in
        # case it does returns immediately to avoid duplicated values
        is_duplicate = verify and callable_o in self._delayed_o
        if is_duplicate: return

        # creates the "final" callable tuple with the target time, the
        # callable and the loop id (lid) then inserts both the delayed
        # (original) callable tuple and the callable tuple in the lists
        callable_t = (target, callable, self._lid)
        heapq.heappush(self._delayed, callable_t)
        heapq.heappush(self._delayed_o, callable_o)

    def load(self):
        if self._loaded: return

        self.load_logging(self.level);
        self._loaded = True

    def load_logging(self, level = logging.DEBUG, format = LOG_FORMAT):
        level_t = type(level)
        if not level_t == types.IntType: level = logging.getLevelName(level)
        formatter = logging.Formatter(format)
        identifier = self.get_id()
        self.handler_stream.setLevel(level)
        self.handler_stream.setFormatter(formatter)
        self.logger = logging.getLogger(identifier)
        self.logger.parent = None
        self.logger.setLevel(level)
        for handler in self.handlers:
            if not handler: continue
            self.logger.addHandler(handler)

    def start(self):
        # re-builds the polling structure with the new name this
        # is required so that it's possible to change the polling
        # mechanism in the middle of the loading process
        self.poll = self.build_poll()

        # retrieves the name of the polling mechanism that is
        # going to be used in the main loop of the current
        # base service, this is going to be used for diagnostics
        poll_name = self.get_poll_name()

        # retrieves the current thread identifier as the current
        # "tid" value to be used for thread control mechanisms
        self.tid = thread.get_ident()

        # triggers the loading of the internal structures of
        # the base structure in case the loading has already
        # been done nothing is done (avoids duplicated load)
        self.load()

        # opens the polling mechanism so that its internal structures
        # become ready for the polling cycle, the inverse operation
        # (close) should be performed as part of the cleanup
        self.poll.open(timeout = self.poll_timeout)

        # sets the running flag that controls the running of the
        # main loop and then changes the current state to start
        # as the main loop is going to start
        self._running = True
        self.set_state(STATE_START)

        # enters the main loop operation printing a message
        # to the logger indicating this start, this stage
        # should block the thread until a stop call is made
        self.debug("Starting '%s' service main loop (%.2fs) ..." % (self.name, self.poll_timeout))
        self.debug("Using '%s' as polling mechanism" % poll_name)
        self.trigger("start", self)
        try: self.loop()
        except (KeyboardInterrupt, SystemExit):
            self.info("Finishing '%s' service on user request ..." % self.name)
        except BaseException, exception:
            self.error(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.warning(line)
        except:
            self.critical("Critical level loop exception raised")
            lines = traceback.format_exc().splitlines()
            for line in lines: self.error(line)
        finally:
            self.trigger("stop", self)
            self.debug("Finished '%s' service main loop" % self.name)
            self.cleanup()
            self.set_state(STATE_STOP)

    def stop(self):
        self._running = False

    def close(self):
        self.stop()

    def is_edge(self):
        return self.poll.is_edge()

    def is_empty(self):
        return self.poll.is_empty()

    def is_sub_read(self, socket):
        return self.poll.is_sub_read(socket)

    def is_sub_write(self, socket):
        return self.poll.is_sub_write(socket)

    def is_sub_error(self, socket):
        return self.poll.is_sub_error(socket)

    def sub_all(self, socket):
        return self.poll.sub_all(socket, owner = self)

    def unsub_all(self, socket):
        return self.poll.unsub_all(socket)

    def sub_read(self, socket):
        return self.poll.sub_read(socket, owner = self)

    def sub_write(self, socket):
        return self.poll.sub_write(socket, owner = self)

    def sub_error(self, socket):
        return self.poll.sub_error(socket, owner = self)

    def unsub_read(self, socket):
        return self.poll.unsub_read(socket)

    def unsub_write(self, socket):
        return self.poll.unsub_write(socket)

    def unsub_error(self, socket):
        return self.poll.unsub_error(socket)

    def cleanup(self):
        # creates a copy of the connections list because this structure
        # is going to be changed in the closing of the connection object
        connections = copy.copy(self.connections)

        # iterates over the complete set of connections currently
        # registered in the base structure and closes them so that
        # can no longer be used and are gracefully disconnected
        for connection in connections: connection.close()

        # closes the current poll mechanism so that no more issues arise
        # from an open poll system (memory leaks, etc.)
        self.poll.close()

    def loop(self):
        # iterates continuously while the running flag
        # is set, once it becomes unset the loop breaks
        # at the next execution cycle
        while self._running:
            # calls the base tick int handler indicating that a new
            # tick loop iteration is going to be started, all the
            # "in between loop" operation should be performed in this
            # callback as this is the "space" they have for execution
            self.ticks()

            print "cenas"

            # updates the current state to poll to indicate
            # that the base service is selecting the connections
            self.set_state(STATE_POLL)

            # runs the main selection operation on the current set
            # of connection for each of the three operations returning
            # the resulting active sets for the callbacks
            reads, writes, errors = self.poll.poll()

            # calls the various callbacks with the selections lists,
            # these are the main entry points for the logic to be executed
            # each of this methods should be implemented in the underlying
            # class instances as no behavior is defined at this inheritance
            # level (abstract class)
            self.reads(reads)
            self.writes(writes)
            self.errors(errors)

    def ticks(self):
        # updates the current state value to the tick state indicating
        # that the current process is updating a new tick in loop
        self.set_state(STATE_TICK)

        # "calculates" the new loop id by incrementing one value
        # to the previous one, note that the value is calculated
        # in a modulus way so that no overflow occurs
        self._lid = (self._lid + 1) % 2147483647

        # runs the processing of the delayed calls so that the pending
        # calls are called if the correct time has been reached
        self._delays()

    def reads(self, reads, state = True):
        if state: self.set_state(STATE_READ)

    def writes(self, writes, state = True):
        if state: self.set_state(STATE_WRITE)

    def errors(self, errors, state = True):
        if state: self.set_state(STATE_ERRROR)

    def on_connection_c(self, connection):
        self.debug(
            "Connection '%s' from '%s' created ..." %\
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are '%d' connections for '%s' ..." %\
            (len(connection.owner.connections), connection.owner.name)
        )

    def on_connection_d(self, connection):
        self.debug(
            "Connection '%s' from '%s' deleted" %\
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are '%d' connections for '%s' ..." %\
            (len(connection.owner.connections), connection.owner.name)
        )

    def info_dict(self):
        info = dict()
        info["loaded"] = self._loaded
        info["connections"] = len(self.connections)
        info["state"] = self.get_state_s()
        info["poll"] = self.get_poll_name()
        return info

    def new_connection(self, socket, address, ssl = False):
        """
        Creates a new connection for the provided socket
        object and string based address, the returned
        value should be a workable object.

        @type socket: Socket
        @param socket: The socket object to be encapsulated
        by the object to be created (connection).
        @type address: String
        @param address: The address as a string to be used to
        describe the connection object to be created.
        @type ssl: bool
        @param ssl: If the connection to be created is meant to
        be secured using the ssl framework for encryption.
        @rtype: Connection
        @return: The connection object that encapsulates the
        provided socket and address values.
        """

        return Connection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def load_config(self, path = "config.json", **kwargs):
        kwargs = self.apply_config(path, kwargs)
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def apply_config(self, path, kwargs):
        if not os.path.exists(path): return kwargs

        self.info("Applying configuration file '%s' ..." % path)

        kwargs = copy.copy(kwargs)
        file = open(path, "rb")
        try: contents = json.load(file)
        finally: file.close()

        for key, value in contents.iteritems():
            kwargs[key] = value

        return kwargs

    def is_debug(self):
        return self.logger.isEnabledFor(logging.DEBUG)

    def is_info(self):
        return self.logger.isEnabledFor(logging.INFO)

    def is_warning(self):
        return self.logger.isEnabledFor(logging.WARNING)

    def is_error(self):
        return self.logger.isEnabledFor(logging.ERROR)

    def is_critical(self):
        return self.logger.isEnabledFor(logging.CRITICAL)

    def debug(self, object):
        self.log(object, level = logging.DEBUG)

    def info(self, object):
        self.log(object, level = logging.INFO)

    def warning(self, object):
        self.log(object, level = logging.WARNING)

    def error(self, object):
        self.log(object, level = logging.ERROR)

    def critical(self, object):
        self.log(object, level = logging.CRITICAL)

    def log(self, object, level = logging.INFO):
        object_t = type(object)
        try: message = unicode(object) if not object_t in types.StringTypes else object
        except: message = str(object).decode("utf-8", errors = "ignore")
        if not self.logger: return
        self.logger.log(level, message)

    def build_poll(self):
        # verifies if the currently set polling mechanism is open in
        # case it's no need to re-build the polling mechanism, otherwise
        # rebuild the polling mechanism with the current name and returns
        # the new poll object to the caller method (as expected)
        if self.poll and self.poll.is_open(): return self.poll
        self.poll = Base.test_poll(preferred = self.poll_name)()
        return self.poll

    def get_id(self):
        return NAME + "-" + str(self._uuid)

    def get_poll(self):
        return self.poll

    def get_poll_name(self):
        poll = self.get_poll()
        name = poll.name()
        return name

    def set_state(self, state):
        self._state = state

    def get_state_s(self, lower = True):
        """
        Retrieves a string describing the current state
        of the system, this string should be as descriptive
        as possible.

        An optional parameter controls if the string should
        be lower cased or not.

        @type lower: bool
        @param lower: If the returned string should be converted
        into a lower cased version.
        @rtype: String
        @return: A string describing the current sate of the loop
        system, should be as descriptive as possible.
        """

        state_s = STATE_STRINGS[self._state - 1]
        state_s = state_s.lower() if lower else state_s
        return state_s

    def get_env(self, name, default = None, cast = str):
        """
        Retrieves the value of the environment variable with the
        requested name, defaulting to the provided value in case
        it's not possible to find such variable.

        An optional cast type may be provided in order to cast the
        value of the environment variable in to the target type.

        @type name: String
        @param name: The name of the environment variable that is
        meant to be retrieved from the current environment
        @type default: Object
        @param default: The default value to be returned in case
        no value is found for the provided name.
        @type cast: Type
        @param cast: The cast type to be used to cast the value
        of the requested environment variable.
        @rtype: Object
        @return: The value of the requested environment variable
        properly casted into the target value.
        """

        if not name in os.environ: return default
        value = os.environ.get(name, default)
        try: value = int(value) == 1 if cast == bool else cast(value)
        except: value = value
        return value

    def _pending(self, _socket):
        """
        Tries to perform the pending operations in the socket
        and, these operations are set in the pending variable
        of the socket structure.

        The method returns if there are still pending operations
        after this method tick.

        @type _socket: Socket
        @param _socket: The socket object to be checked for
        pending operations and that is going to be used in the
        performing of these operations.
        @rtype: bool
        @return: If there are still pending operations to be
        performed in the provided socket.
        """

        # verifies if the pending attribute exists in the socket
        # and that the value is valid, in case it's not there's
        # no pending operation (method call) to be performed, and
        # as such must return immediately with no pending value
        if not hasattr(_socket, "_pending") or\
            not _socket._pending: return False

        # calls the pending callback method and verifies if the
        # pending value still persists in the socket if that the
        # case returns the is pending value to the caller method
        _socket._pending(_socket)
        is_pending = not _socket._pending == None
        return is_pending

    def _delays(self):
        """
        Calls the complete set of elements that are considered to
        be part of the delayed set of methods to be called.

        These methods are expected to be run before a poll call so
        that they are run outside the handling.

        The calling of the delayed methods takes into account a
        series of assumptions including the loop identifier in order
        to avoid loops in the delayed calls/insertions.
        """

        # in case there's no delayed items to be called returns immediately
        # otherwise creates a copy of the delayed list and removes all
        # of the elements from the current list in instance
        if not self._delayed: return

        # retrieves the value for the current timestamp, to be used in
        # comparisons against the target timestamps of the callables
        current = time.time()

        # creates the lists that will hold all the values that are not
        # yet ready to be called in this iteration, the value in this
        # list will be added back to the heap at the end of the iteration
        pendings = []
        pendings_o = []

        # iterates over all the delayed callable tuples to try to find
        # (and call) the ones that are meant to be executed in the past
        # (have a target timestamp with a value less than the current)
        while self._delayed:
            # "pops" the current item from the delayed list to be used
            # in the execution of the current iteration cycle
            callable_t = heapq.heappop(self._delayed)
            callable_o = heapq.heappop(self._delayed_o)

            # unpacks the current callable tuple in iteration into a
            # target (timestamp value) and a method to be called in
            # case the target timestamp is valid (in the past)
            target, method, lid = callable_t

            # tests if the current target is valid (less than or
            # equals to the current time value) and in case it's
            # not restores the value to the heap and breaks the loop
            is_valid = target <= current
            if not is_valid:
                pendings.append(callable_t)
                pendings_o.append(callable_o)
                break

            # in case the loop id present in the delayed call tuple is
            # the same as the current iteration identifier then the
            # call must be done in the next iteration cycle, this
            # verification avoids loops in calls, note that this verification
            # is only required for target zero calls referring the delayed
            # calls to be executed immediately (on next loop)
            if target == 0 and self._lid == lid:
                pendings.append(callable_t)
                pendings_o.append(callable_o)
                continue

            # calls the callback method as the delayed operation is
            # now meant to be run, this is an operation that may change
            # the current list of delayed object (causing cycles) and so
            # must be implemented with the proper precautions
            method()

        # iterates over all the pending callable tuple values and adds
        # them back to the delayed heap list so that they are called
        # latter on (not ready to be called now)
        for pending, pending_o in zip(pendings, pendings_o):
            heapq.heappush(self._delayed, pending)
            heapq.heappush(self._delayed_o, pending_o)

    def _socket_keepalive(self, _socket):
        hasattr(_socket, "TCP_KEEPIDLE") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPIDLE, #@UndefinedVariable
                KEEPALIVE_TIMEOUT
            )
        hasattr(_socket, "TCP_KEEPINTVL") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPINTVL, #@UndefinedVariable
                KEEPALIVE_INTERVAL
            )
        hasattr(_socket, "TCP_KEEPCNT") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPCNT, #@UndefinedVariable
                KEEPALIVE_COUNT
            )
        hasattr(_socket, "SO_REUSEPORT") and\
            self.socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEPORT, #@UndefinedVariable
                1
            )

    def _ssl_wrap(self, _socket, key_file = None, cer_file = None, server = True):
        dir_path = os.path.dirname(__file__)
        base_path = os.path.join(dir_path, "../../")
        base_path = os.path.normpath(base_path)
        extras_path = os.path.join(base_path, "extras")
        ssl_path = os.path.join(extras_path, "ssl")

        key_file = key_file or os.path.join(ssl_path, "server.key")
        cer_file = cer_file or os.path.join(ssl_path, "server.cer")

        socket_ssl = ssl.wrap_socket(
            _socket,
            keyfile = key_file,
            certfile = cer_file,
            server_side = server,
            ssl_version = ssl.PROTOCOL_SSLv23,
            do_handshake_on_connect = False,
            ciphers = "ALL"
        )
        return socket_ssl

    def _ssl_handshake(self, _socket):
        try:
            _socket.do_handshake()
            _socket._pending = None
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_VALID_ERRORS:
                _socket._pending = self._ssl_handshake
            else: raise

class BaseThread(threading.Thread):
    """
    The top level thread class that is meant to encapsulate
    a running base object and run it in a new context.
    """

    def __init__(self, owner, daemon = False, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.owner = owner
        self.daemon = daemon

    def run(self):
        threading.Thread.run(self)
        self.owner.start()
