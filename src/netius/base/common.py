#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import sys
import copy
import json
import heapq
import signal
import logging
import hashlib
import tempfile
import traceback

import netius.pool
import netius.adapters

from . import log
from . import errors

from .conn import * #@UnusedWildImport
from .poll import * #@UnusedWildImport

NAME = "netius"
""" The global infra-structure name to be used in the
identification of both the clients and the services this
value may be prefixed or suffixed """

VERSION = "1.6.54"
""" The version value that identifies the version of the
current infra-structure, all of the services and clients
may share this value """

PLATFORM = "%s %d.%d.%d.%s %s" % (
    sys.subversion[0] if hasattr(sys, "subversion") else "CPython",
    sys.version_info[0],
    sys.version_info[1],
    sys.version_info[2],
    sys.version_info[3],
    sys.platform
)
""" Extra system information containing some of the details
of the technical platform that is running the system, this
string should be exposed carefully to avoid extra information
from being exposed to outside agents """

IDENTIFIER_SHORT = "%s/%s" % (NAME, VERSION)
""" The short version of the current environment's identifier
meant to be used in production like environment as it hides some
of the critical and internal information of the system """

IDENTIFIER_LONG = "%s/%s (%s)" % (NAME, VERSION, PLATFORM)
""" Longest version of the system identifier, to be used in the
development like environment as it shows critical information
about the system internals that may expose the system """

IDENTIFIER = IDENTIFIER_LONG if config._is_devel() else IDENTIFIER_SHORT
""" The identifier that may be used to identify an user agent
or service running under the current platform, this string
should comply with the typical structure for such values,
by default this value is set with the short version of the
identifier (less information) but this may be changed at
runtime if the current verbosity level is changed """

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
    errno.EPIPE,
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
    ssl.SSL_ERROR_ZERO_RETURN
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
SSL_CA_PATH = os.path.join(EXTRAS_PATH, "net.ca")
SSL_DH_PATH = os.path.join(EXTRAS_PATH, "dh.pem")
if not os.path.exists(SSL_CA_PATH): SSL_CA_PATH = None
if not os.path.exists(SSL_DH_PATH): SSL_DH_PATH = None

class AbstractBase(observer.Observable):
    """
    Base network structure to be used by all the network
    capable infra-structures (eg: servers and clients).

    Should handle all the nonblocking event loop so that
    the read and write operations are easy to handle.
    """

    def __init__(self, name = None, handlers = None, *args, **kwargs):
        observer.Observable.__init__(self, *args, **kwargs)
        poll = AbstractBase.test_poll()
        self.name = name or self.__class__.__name__
        self.handler_stream = logging.StreamHandler()
        self.handlers = handlers or (self.handler_stream,)
        self.level = kwargs.get("level", logging.INFO)
        self.diag = kwargs.get("diag", False)
        self.tid = None
        self.logger = None
        self.logging = None
        self.fpool = None
        self.poll_c = kwargs.get("poll", poll)
        self.poll = self.poll_c()
        self.poll_name = self.poll.name()
        self.poll_timeout = kwargs.get("poll_timeout", POLL_TIMEOUT)
        self.poll_owner = True
        self.diag_app = None
        self.connections = []
        self.connections_m = {}
        self._uuid = uuid.uuid4()
        self._lid = 0
        self._running = False
        self._loaded = False
        self._delayed = []
        self._delayed_o = []
        self._extra_handlers = []
        self._ssl_init()
        self.set_state(STATE_STOP)

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
        callable_o = legacy.orderable(callable_o)

        # in case the verify flag is set, must verify id the callable
        # is already inserted in the list of delayed operations in
        # case it does returns immediately to avoid duplicated values
        is_duplicate = verify and callable_o in self._delayed_o
        if is_duplicate: return

        # creates the "final" callable tuple with the target time, the
        # callable and the loop id (lid) then inserts both the delayed
        # (original) callable tuple and the callable tuple in the lists
        callable_t = (target, callable, self._lid)
        callable_t = legacy.orderable(callable_t)
        heapq.heappush(self._delayed, callable_t)
        heapq.heappush(self._delayed_o, callable_o)

    def load(self, full = False):
        # in case the current structure is considered/marked as already loaded
        # there's no need to continue with the loading execution (returns immediately)
        if self._loaded: return

        # calls the boot hook responsible for the initialization of the various
        # structures of the base system, note that is going to be called once
        # per each loop starting process (structure should be destroyed on cleanup)
        self.boot()

        # loads the various parts of the base system, under this calls each
        # of the systems should have it's internal structures started
        self.load_logging(self.level)

        # loads the diagnostics application handlers that allows external
        # interaction with the service for diagnostics/debugging
        self.load_diag()

        # calls the welcome handle this is meant to be used to print some
        # information about the finishing of the loading of the infra-structure
        # this is going to be called once per base system
        self.welcome()

        # runs the binding of the system wide signals so that if
        # any of such signals is raised it's properly handled and
        # redirected to the proper logic through exceptions
        self.bind_signals()

        # sets the private loading flag ensuring that no extra load operations
        # will be done after this first call to the loading (no duplicates)
        self._loaded = True

    def unload(self, full = False):
        # verifies if the current structure is considered/marked as already
        # "unloaded", if that's the case returns the control flow immediately
        # as there's nothing pending to be (undone)
        if not self._loaded: return

        # triggers the operation that will start the unloading process of the
        # logging infra-structure of the current system
        if full: self.unload_logging()

        # marks the current system as unloaded as the complete set of operations
        # meant to start the unloading process have been finished
        self._loaded = False

    def boot(self):
        pass

    def welcome(self):
        pass

    def load_logging(self, level = logging.DEBUG, format = LOG_FORMAT, unique = False):
        # normalizes the provided level value so that it represents
        # a proper and understandable value, then starts the formatter
        # that is going to be used and retrieves the (possibly unique)
        # identifier to be used in the logger retrieval/identification
        level = self._level(level)
        formatter = logging.Formatter(format)
        identifier = self.get_id(unique = unique)

        # retrieves the logger that is going to be according to the
        # decided identifier and then verifies that the counter value
        # is properly updated deciding also if the logger instance is
        # a new one or if instead it refers an already initialized/old
        # instance that doesn't need a new initialization process
        self.logger = logging.getLogger(identifier)
        counter = self.logger._counter if hasattr(self.logger, "_counter") else 0
        is_new = counter == 0
        self.logger._counter = counter + 1
        if not is_new: return

        # start the extra logging infrastructure (extra handlers)
        # and initializes the stream handlers with the proper level
        # and formatter values (as expected)
        self.extra_logging(level, formatter)
        self.handler_stream.setLevel(level)
        self.handler_stream.setFormatter(formatter)

        # starts the new logger instance by setting no parent to it,
        # updating the verbosity level of it and then registering the
        # complete set of handlers for it (as expected)
        self.logger.parent = None
        self.logger.setLevel(level)
        for handler in self.handlers:
            if not handler: continue
            self.logger.addHandler(handler)

    def unload_logging(self):
        # updates the counter value for the logger and validates
        # that no more "clients" are using the logger so that it
        # may be properly destroyed (as expected)
        counter = self.logger._counter
        is_old = counter == 1
        self.logger._counter = counter - 1
        if not is_old: return

        # iterates over the complete set of handlers in the current
        # base element and removes them from the current logger
        for handler in self.handlers:
            if not handler: continue
            self.logger.removeHandler(handler)

        # iterates over the complete set of (built) extra handlers
        # and runs the close operation for each of them, as they are
        # no longer considered required for logging purposes
        for handler in self._extra_handlers: handler.close()

    def extra_logging(self, level, formatter):
        """
        Loads the complete set of logging handlers defined in the
        current logging value, should be a map of definitions.

        This handlers will latter be used for piping the various
        logging messages to certain output channels.

        The creation of the handler is done using a special keyword
        arguments strategy so that python and configuration files
        are properly set as compatible.

        @type level: String/int
        @param level: The base severity level for which the new handler
        will be configured in case no extra level definition is set.
        @type formatter: Formatter
        @param formatter: The logging formatter instance to be set in
        the handler for formatting messages to the output.
        """

        # verifies if the logging attribute of the current instance is
        # defined and in case it's not returns immediately, otherwise
        # starts by converting the currently defined set of handlers into
        # a list so that it may be correctly manipulated (add handlers)
        if not self.logging: return
        self.handlers = list(self.handlers)

        # iterates over the complete set of handler configuration in the
        # logging to create the associated handler instances
        for config in self.logging:
            # gathers the base information on the current handler configuration
            # running also the appropriate transformation on the level
            name = config.get("name", None)
            _level = config.get("level", level)
            _level = self._level(_level)

            # "clones" the configuration dictionary and then removes the base
            # values so that they do not interfere with the building
            config = dict(config)
            if "level" in config: del config["level"]
            if "name" in config: del config["name"]

            # retrieves the proper building, skipping the current loop in case
            # it does not exits and then builds the new handler instance, setting
            # the proper level and formatter and then adding it to the set
            if not hasattr(log, name + "_handler"): continue
            builder = getattr(log, name + "_handler")
            handler = builder(**config)
            handler.setLevel(_level)
            handler.setFormatter(formatter)
            self.handlers.append(handler)
            self._extra_handlers.append(handler)

        # restores the handlers structure back to the "original" tuple form
        # so that no expected data types are violated
        self.handlers = tuple(self.handlers)

    def level_logging(self, level):
        """
        Changes the verbosity level of the current logging infra-structure
        into the provided level of verbosity.

        The provided value may be an integer (internal value) or a string
        representation of the requested verbosity level.

        @type level: int/String
        @param level: The (logging) for which the logging infra-structure
        must be changed, either an integer or string value.
        """

        # converts the provided logging level value (either string or
        # integer value) into the appropriate normalized value that can
        # be used internally for logging level setting
        level = self._level(level)

        # sets the (new) level value value for both the base stream
        # handler and also for the logger itself
        self.handler_stream.setLevel(level)
        self.logger.setLevel(level)

        # iterates over the complete set of attached handlers to
        # update their respective logging level
        for handler in self.handlers: handler.setLevel(level)

    def load_diag(self, env = True):
        # verifies if the diagnostics "feature" has been requested
        # for the current infra-structure and if that's not the case
        # returns the control flow immediately to the caller
        if not self.diag: return

        # runs the import operations for the diag module, note that
        # this must be performed locally no avoid any unwanted behaviour
        # or collision with a runtime process (would pose issues)
        from . import diag

        # verifies if the diag module has been correctly loaded and
        # if that's not the case fails gracefully and returns the
        # control flow to the caller method
        if not diag.loaded:
            self.info("Failed to load diagnostics, import problem")
            return

        # retrieves the various server related value for the diagnostics
        # server, taking into account if the env flag is set
        server = self.get_env("DIAG_SERVER", "netius") if env else "netius"
        host = self.get_env("DIAG_HOST", "127.0.0.1") if env else "127.0.0.1"
        port = self.get_env("DIAG_PORT", 5050, cast = int) if env else 5050

        # creates the application object that is going to be
        # used for serving the diagnostics app and then starts
        # the "serving" of it under a new thread
        self.diag_app = diag.DiagApp(self)
        self.diag_app.serve(
            server = server,
            host = host,
            port = port,
            diag = False,
            threaded = True,
            conf = False
        )

    def bind_signals(self):
        # creates the signal handler function that propagates the raising
        # of the system exit exception (proper logic is executed) and then
        # registers such handler for the (typical) sigterm signal
        def handler(signum = None, frame = None): raise SystemExit()
        try: signal.signal(signal.SIGTERM, handler)
        except: self.debug("Failed to register SIGTERM handler")

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
        cthread = threading.current_thread()
        self.tid = cthread.ident or 0

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

        # retrieves the complete set of information regarding the current
        # thread that is being used for the starting of the loop, this data
        # may be used for runtime debugging purposes (debug only data)
        cthread = threading.current_thread()
        name = cthread.getName()
        ident = cthread.ident or 0

        # enters the main loop operation printing a message
        # to the logger indicating this start, this stage
        # should block the thread until a stop call is made
        self.debug("Starting '%s' service main loop (%.2fs) ..." % (self.name, self.poll_timeout))
        self.debug("Using thread '%s' with tid '%d'" % (name, ident))
        self.debug("Using '%s' as polling mechanism" % poll_name)
        self.trigger("start", self)
        try: self.loop()
        except (KeyboardInterrupt, SystemExit):
            self.info("Finishing '%s' service on user request ..." % self.name)
        except BaseException as exception:
            self.error(exception)
            self.log_stack(method = self.warning)
        except:
            self.critical("Critical level loop exception raised")
            self.log_stack(method = self.error)
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
        # runs the unload operation for the current base container this should
        # unset/unload some of the components for this base infra-structure
        self.unload()

        # destroys the current information on the delays that are is longer
        # going to be executed as the poll/system is closing, this is required
        # in order to avoid any possible memory leak with clojures/cycles
        del self._delayed[:]
        del self._delayed_o[:]

        # runs the destroy operation on the ssl component of the base
        # element so that no more ssl is available/used (avoids leaks)
        self._ssl_destroy()

        # verifies if there's a valid (and open) file pool, if that's
        # the case starts the stop process for it so that there's no
        # leaking of file descriptors and other structures
        if self.fpool: self.fstop()

        # creates a copy of the connections list because this structure
        # is going to be changed in the closing of the connection object
        connections = copy.copy(self.connections)

        # iterates over the complete set of connections currently
        # registered in the base structure and closes them so that
        # can no longer be used and are gracefully disconnected
        for connection in connections: connection.close()

        # iterates over the complete set of sockets in the connections
        # map to properly close them (avoids any leak of resources)
        for _socket in self.connections_m: _socket.close()

        # closes the current poll mechanism so that no more issues arise
        # from an open poll system (memory leaks, etc.), note that this is
        # only performed in case the current base instance is the owner of
        # the poll that is going to be closed (works with containers)
        if self.poll_owner: self.poll.close()

        # deletes some of the internal data structures created for the instance
        # and that are considered as no longer required
        self.connections_m.clear()
        del self.connections[:]
        del self._extra_handlers[:]

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

        # runs the verification/processing of the complete set of file
        # events that have been raised meanwhile, this allows for the
        # processing of various file driven operations
        self.files()

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

    def files(self):
        if not self.fpool: return
        events = self.fpool.pop_all(denotify = True)
        for event in events:
            callback = event[-1]
            if not callback: continue
            callback(*event[1:-1])

    def fopen(self, *args, **kwargs):
        self.fensure()
        return self.fpool.open(*args, **kwargs)

    def fclose(self, *args, **kwargs):
        self.fensure()
        return self.fpool.close(*args, **kwargs)

    def fread(self, *args, **kwargs):
        self.fensure()
        return self.fpool.read(*args, **kwargs)

    def fwrite(self, *args, **kwargs):
        self.fensure()
        return self.fpool.write(*args, **kwargs)

    def fensure(self):
        if self.fpool: return
        self.fstart()

    def fstart(self):
        # verifies if there's an already open file pool for
        # the current system and if that's not the case creates
        # a new one and starts it's thread cycle
        if self.fpool: return
        self.fpool = netius.pool.FilePool()
        self.fpool.start()

        # prints a debug message stating that a new file pool is
        # being created for the handling of message events
        self.debug("Started new file pool, for async file handling")

        # tries to retrieve the file descriptor of the event virtual
        # object that is notified for each operation associated with
        # the file pool, (primary communication mechanism)
        eventfd = self.fpool.eventfd()
        if not eventfd: self.warning("Starting file pool without eventfd")
        if not eventfd: return
        if not self.poll: return
        self.poll.sub_read(eventfd)

        # echoes a debug message indicating that a new read event
        # subscription has been created for the event fd of the file pool
        self.debug("Subscribed for read operations on event fd")

    def fstop(self):
        # verifies if there's an available file pool and
        # if that's the case initializes the stopping of
        # such system, note that this is blocking call as
        # all of the thread will be joined under it
        if not self.fpool: return
        self.fpool.stop()

        # prints a debug message notifying the user that no more
        # async file handling is possible using the file pool
        self.debug("Stopped existing file pool, no more async handling")

        # tries to retrieve the event file descriptor for
        # the file pool an in case it exists unsubscribes
        # from it under the current polling system
        eventfd = self.fpool.eventfd()
        if not eventfd: self.warning("Stopping file pool without eventfd")
        if not eventfd: return
        if not self.poll: return
        self.poll.unsub_read(eventfd)

        # echoes a debug message indicating that a new read event
        # unsubscription has been created for the event fd of the file pool
        self.debug("Unsubscribed for read operations on event fd")

    def on_connection_c(self, connection):
        self.debug(
            "Connection '%s' from '%s' created ..." %
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are '%d' connections for '%s' ..." %
            (len(connection.owner.connections), connection.owner.name)
        )

    def on_connection_d(self, connection):
        self.debug(
            "Connection '%s' from '%s' deleted" %
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are '%d' connections for '%s' ..." %
            (len(connection.owner.connections), connection.owner.name)
        )

    def info_dict(self, full = False):
        info = dict(
            loaded = self._loaded,
            connections = len(self.connections),
            state = self.get_state_s(),
            poll = self.get_poll_name()
        )
        if full: info.update(
            _lid = self._lid
        )
        return info

    def info_string(self, full = False, safe = True):
        try: info = self.info_dict(full = full)
        except: info = dict()
        info_s = json.dumps(
            info,
            ensure_ascii = False,
            indent = 4,
            separators = (",", " : "),
            sort_keys = True
        )
        return info_s

    def connections_dict(self, full = False):
        connections = []
        for connection in self.connections:
            info = connection.info_dict(full = full)
            connections.append(info)
        return connections

    def connection_dict(self, id, full = False):
        connection = None
        for _connection in self.connections:
            if not _connection.id == id: continue
            connection = _connection
            break
        if not connection: return None
        return connection.info_dict(full = full)

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
        for key, value in kwargs.items():
            setattr(self, key, value)

    def apply_config(self, path, kwargs):
        if not os.path.exists(path): return kwargs

        self.info("Applying configuration file '%s' ..." % path)

        kwargs = copy.copy(kwargs)
        file = open(path, "rb")
        try: contents = json.load(file)
        finally: file.close()

        for key, value in contents.items():
            kwargs[key] = value

        return kwargs

    def is_devel(self):
        """
        Verifies if the current running environment is meant to be used
        for development purposes as opposed to a production environment.

        The method should always be used in situations where some critical
        and internal information is meant to be displayed in a development
        environment but hidden in a production one.

        This method should be used at runtime as opposed to the private
        configuration based one.

        @rtype: bool
        @return: If the current environment is development oriented or
        if it's considered to be a production one (invalid result).
        """

        return self.is_debug()

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

    def log_stack(self, method = None, info = True):
        if not method: method = self.info
        lines = traceback.format_exc().splitlines()
        for line in lines: method(line)
        if info: self.log_info(method = method)

    def log_info(self, method = None):
        if not method: method = self.info
        info_string = self.info_string(full = True)
        for line in info_string.split("\n"): method(line)

    def log(self, *args, **kwargs):
        if legacy.PYTHON_3: return self.log_python_3(*args, **kwargs)
        else: return self.log_python_2(*args, **kwargs)

    def log_python_3(self, object, level = logging.INFO):
        object_t = type(object)
        try: message = str(object) if not object_t == str else object
        except: message = str(object)
        if not self.logger: return
        self.logger.log(level, message)

    def log_python_2(self, object, level = logging.INFO):
        object_t = type(object)
        try: message = unicode(object) if not object_t in legacy.str else object #@UndefinedVariable
        except: message = str(object).decode("utf-8", "ignore")
        if not self.logger: return
        self.logger.log(level, message)

    def build_poll(self):
        # verifies if the currently set polling mechanism is open in
        # case it's ther's no need to re-build the polling mechanism
        # otherwise rebuilds the polling mechanism with the current
        # name and returns the new poll object to the caller method
        if self.poll and self.poll.is_open(): return self.poll

        # runs the testing of the poll again and verifies if the polling
        # class has changed in case it did not returns the current poll
        # instance as expected by the current infra-structure
        poll_c = AbstractBase.test_poll(preferred = self.poll_name)
        if poll_c == self.poll_c: return self.poll

        # updates the polling class with the new value and re-creates
        # the polling instance with the new polling class returning this
        # new value to the caller method
        self.poll_c = poll_c
        self.poll = self.poll_c()
        return self.poll

    def get_id(self, unique = True):
        base = NAME + "-" + self.name
        if not unique: return base
        return base + "-" + str(self._uuid)

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

    def get_env(self, name, default = None, cast = None, expand = False):
        """
        Retrieves the value of the environment variable with the
        requested name, defaulting to the provided value in case
        it's not possible to find such variable.

        An optional cast type may be provided in order to cast the
        value of the environment variable in to the target type.

        An optional expand flag may be set so that the variable gets
        expanded as a file system file, for this the newline values
        should be escaped as explicit '\n' string sequences (two chars).

        Current implementation forwards the request to the current
        configuration registry so that other data providers may
        also be used in search for configuration.

        @type name: String
        @param name: The name of the environment variable that is
        meant to be retrieved from the current environment
        @type default: Object
        @param default: The default value to be returned in case
        no value is found for the provided name.
        @type cast: Type
        @param cast: The cast type to be used to cast the value
        of the requested environment variable.
        @type expand: bool
        @param expand: If the variable should be expanded as a file
        object and stored in a temporary storage, for this situation
        the resulting object should be a string with the file path.
        @rtype: Object
        @return: The value of the requested environment variable
        properly casted into the target value.
        """

        if not name in config.CONFIGS: return default
        value = config.CONFIGS.get(name, default)
        if expand: value = self.expand(value)
        cast = config.CASTS.get(cast, cast)
        if cast and not value == None: value = cast(value)
        return value

    def expand(self, value, encoding = "utf-8", force = False):
        """
        Expands the provided string/bytes value into a file in the
        current file system so that it may be correctly used by interfaces
        that require certain values to be file system based.

        In case the force value is provided the the file is created even
        for situations where the provided value is invalid/unset.

        @type value: String
        @param value: The string/bytes based value that is going to be
        expanded into a proper file system based (temporary) file.
        @type encoding: String
        @param encoding: The encoding that is going to be used to convert
        the value into a bytes based one in case the provided value is not
        bytes compliant (and must be converted).
        @type force: bool
        @param force: If the expansion operation should be performed even
        for situations where the value is considered invalid/unset.
        @rtype: String
        @return: The path to the temporary file that has just been generated
        for the expansion of the provided value.
        """

        if not value and not force: return value
        is_bytes = legacy.is_bytes(value)
        if not is_bytes: value = value.encode(encoding)
        value = value.replace(b"\\n", b"\n")
        fd, file_path = tempfile.mkstemp()
        file = open(file_path, "wb")
        try: file.write(value)
        except: os.close(fd); file.close()
        return file_path

    def get_adapter(self, name = "memory", *args, **kwargs):
        """
        Retrieves an instance of a storage adapter described
        by the provided name, note that the dynamic (extra)
        arguments are going to be used in the construction of
        the adapter instance.

        @type name: String
        @param name: The name of the adapter to be retrieved
        this should be equivalent to the adapter class name.
        @rtype: Adapter
        @return: An instance (properly configured) of the
        requested adapter (defined by the name argument).
        """

        name_f = name.title() + "Adapter"
        adapter_c = getattr(netius.adapters, name_f)
        adapter = adapter_c(*args, **kwargs)
        return adapter

    def get_auth(self, name = "memory", *args, **kwargs):
        """
        Gathers the proper authentication handler that is being
        requested with the provided name. The retrieved auth
        is a static class that should be used from its interface
        based on class based methods.

        The state of theses authentication (handlers) is based
        on the "global" state of the environment (no instances).

        @type name: String
        @param name: The name of the authentication (handler)
        class that should be retrieved.
        @rtype: Auth
        @return: An authentication based class that may be used
        for the interaction of authentication methods.
        """

        name_f = name.title() + "Auth"
        auth_c = getattr(netius.auth, name_f)
        return auth_c

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

    def _generate(self, hashed = True):
        """
        Generates a random unique identifier that may be used
        to uniquely identify a certain object or operation.

        This method must be used carefully to avoid any unwanted
        behavior resulting from value collisions.

        @type hashed: bool
        @param hashed: If the identifier should be hashed into
        and hexadecimal string instead of an uuid based identifier.
        @rtype: String
        @return: The random unique identifier generated and that
        may be used to identify objects or operations.
        """

        identifier = str(uuid.uuid4())
        identifier = identifier.upper()
        if not hashed: return identifier
        identifier = legacy.bytes(identifier)
        hash = hashlib.sha256(identifier)
        indetifier = hash.hexdigest()
        identifier = identifier.upper()
        return indetifier

    def _socket_keepalive(self, _socket):
        is_inet = _socket.family in (socket.AF_INET, socket.AF_INET6)
        is_inet and hasattr(_socket, "TCP_KEEPIDLE") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPIDLE, #@UndefinedVariable
                KEEPALIVE_TIMEOUT
            )
        is_inet and hasattr(_socket, "TCP_KEEPINTVL") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPINTVL, #@UndefinedVariable
                KEEPALIVE_INTERVAL
            )
        is_inet and hasattr(_socket, "TCP_KEEPCNT") and\
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

    def _ssl_init(self, strict = True, env = True):
        # initializes the values of both the "main" context for ssl
        # and the map that associated an hostname and a context, both
        # are going to be used (if possible) at runtime for proper
        # resolution of both key and certificated files
        self._ssl_context = None
        self._ssl_contexts = dict()

        # verifies if the current ssl module contains a reference to
        # the ssl context class symbol if not, the control flow is
        # returned to the caller method as it's not possible to created
        # any kind of context information for ssl
        has_context = hasattr(ssl, "SSLContext")
        if not has_context: return

        # retrieves the reference to the environment variables that are going
        # to be used in the construction of the various ssl contexts, note that
        # the secure variable is extremely important to ensure that a proper and
        # secure ssl connection is established with the peer
        secure = self.get_env("SSL_SECURE", True, cast = bool) if env else False
        contexts = self.get_env("SSL_CONTEXTS", {}, cast = dict) if env else {}

        # creates the main/default ssl context setting the default key
        # and certificate information in such context, then verifies
        # if the callback registration method is defined and if it is
        # defined registers a callback for when the hostname information
        # is available, so that proper concrete context may be set, note
        # that in case the strict mode is enabled (default) the context
        # is unset for situation where no callback registration is possible
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        if secure and hasattr(ssl, "OP_NO_SSLv2"):
            self._ssl_context.options |= ssl.OP_NO_SSLv2
        if secure and hasattr(ssl, "OP_NO_SSLv3"):
            self._ssl_context.options |= ssl.OP_NO_SSLv3
        if secure and hasattr(ssl, "OP_SINGLE_DH_USE"):
            self._ssl_context.options |= ssl.OP_SINGLE_DH_USE
        if secure and hasattr(ssl, "OP_SINGLE_ECDH_USE"):
            self._ssl_context.options |= ssl.OP_SINGLE_ECDH_USE
        if secure and hasattr(ssl, "OP_CIPHER_SERVER_PREFERENCE"):
            self._ssl_context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        if secure and hasattr(self._ssl_context, "set_ecdh_curve"):
            self._ssl_context.set_ecdh_curve("prime256v1")
        if secure and SSL_DH_PATH and hasattr(self._ssl_context, "load_dh_params"):
            self._ssl_context.load_dh_params(SSL_DH_PATH)
        self._ssl_certs(self._ssl_context)
        has_callback = hasattr(self._ssl_context, "set_servername_callback")
        if has_callback: self._ssl_context.set_servername_callback(self._ssl_callback)
        elif strict: self._ssl_context = None

        # retrieves the reference to the map containing the various key
        # and certificate paths for the various defined host names and
        # uses it to create the complete set of ssl context objects
        for hostname, values in legacy.iteritems(contexts):
            context = self._ssl_ctx(values, secure = secure)
            self._ssl_contexts[hostname] = (context, values)

    def _ssl_destroy(self):
        self._ssl_context = None
        self._ssl_contexts = dict()

    def _ssl_callback(self, socket, hostname, context):
        context, values = self._ssl_contexts.get(hostname, (context, None))
        socket.context = context
        if not values: return
        ssl_host = values.get("ssl_host", None)
        if not ssl_host: return
        connection = self.connections_m.get(socket, None)
        if not connection: return
        connection.ssl_host = ssl_host

    def _ssl_ctx(self, values, context = None, secure = True):
        context = context or ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        if secure and hasattr(ssl, "OP_NO_SSLv2"):
            context.options |= ssl.OP_NO_SSLv2
        if secure and hasattr(ssl, "OP_NO_SSLv3"):
            context.options |= ssl.OP_NO_SSLv3
        if secure and hasattr(ssl, "OP_SINGLE_DH_USE"):
            context.options |= ssl.OP_SINGLE_DH_USE
        if secure and hasattr(ssl, "OP_SINGLE_ECDH_USE"):
            context.options |= ssl.OP_SINGLE_ECDH_USE
        if secure and hasattr(ssl, "OP_CIPHER_SERVER_PREFERENCE"):
            context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        if secure and hasattr(context, "set_ecdh_curve"):
            context.set_ecdh_curve("prime256v1")
        if secure and SSL_DH_PATH and hasattr(context, "load_dh_params"):
            context.load_dh_params(SSL_DH_PATH)
        key_file = values.get("key_file", None)
        cer_file = values.get("cer_file", None)
        ca_file = values.get("ca_file", None)
        ca_root = values.get("ca_root", True)
        ssl_verify = values.get("ssl_verify", False)
        cert_reqs = ssl.CERT_REQUIRED if ssl_verify else ssl.CERT_NONE
        self._ssl_certs(
            context,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            verify_mode = cert_reqs
        )
        return context

    def _ssl_certs(
        self,
        context,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = False,
        verify_mode = ssl.CERT_NONE,
        check_hostname = False
    ):
        dir_path = os.path.dirname(__file__)
        root_path = os.path.join(dir_path, "../")
        root_path = os.path.normpath(root_path)
        base_path = os.path.join(root_path, "base")
        extras_path = os.path.join(base_path, "extras")
        key_file = key_file or os.path.join(extras_path, "net.key")
        cer_file = cer_file or os.path.join(extras_path, "net.cer")
        context.load_cert_chain(cer_file, keyfile = key_file)
        context.verify_mode = verify_mode
        if hasattr(context, "check_hostname"): context.check_hostname = check_hostname
        if ca_file: context.load_verify_locations(cafile = ca_file)
        if ca_root and hasattr(context, "load_default_certs"):
            context.load_default_certs(purpose = ssl.Purpose.SERVER_AUTH)
        if ca_root and SSL_CA_PATH:
            context.load_verify_locations(cafile = SSL_CA_PATH)

    def _ssl_upgrade(
        self,
        _socket,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        server = True,
        ssl_verify = False
    ):
        socket_ssl = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            server = server,
            ssl_verify = ssl_verify
        )
        return socket_ssl

    def _ssl_wrap(
        self,
        _socket,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        server = True,
        ssl_verify = False
    ):
        dir_path = os.path.dirname(__file__)
        root_path = os.path.join(dir_path, "../")
        root_path = os.path.normpath(root_path)
        base_path = os.path.join(root_path, "base")
        extras_path = os.path.join(base_path, "extras")

        key_file = key_file or os.path.join(extras_path, "net.key")
        cer_file = cer_file or os.path.join(extras_path, "net.cer")

        cert_reqs = ssl.CERT_REQUIRED if ssl_verify else ssl.CERT_NONE

        if not self._ssl_context: return ssl.wrap_socket(
            _socket,
            keyfile = key_file,
            certfile = cer_file,
            server_side = server,
            cert_reqs = cert_reqs,
            ca_certs = ca_file,
            ssl_version = ssl.PROTOCOL_SSLv23,
            do_handshake_on_connect = False
        )

        self._ssl_certs(
            self._ssl_context,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            verify_mode = cert_reqs
        )

        socket_ssl = self._ssl_context.wrap_socket(
            _socket,
            server_side = server,
            do_handshake_on_connect = False
        )
        return socket_ssl

    def _ssl_handshake(self, _socket):
        try:
            _socket.do_handshake()
            _socket._pending = None
        except ssl.SSLError as error:
            error_v = error.args[0] if error.args else None
            if error_v in SSL_VALID_ERRORS:
                _socket._pending = self._ssl_handshake
            else: raise

    def _level(self, level):
        """
        Converts the provided logging level value into the best
        representation of it, so that it may be used to update
        a logger's level of representation.

        This method takes into account the current interpreter
        version so that no problem occur.

        @type level: String/int
        @param level: The level value that is meant to be converted
        into the best representation possible.
        @rtype: int
        @return: The best representation of the level so that it may
        be used freely for the setting of logging levels under the
        current running interpreter.
        """

        level_t = type(level)
        if level_t == int: return level
        if level == None: return level
        if level == "SILENT": return log.SILENT
        if hasattr(logging, "_checkLevel"):
            return logging._checkLevel(level)
        return logging.getLevelName(level)

    def _format_delta(self, time_delta, count = 2):
        days = time_delta.days
        hours, remainder = divmod(time_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        delta_s = ""
        if days > 0:
            delta_s += "%dd " % days
            count -= 1
        if count == 0: return delta_s.strip()
        if hours > 0:
            delta_s += "%dh " % hours
            count -= 1
        if count == 0: return delta_s.strip()
        if minutes > 0:
            delta_s += "%dm " % minutes
            count -= 1
        if count == 0: return delta_s.strip()
        delta_s += "%ds" % seconds
        return delta_s.strip()

class DiagBase(AbstractBase):

    def __init__(self, *args, **kwargs):
        AbstractBase.__init__(self, *args, **kwargs)
        self.reads_c = 0
        self.writes_c = 0
        self.errors_c = 0

    def reads(self, *args, **kwargs):
        AbstractBase.reads(self, *args, **kwargs)
        self.reads_c += 1

    def writes(self, *args, **kwargs):
        AbstractBase.writes(self, *args, **kwargs)
        self.writes_c += 1

    def errors(self, *args, **kwargs):
        AbstractBase.errors(self, *args, **kwargs)
        self.errors_c += 1

    def info_dict(self, full = False):
        info = AbstractBase.info_dict(self, full = full)
        info.update(
            reads_c = self.reads_c,
            writes_c = self.writes_c,
            errors_c = self.errors_c
        )
        return info

class BaseThread(threading.Thread):
    """
    The top level thread class that is meant to encapsulate
    a running base object and run it in a new context.

    This base thread may be used to run a network loop allowing
    a main thread to continue with execution logic.
    """

    def __init__(self, owner = None, daemon = False, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.owner = owner
        self.daemon = daemon

    def run(self):
        threading.Thread.run(self)
        if not self.owner: return
        self.owner.start()
        self.owner = None

is_diag = config.conf("DIAG", False, cast = bool)
if is_diag: Base = DiagBase
else: Base = AbstractBase
