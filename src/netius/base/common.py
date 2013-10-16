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
import time
import errno
import select
import logging
import traceback

import observer

from conn import * #@UnusedWildImport

WSAEWOULDBLOCK = 10035
""" The wsa would block error code meant to be used on
windows environments as a replacement for the would block
error code that indicates the failure to operate on a non
blocking connection """

VALID_ERRORS = (
    errno.EWOULDBLOCK,
    errno.EAGAIN,
    errno.EPERM,
    errno.ENOENT,
    WSAEWOULDBLOCK
)
""" List containing the complete set of error that represent
non ready operations in a non blocking socket """

SSL_VALID_ERRORS = (
    ssl.SSL_ERROR_WANT_READ,
    ssl.SSL_ERROR_WANT_WRITE
)
""" The list containing the valid error in the handshake
operation of the ssl connection establishment """

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

STATE_SELECT = 4
""" State to be used when the service is in the select part
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
    "SELECT",
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

    def __init__(self, name = None, handler = None, *args, **kwargs):
        observer.Observable.__init__(self, *args, **kwargs)
        self.name = name or self.__class__.__name__
        self.handler = handler
        self.logger = None
        self.read_l = []
        self.write_l = []
        self.error_l = []
        self.connections = []
        self.connections_m = {}
        self._running = False
        self._loaded = False
        self.set_state(STATE_STOP);

    def __del__(self):
        self.close()

    def load(self):
        if self._loaded: return

        self.load_logging();
        self._loaded = True

    def load_logging(self, level = logging.DEBUG):
        logging.basicConfig(format = "%(asctime)s [%(levelname)s] %(message)s")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(level)
        self.handler and self.logger.addHandler(self.handler)

    def start(self):
        # triggers the loading of the internal structures of
        # the base structure in case the loading has already
        # been done nothing is done (avoids duplicated load)
        self.load()

        # sets the running flag that controls the running of the
        # main loop and then changes the current state to start
        # as the main loop is going to start
        self._running = True
        self.set_state(STATE_START)

        # enters the main loop operation printing a message
        # to the logger indicating this start, this stage
        # should block the thread until a stop call is made
        self.info("Starting the '%s' service main loop" % self.name)
        try: self.loop()
        except BaseException, exception:
            self.error(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.warning(line)
        except:
            self.critical("Critical level loop exception raised")
            lines = traceback.format_exc().splitlines()
            for line in lines: self.error(line)
        finally:
            self.info("Stopping the service's main loop")
            self.cleanup()
            self.set_state(STATE_STOP)

    def stop(self):
        self._running = False

    def close(self):
        self.stop()

    def is_empty(self):
        return not self.read_l and not self.write_l and not self.error_l

    def cleanup(self):
        # creates a copy of the connections list because this structure
        # is going to be changed in the closing of the connection object
        connections = copy.copy(self.connections)

        # iterates over the complete set of connections currently
        # registered in the base structure and closes them so that
        # can no longer be used and are gracefully disconnected
        for connection in connections: connection.close()

        # removes the contents of all of the loop related structures
        # so that no extra selection operations are issued
        del self.read_l[:]
        del self.write_l[:]
        del self.error_l[:]

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

            # updates the current state to select to indicate
            # that the base service is selecting the connections
            self.set_state(STATE_SELECT)

            # verifies if the current selection list is empty
            # in case it's sleeps for a while and then continues
            # the loop (this avoids error in empty selection)
            is_empty = self.is_empty()
            if is_empty: time.sleep(0.25); continue

            # runs the main selection operation on the current set
            # of connection for each of the three operations returning
            # the resulting active sets for the callbacks
            reads, writes, errors = select.select(
                self.read_l,
                self.write_l,
                self.error_l,
                0.25
            )

            # calls the various callbacks with the selections lists,
            # these are the main entry points for the logic to be executed
            # each of this methods should be implemented in the underlying
            # class instances as no behavior is defined at this inheritance
            # level (abstract class)
            self.reads(reads)
            self.writes(writes)
            self.errors(errors)

    def ticks(self):
        self.set_state(STATE_TICK)

    def reads(self, reads):
        self.set_state(STATE_READ)

    def writes(self, writes):
        self.set_state(STATE_WRITE)

    def errors(self, errors):
        self.set_state(STATE_ERRROR)

    def info_dict(self):
        info = dict()
        info["loaded"] = self._loaded
        info["connections"] = len(self.connections)
        info["state"] = self.get_state_s()
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

        return Connection(self, socket, address, ssl = ssl)

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
        message = unicode(object) if not object_t in types.StringTypes else object
        self.logger.log(level, message)

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
            ssl_version = ssl.PROTOCOL_TLSv1,
            do_handshake_on_connect = False
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
