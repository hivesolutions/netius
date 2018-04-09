#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
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
from . import util
from . import compat
from . import asynchronous

from .. import middleware

from .conn import * #@UnusedWildImport
from .poll import * #@UnusedWildImport
from .asynchronous import * #@UnusedWildImport

NAME = "netius"
""" The global infra-structure name to be used in the
identification of both the clients and the services this
value may be prefixed or suffixed """

VERSION = "1.17.15"
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

IDENTIFIER_TINY = "%s" % NAME
""" The tiny version of the current environment's identifier
meant to be used in a safe production like environment as it hides
most of the valuable information (able to compromise it) """

IDENTIFIER_SHORT = "%s/%s" % (NAME, VERSION)
""" The short version of the current environment's identifier
meant to be used in production like environment as it hides some
of the critical and internal information of the system """

IDENTIFIER_LONG = "%s/%s (%s)" % (NAME, VERSION, PLATFORM)
""" Longest version of the system identifier, to be used in the
development like environment as it shows critical information
about the system internals that may expose the system """

IDENTIFIER = IDENTIFIER_LONG if config._is_devel() else\
    IDENTIFIER_TINY if config._is_secure() else IDENTIFIER_SHORT
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

SSL_ERROR_CERT_ALREADY_IN_HASH_TABLE = 101
""" Error raised under the SSL infra-structure for situations
where the certificate does not required re-loading as it is
already present in the hash table, this error may be safely
ignored as it does not represent a threat """

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
    ssl.SSL_ERROR_WANT_WRITE,
    SSL_ERROR_CERT_ALREADY_IN_HASH_TABLE
)
""" The list containing the valid errors for the handshake
operation of the SSL connection establishment """

SSL_ERROR_NAMES = {
    ssl.SSL_ERROR_WANT_READ : "SSL_ERROR_WANT_READ",
    ssl.SSL_ERROR_WANT_WRITE : "SSL_ERROR_WANT_WRITE",
    SSL_ERROR_CERT_ALREADY_IN_HASH_TABLE : "SSL_ERROR_CERT_ALREADY_IN_HASH_TABLE"
}
""" The dictionary containing the association between the
various SSL errors and their string representation """

SSL_VALID_REASONS = (
    "CERT_ALREADY_IN_HASH_TABLE",
)
""" The list containing the valid reasons for the handshake
operation of the SSL connection establishment """

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

STATE_PAUSE = 3
""" The pause state set for a service for which the main event
loop has been paused and should be resumed latter """

STATE_CONFIG = 4
""" The configuration state that is set when the service is
preparing to become started and the configuration attributes
are being set according to pre-determined indications """

STATE_POLL = 5
""" State to be used when the service is in the polling part
of the loop, this is the most frequent state in an idle service
as the service "spends" most of its time in it """

STATE_TICK = 6
""" Tick state representative of the situation where the loop
tick operation is being started and all the pre tick handlers
are going to be called for pre-operations """

STATE_READ = 7
""" Read state that is set when the connection are being read
and the on data handlers are being called, this is the part
where all the logic driven by incoming data is being called """

STATE_WRITE = 8
""" The write state that is set on the writing of data to the
connections, this is a pretty "fast" state as no logic is
associated with it """

STATE_ERRROR = 9
""" The error state to be used when the connection is processing
any error state coming from its main select operation and associated
with a certain connection (very rare) """

STATE_STRINGS = (
    "STOP",
    "START",
    "PAUSE",
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

KEEPALIVE_INTERVAL = int(KEEPALIVE_TIMEOUT / 10)
""" The time between the retrying of "ping" packets, this value
does not need to be too large and should not be considered too
important (may be calculated automatically) """

KEEPALIVE_COUNT = 3
""" The amount of times the "ping" packet is re-sent until the
connection is considered to be offline and is dropped """

ALLOW_BLOCK = False
""" The default value for the allow sub-blocking operation, it's
set as not allowed because this is considered to be a dangerous
operation, may create undesired behaviour """

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
""" The format that is going to be used by the logger of the
netius infra-structure for debugging purposes it should allow
and end developer to dig into the details of the execution """

# initializes the various paths that are going to be used for
# the base files configuration in the complete service infra
# structure, these should include the SSL based files
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

    Should handle all the non blocking event loop stuff,
    so that the read and write operations are easy to handle.

    This is considered to be the main event loop code.
    """

    _MAIN = None
    """ Reference to the top level main instance responsible
    for the control of the main thread loop """

    _MAIN_C = None
    """ The compatibility version of the abstract main loop,
    should be used to provide compatibility with protocol and
    transports used by the new API """

    def __init__(self, name = None, handlers = None, *args, **kwargs):
        observer.Observable.__init__(self, *args, **kwargs)
        cls = self.__class__
        poll = cls.test_poll()
        self.name = name or self.__class__.__name__
        self.handler_stream = logging.StreamHandler()
        self.handlers = handlers or (self.handler_stream,)
        self.level = kwargs.get("level", logging.INFO)
        self.diag = kwargs.get("diag", False)
        self.middleware = kwargs.get("middleware", [])
        self.children = kwargs.get("children", 0)
        self.tid = None
        self.tname = None
        self.logger = None
        self.logging = None
        self.npool = None
        self.tpool = None
        self.fpool = None
        self.poll_c = kwargs.get("poll", poll)
        self.poll = self.poll_c()
        self.poll_name = self.poll.name()
        self.poll_timeout = kwargs.get("poll_timeout", POLL_TIMEOUT)
        self.keepalive_timeout = kwargs.get("keepalive_timeout", KEEPALIVE_TIMEOUT)
        self.keepalive_interval = kwargs.get("keepalive_interval", KEEPALIVE_INTERVAL)
        self.keepalive_count = kwargs.get("keepalive_count", KEEPALIVE_COUNT)
        self.allow_block = kwargs.get("allow_block", ALLOW_BLOCK)
        self.poll_owner = True
        self.diag_app = None
        self.middleware_l = []
        self.connections = []
        self.connections_m = {}
        self.callbacks_m = {}
        self._uuid = uuid.uuid4()
        self._compat = compat.CompatLoop(self)
        self._lid = 0
        self._did = 0
        self._main = kwargs.get("_main", False)
        self._slave = kwargs.get("_slave", False)
        self._running = False
        self._pausing = False
        self._loaded = False
        self._forked = False
        self._child = False
        self._childs = []
        self._events = {}
        self._notified = []
        self._delayed = []
        self._delayed_o = []
        self._delayed_n = []
        self._delayed_l = threading.RLock()
        self._extra_handlers = []
        self._expanded = []
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

    @classmethod
    def get_loop(cls, compat = False, asyncio = False):
        loop = cls.get_asyncio() if asyncio else None
        loop = loop or cls.get_main(compat = compat)
        return loop

    @classmethod
    def get_main(cls, compat = False):
        return cls._MAIN_C if compat else cls._MAIN

    @classmethod
    def get_asyncio(cls):
        asyncio = asynchronous.get_asyncio()
        if not asyncio: return None
        policy = asyncio.get_event_loop_policy()
        if not policy._local._loop: return None
        return asyncio.get_event_loop()

    @classmethod
    def set_main(cls, instance, set_compat = True):
        compat = compat_loop(instance)
        cls._MAIN = instance
        cls._MAIN_C = compat
        if not set_compat: return
        asyncio = asynchronous.get_asyncio()
        if not asyncio: return
        cls.patch_asyncio()
        asyncio.set_event_loop(compat)

    @classmethod
    def unset_main(cls, set_compat = True):
        cls.set_main(None, set_compat = set_compat)

    @classmethod
    def patch_asyncio(cls):
        asyncio = asynchronous.get_asyncio()
        if not asyncio: return
        if hasattr(asyncio, "_patched"): return
        if hasattr(asyncio.tasks, "_PyTask"):
            asyncio.Task = asyncio.tasks._PyTask #@UndefinedVariable
            asyncio.tasks.Task = asyncio.tasks._PyTask #@UndefinedVariable
        asyncio._patched = True

    def destroy(self):
        observer.Observable.destroy(self)

        # iterates over the complete set of sockets in the connections
        # map to properly close them (avoids any leak of resources)
        for _socket in self.connections_m: _socket.close()

        # clears some of the internal structure so that they don't
        # get called any longer (as expected)
        self.connections_m.clear()
        self.callbacks_m.clear()

    def call_safe(self, callable, args = [], kwargs = {}):
        """
        Calls the provided callable object using a safe strategy
        meaning that in case there's an exception raised in the
        middle of the callable execution it is going to be caught
        and the details of it logged.

        :type callable: Function
        :param callable: The callable function that is going to
        be called using the safe approach.
        :type args: List
        :param args: The normal (non keyword) arguments to be sent
        to the callable.
        :type kwargs: Dictionary
        :param kwargs: The set of keyword arguments that are going
        to be sent to the callable.
        :rtype: Object
        :return: The result of the calling of the callable.
        """

        try:
            # calls the provided callable (method) with the
            # provided arguments and keyword arguments returning
            # the result to the caller method
            return callable(*args, **kwargs)
        except BaseException as exception:
            # in case there's an exception displays a warning
            # about the raised exception and the logs the current
            # stack so that the exception is traceable
            self.warning(exception)
            self.log_stack()

    def wait_event(self, callable, name = None):
        # tries to retrieve the list of binds for the event
        # to be "waited" for, this list should contain the
        # complete list of callables to be called upon the
        # event notification/trigger
        binds = self._events.get(name, [])
        if callable in binds: return

        # adds the callable to the list of binds for the event
        # the complete set of callables will be called whenever
        # the a notification for the event occurs
        binds.append(callable)
        self._events[name] = binds

    def unwait_event(self, callable, name = None):
        # tries to retrieve the list of binds for the event
        # and verifies that the callable is present on them
        # and if that's not the case ignores the operation
        binds = self._events.get(name, None)
        if not binds or not callable in binds: return

        # removes the callable from the binds list so that
        # it's no longer going to be called
        binds.remove(callable)

        # verifies if the binds list is still valid deleting
        # it from the map of events otherwise
        if binds: self._events[name] = binds
        else: del self._events[name]

    def delay(
        self,
        callable,
        timeout = None,
        immediately = False,
        verify = False,
        safe = False
    ):
        # in case the safe flag is set and the thread trying to add
        # delayed elements is not the main the proper (safe) method
        # is used meaning a safe execution is targeted
        if safe and not self.is_main():
            return self.delay_s(
                callable,
                timeout = timeout,
                immediately = immediately,
                verify = verify
            )

        # creates the original target value with a zero value (forced
        # execution in next tick) in case the timeout value is set the
        # value is incremented to the current time, then created the
        # callable original tuple with the target (time) and the callable
        target = -1 if immediately else 0
        if timeout: target = time.time() + timeout
        callable_o = (target, callable)
        callable_o = legacy.orderable(callable_o)

        # in case the verify flag is set, must verify if the callable
        # is already inserted in the list of delayed operations in
        # case it does returns immediately to avoid duplicated values
        is_duplicate = verify and callable_o in self._delayed_o
        if is_duplicate: return

        # creates the list that is going to be used to populate the
        # options to be used by the calling tuple
        options = [True]

        # creates the "final" callable tuple with the target time, the
        # callable and the loop id (lid) then inserts both the delayed
        # (original) callable tuple and the callable tuple in the lists
        callable_t = (target, self._did, callable, self._lid, options)
        callable_t = legacy.orderable(callable_t)
        heapq.heappush(self._delayed, callable_t)
        heapq.heappush(self._delayed_o, callable_o)

        # increments the "delay" identifier by one, this identifier is
        # used to correctly identify a delayed object so that for the
        # same target value a sorting is performed (fifo like)
        self._did += 1

        # returns the callable tuple that may be latter used to control
        # the execution or not of the delayed operation (cancellation)
        return callable_t

    def delay_s(
        self,
        callable,
        timeout = None,
        immediately = True,
        verify = False,
        wakeup = True
    ):
        """
        Safe version of the delay operation to be used to insert a callable
        from a different thread (implied lock mechanisms).

        This method should only be used from different threads as there's
        a huge performance impact created from using this method instead of
        the local event loop one (delay()).

        :type callable: Function
        :param callable: The callable that should be called on the next tick
        according to the event loop rules.
        :type timeout: int
        :param timeout: The timeout for the callable to be called, this value
        may not reflect an accurate value and depends greatly on the minimum
        resolution value of the polling mechanism.
        :type immediately: bool
        :param immediately: If the callable should be called as soon as possible,
        this is equivalent to setting timeout to -1.
        :type verify: bool
        :param verify: If the delayed sequences should be verified for possible
        duplicated, avoiding possible issues.
        :type wakeup: bool
        :param wakeup: If the main event loop should be awaken so that the
        callable is processed as soon as possible.
        """

        # creates the next element tuple that is going to be scheduled according
        # to the definition provided to the method
        next = (callable, timeout, immediately, verify)

        # acquires the lock that controls the access to the delayed for next
        # tick list and then adds the callable to such list, please note that
        # the delayed (next) list is only going to be joined/merged with delay
        # operations and list on the next tick (through the merge operation)
        self._delayed_l.acquire()
        try: self._delayed_n.append(next)
        finally: self._delayed_l.release()

        # in case the wakeup flag is set this delay operation should have
        # been called from a different thread and the event loop should
        # awaken as soon as possible to handle the event
        if wakeup: self.wakeup()

    def delay_m(self):
        """
        Runs the merge operation so that the delay next list (used by the delay
        safe operation) is merged with the delayed and the delayed ordered
        structures, making the events (effectively) ready to be executed by delays.
        """

        # verifies if the delay next list is not valid or empty and if that's
        # the case returns immediately as there's nothing to be merged
        if not self._delayed_n: return

        # iterates over the complete set of next elements in the delay next list
        # and schedules them as delay for the next tick execution
        for next in self._delayed_n:
            callable, timeout, immediately, verify = next
            self.delay(
                callable,
                timeout = timeout,
                immediately = immediately,
                verify = verify
            )

        # deletes the complete set of elements present in the delay next list, this
        # is considered to be equivalent to the empty operation
        del self._delayed_n[:]

    def ensure(
        self,
        coroutine,
        args = [],
        kwargs = {},
        thread = None,
        future = None,
        immediately = True
    ):
        """
        Main method for the queuing/startup of an asynchronous coroutine
        of async method, this should be called at the most higher level
        of the execution of a chained coroutine sequence.

        It should ensure that the provided callable is wrapped into a
        coroutine if that's the case, so that chained calling is not
        violated by a non compliant element.

        The method should create a proper sequence/pipelined handling of
        the various chained coroutine calls so that they are called one
        after the other using futures for such handling. The final "simple"
        abstraction should expose one "parent" future object as the interface.

        Multiple calls to this method should generate different async
        contexts (with different parent future instances).

        :type coroutine: Coroutine/CoroutineObject/Callable
        :param coroutine: The callable or coroutine that is going to be
        "inserted" for an asynchronous execution, if a callable is provided
        a coroutine is created wrapping the execution of such callable.
        :type args: List
        :param args: The list of "normal" arguments to be sent to the
        coroutine as parts of its signature.
        :type kwargs: Dictionary
        :param kwargs: The keyword arguments to be sent to the coroutine.
        :type thread: bool
        :param thread: If the execution of the coroutine should be done
        using a different thread (via thread pool), this may be interesting
        if the coroutine includes blocking i/o calls.
        :type future: Future
        :param future: If provided ensures that non new future object is going
        to be created for this async context to be created.
        :type immediately: bool
        :param immediately: If the callback should be scheduler in the event
        pool to be executed immediately (as soon as possible).
        :rtype: Future
        :return: The future that has been created for this new async context
        or the provided one if one was provided (this is considered to be the
        parent future of the complete coroutine chain).
        """

        # tries to determine if the provided callable is really
        # a coroutine and uses that condition to determine the
        # default value for the thread argument, notice that the
        # verification is also performed for the coroutine object
        is_coroutine = asynchronous.is_coroutine(coroutine)
        is_coroutine_object = asynchronous.is_coroutine_object(coroutine)
        is_defined = is_coroutine or is_coroutine_object
        if thread == None: thread = False if is_defined else True

        # verifies if a future variable is meant to be re-used
        # or if instead a new one should be created for the new
        # ensure execution operation
        future = future or self.build_future()

        # in case the provided coroutine callable is not really
        # a coroutine and instead a "normal" function a conversion
        # is required so that there's compatibility between the
        # coroutine model and the typical sync model
        if not is_defined:
            # saves the "original" callable so that it may be latter
            # used as part of the back calling process
            coroutine_c = coroutine

            # creates the coroutine that is going to be used to
            # encapsulate the callable, note that the result of the
            # callable is set as the result of the future (as expected)
            def coroutine(future, *args, **kwargs):
                yield
                result = coroutine_c(*args, **kwargs)
                future.set_result(result)

        # creates the function that is going to "propagate" the cancel
        # operation from the "parent" future to the child one, this
        # should also close the associated generator
        def cleanup(future):
            if not future.cancelled(): return
            if not hasattr(future, "child"): return
            if not future.child: return
            future.child.cancel()

        # adds the cleanup function as a done callback so that whenever
        # the future is canceled a child future is also canceled, this
        # propagation of operations allows for proper cleanup
        future.add_done_callback(cleanup)

        # verifies if the currently provided coroutine is in fact (already)
        # a coroutine object, if that's the case the sequence (generator)
        # is already present and the coroutine is simply assigned to the
        # sequence without any kind of conversion
        if is_coroutine_object:
            sequence = coroutine

        # otherwise the sequence must be created by calling the coroutine
        # (function) with the proper set of arguments, notice that the signature
        # is inspected to determine if a future argument is required
        else:
            # retrieves the argument spec of the provided coroutine to check
            # if the provided coroutine requires a future to be passed
            spec = legacy.getargspec(coroutine)
            is_future = spec[0] and spec[0][0] == "future"

            # creates the generate sequence from the coroutine callable
            # by calling it with the newly created future instance, that
            # will be used for the control of the execution, notice that
            # the future is only passed in case the coroutine has been
            # determined to be receiving the future as first argument
            if is_future: sequence = coroutine(future, *args, **kwargs)
            else: sequence = coroutine(*args, **kwargs)

        # calls the ensure generator method so that the provided sequence
        # gets properly "normalized" into the expected generator structure
        # in case the normalization is not possible a proper exception is
        # raised indicating the "critical" problem
        is_generator, sequence = asynchronous.ensure_generator(sequence)
        if not is_generator: raise errors.AssertionError("Expected generator")

        # creates the callable that is going to be used to call
        # the coroutine with the proper future variable as argument
        # note that in case the thread mode execution is enabled the
        # callable is going to be executed on a different thread
        if thread: callable = lambda f = future: self.texecute(step, [f])
        else: callable = lambda f = future: step(f)

        # creates the function that will be used to step through the
        # various elements in the sequence created from the calling of
        # the coroutine, the values returned from it may be either future
        # or concrete values, for each situation a proper operation must
        # be applied to complete the final task in the proper way
        def step(_future):
            # unsets any possible reference to a child element as it must
            # have been processed if the control flow reached this point,
            # this avoids duplicated approval of child futures
            future.child = None

            # iterates continuously over the generator that may emit both
            # plain object values or future (delayed executions)
            while True:
                # in case the future object is considered to be closed,
                # (done using a pipeline of callbacks) no more steps are
                # going to be taken and the sequence should be closed as
                # it's not longer going to be used (for sure), this means
                # that the blocked coroutine is not going to be resumed
                if future.closed:
                    sequence.close()
                    future.cancel()
                    break

                # determines if the future is ready to receive new work
                # this is done using a pipeline of callbacks that must
                # deliver a positive value so that the future is considered
                # ready, note that in case the future is not ready the current
                # iteration cycle is delayed until the next tick
                if not future.ready:
                    self.delay(callable)
                    break

                # in case the finished future has been canceled propagates
                # such cancellation to the parent future
                if _future.cancelled():
                    future.cancel()
                    break

                # in case there's an exception in the future that has just
                # been executed propagates such exception to the parent future
                if _future.exception():
                    future.set_exception(_future.exception())
                    break

                # retrieves the next value from the generator and in case
                # value is the last one (stop iteration) verifies if the
                # is still considered running (no value or exception) set and
                # if that's the case runs the default value set (approve)
                # and then breaks the loop, notice that if there's an
                # exception raised in the middle of the generator iteration
                # it's set on the future (indirect notification)
                try: value = next(sequence)
                except StopIteration as exception:
                    result = exception.args[0] if exception.args else None
                    if future.running(): future.set_result(result)
                    break
                except BaseException as exception:
                    future.set_exception(exception)
                    break

                # determines if the value retrieved from the generator is a
                # future and if that's the case schedules a proper execution
                is_future = asynchronous.is_future(value)

                # in case the current value is a future schedules it for execution
                # taking into account the proper thread execution model, note that
                # the future is set as a child of the current "parent" future
                if is_future:
                    future.child = value
                    value.add_done_callback(callable)
                    break

                # otherwise it's a normal value being yielded and should be sent
                # to the future object as a partial value (pipelining)
                else:
                    # for a situation where a thread pool should be used the new
                    # value should be "consumed" by adding the data handler operation
                    # to the list of delayed operations and notifying the task pool
                    # so that the event loop on the main thread gets unblocked and
                    # the proper partial value handling is performed (always on main thread)
                    if thread:
                        def handler():
                            future.partial(value)
                            callable()

                        self.delay_s(handler)
                        break

                    # otherwise we're already on the main thread so a simple partial callback
                    # notification should be enough for the proper consuming of the data
                    else:
                        future.partial(value)

        # delays the execution of the callable so that it is executed
        # immediately if possible (event on the same iteration)
        self.delay(callable, immediately = immediately)
        return future

    def resolve_hostname(self, hostname, type = "a"):
        """
        Resolve the provided hostname according to the provided type
        resolution. The resolution process itself is asynchronous and
        implementation independent, returning a future for the control
        of the execution.

        :type hostname: String
        :param hostname: The name of the host to be resolved.
        :type type: String
        :param type: The type of resolutions to be used (eg: a, aaaa, mx, etc.)
        :rtype: Future
        :return: The future to be used in the operation execution.
        """

        import netius.clients

        future = self.build_future()

        def handler(response):
            if not response:
                raise errors.RuntimeError("Timeout in resolution")
            if not response.answers:
                raise errors.RuntimeError("Unable to resolve name")

            answer = response.answers[0]
            address = answer[4]

            future.set_result(address)

        netius.clients.DNSClient.query_s(
            hostname,
            type = type,
            callback = handler
        )

        return future

    def run_forever(self):
        # starts the current event loop, this is a blocking operation until
        # the the stop method is called to unblock the loop
        self.forever(env = False)

    def run_coroutine(
        self,
        coroutine,
        args = [],
        kwargs = {},
        thread = None,
        close = None
    ):
        # creates the callback function that is going to be called when
        # the future associated with the provided ensure context gets
        # finished (on done callback)
        def cleanup(future):
            # calls the stop or pause method for the current loop, effectively
            # ending the loop as soon as possible (next tick), notice that if
            # the close method is called no more loop re-usage is possible
            self.stop() if close else self.pause()

        # tries to determine if the provided object is in fact a coroutine
        # or if instead it is a "simple" future object ready to be used
        is_future = asynchronous.is_future(coroutine)
        is_coroutine = not is_future

        # ensures that the provided coroutine get executed under a new
        # context and retrieves the resulting future
        future = self.ensure(
            coroutine,
            args = args,
            kwargs = kwargs,
            thread = thread
        ) if is_coroutine else coroutine

        # defines the cleanup operation (loop stop) as the target for the
        # done operation on the future (allows cleanup)
        future.add_done_callback(cleanup)

        # starts the current event loop, this is a blocking operation until
        # the done callback is called to stop the loop
        self.start()

        # tries to retrieve a possible exception associated with
        # the future, in case it does not exist ignores the current
        # execution and returns the control flow immediately with
        # the future's result, to be used by the caller
        exception = future.exception()
        if not exception: return future.result()

        # raises the exception to the upper layers so that it's properly
        # handled by them, this is the expected behaviour by this sync
        # execution mode of the coroutine inside an event loop
        raise exception

    def wakeup(self, force = False):
        # verifies if this is the main thread and if that's not the case
        # and the force flag is not set ignore the wakeup operation, avoiding
        # extra usage of resources (not required)
        if self.is_main() and not force: return

        # makes sure that the the notify pool is started (required for proper
        # event notification) and then runs the notification process, should
        # "wake" the main event loop as soon as possible
        if force: self.nensure()
        if not self.npool: return
        self.npool.notify()

    def sleep(self, timeout, future = None):
        # verifies if a future variable is meant to be re-used
        # or if instead a new one should be created for the new
        # sleep operation to be executed
        future = future or self.build_future()

        # creates the callable that is going to be used to set
        # the final value of the future variable
        callable = lambda: future.set_result(timeout)

        # delays the execution of the callable so that it is executed
        # after the requested amount of timeout, note that the resolution
        # of the event loop will condition the precision of the timeout
        self.delay(callable, timeout = timeout)
        return future

    def wait(self, event, timeout = None, future = None):
        # verifies if a future variable is meant to be re-used
        # or if instead a new one should be created for the new
        # sleep operation to be executed
        future = future or self.build_future()

        # creates the callable that is going to be used to set
        # the final value of the future variable, the result
        # set in the future represents the payload of the event
        def callable(data):
            if future.cancelled(): return
            future.set_result(data)

        # creates the callable that is going to be called in case
        # the timeout has been reached, this avoids constant waiting
        # for an event to happen (dead lock)
        def canceler():
            if future.done(): return
            future.cancel()

        # creates the callback function that is going to be called
        # whenever the future is completed (either error or success)
        # this should run the series of cleanup operations
        def cleanup(future):
            self.unwait_event(callable, name = event)

        # registers the cleanup function for the done operation so that
        # the waiting for the event is canceled whenever the future is
        # completed with either success or error
        future.add_done_callback(cleanup)

        # waits the execution of the callable until the event with the
        # provided name is notified/triggered, the execution should be
        # triggered on the same event loop tick as the notification
        self.wait_event(callable, name = event)

        # in case a valid timeout is set schedules the canceler operation
        # to be performed (to unblock the waiting element)
        if timeout: self.delay(canceler, timeout = timeout)

        # returns the provided future or a new one in case none has been
        # provided, this will be used for proper event registration
        return future

    def notify(self, event, data = None):
        # adds the event with the provided name to the list of notifications
        # that are going to be processed in the current tick operation
        self._notified.append((event, data))

        # in case this is considered to be the main thread there no need to
        # proceed with the task pool notification process (expensive)
        if self.is_main(): return

        # runs the wakeup operation making sure that as soon as possible the
        # main event loop gets unblocked for event processing
        self.wakeup()

    def load(self, full = False):
        """
        Starts the loading process for the current engine, this should be
        a singleton (run once) operation to be executed once per instance.

        Some of the responsibilities of the loading process should include:
        logging loading, system signal binding and welcome message printing.

        The method should be protected against double execution issues, meaning
        that should be safely called at any stage of the life cycle.

        :type full: bool
        :param full: If the loading process should be performed completely,
        meaning that even the long tasks should be executed.
        """

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

        # loads the complete set of middleware that has been registered for
        # the current system (takes into account if it's considered the main one)
        self.load_middleware()

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

    def unload(self, full = True):
        """
        Unloads the structures associated with the current engine, so that
        the state of the current engine is reversed to the original one.

        Note that this is not related in any way with the event loop and only
        static structures are affected.

        After a call to this method, the load method may be called again.

        :type full: bool
        :param full: If the complete set of structure unloading operations
        should be performed, this is related with the full flag of load.
        """

        # verifies if the current structure is considered/marked as already
        # "unloaded", if that's the case returns the control flow immediately
        # as there's nothing pending to be (undone)
        if not self._loaded: return

        # triggers the operation that will start the unloading process of the
        # logging infra-structure of the current system
        if full: self.unload_logging()

        # unloads the middleware infra-structure that has been created for the
        # current service, no longer going to be used
        self.unload_middleware()

        # marks the current system as unloaded as the complete set of operations
        # meant to start the unloading process have been finished
        self._loaded = False

    def boot(self):
        pass

    def welcome(self):
        pass

    def load_logging(self, level = logging.DEBUG, format = LOG_FORMAT, unique = False):
        # verifies if there's a logger already set in the current service
        # if that's the case ignores the call no double reloading allowed
        if self.logger: return

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

    def unload_logging(self, safe = True):
        # verifies if there's a valid logger instance set in the
        # current service, in case there's not returns immediately
        # as there's nothing remaining to be done here
        if not self.logger: return

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

        # in case the safe flag is set, iterates over the complete
        # set of handlers registered for the logger and removes them
        # from the current logger, this is required so that proper
        # handler unregistration is ensured even for complex scenarios
        for handler in self.logger.handlers if safe else ():
            if not handler: continue
            self.logger.removeHandler(handler)

        # closes the base stream handler as it's no longer going to
        # be used for any kind of logging operation (avoids leaks)
        self.handler_stream.close()

        # iterates over the complete set of (built) extra handlers
        # and runs the close operation for each of them, as they are
        # no longer considered required for logging purposes
        for handler in self._extra_handlers: handler.close()

        # unset the logger reference in the current service so that
        # it's not possible to use it any longer
        self.logger = None

    def extra_logging(self, level, formatter):
        """
        Loads the complete set of logging handlers defined in the
        current logging value, should be a map of definitions.

        This handlers will latter be used for piping the various
        logging messages to certain output channels.

        The creation of the handler is done using a special keyword
        arguments strategy so that python and configuration files
        are properly set as compatible.

        :type level: String/int
        :param level: The base severity level for which the new handler
        will be configured in case no extra level definition is set.
        :type formatter: Formatter
        :param formatter: The logging formatter instance to be set in
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

        :type level: int/String
        :param level: The (logging) for which the logging infra-structure
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
        # this must be performed locally no avoid any unwanted behavior
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
        # used for serving the diagnostics app
        self.diag_app = diag.DiagApp(self)

        # calls the on diag method so that the current instance is
        # able to act on the newly created application
        self.on_diag()

        # starts the "serving" procedure of it under a new thread
        # to avoid blocking the current context of execution
        self.diag_app.serve(
            server = server,
            host = host,
            port = port,
            diag = False,
            threaded = True,
            conf = False
        )

    def load_middleware(self, suffix = "Middleware"):
        # iterates over the complete set of string that define the middleware
        # that is going to be loaded and executes the loading process
        for name in self.middleware:
            # capitalizes the provided name and appends the suffix to it
            # to created the proper (and complete) middleware class name
            name_c = name.capitalize()
            class_n = name_c + suffix

            # retrieves the class (from the middleware module) that is going
            # to be used for the current middleware
            middleware_c = getattr(middleware, class_n)

            # runs the registration process for the middleware, meaning that
            # the class is going to be instantiated and started and the proper
            # internal structures will be updated in accordance
            self.register_middleware(middleware_c)

    def unload_middleware(self):
        # iterates over the complete set of middleware instance to stop
        # them (close internal structures) and then removes the middleware
        # list so that they don't get used any longer
        for middleware_i in self.middleware_l: middleware_i.stop()
        del self.middleware_l[:]

    def register_middleware(self, middleware_c):
        # instantiates a new middleware class as a new instance and then
        # runs the start method indicating the intention to start a new
        # middleware (should properly start its internal structures)
        middleware_i = middleware_c(self)
        middleware_i.start()

        # adds the middleware instance that has just been created to the
        # list of middleware loaded for the current service
        self.middleware_l.append(middleware_i)

        # returns the instance of middleware that has just been created
        # while running the registration process
        return middleware_i

    def call_middleware(self, name, *args, **kwargs):
        # iterates over the complete set of middleware instance to call the
        # method with the provided name, with the provided arguments
        for middleware_i in self.middleware_l:
            method = getattr(middleware_i, name)
            method(*args, **kwargs)

    def bind_signals(
        self,
        signals = (
            signal.SIGINT,
            signal.SIGTERM,
            signal.SIGHUP if hasattr(signal, "SIGHUP") else None, #@UndefinedVariable
            signal.SIGQUIT if hasattr(signal, "SIGQUIT") else None #@UndefinedVariable
        ),
        handler = None
    ):
        # creates the signal handler function that propagates the raising
        # of the system exit exception (proper logic is executed) and then
        # registers such handler for the (typical) sigterm signal
        def base_handler(signum = None, frame = None): raise SystemExit()
        for signum in signals:
            if signum == None: continue
            try: signal.signal(signum, handler or base_handler)
            except: self.debug("Failed to register %d handler" % signum)

    def bind_env(self):
        """
        Binds the current environment values to the current instance.
        This method has a global behaviour on the current event loop.
        """

        self.level = self.get_env("LEVEL", self.level)
        self.diag = self.get_env("DIAG", self.diag, cast = bool)
        self.middleware = self.get_env("MIDDLEWARE", self.middleware, cast = list)
        self.children = self.get_env("CHILD", self.children, cast = int)
        self.children = self.get_env("CHILDREN", self.children, cast = int)
        self.logging = self.get_env("LOGGING", self.logging)
        self.poll_name = self.get_env("POLL", self.poll_name)

    def forever(self, env = True):
        if env: self.bind_env()
        return self.start()

    def start(self):
        # in case the current instance is currently paused runs the
        # resume operation instead as that's the expected operation
        if self.is_paused(): return self.resume()

        # in case the event loop is already running then a new sub-
        # context based loop should be created in order to block the
        # current execution stack (as expected)
        if self.is_running(): return self.block()

        # re-builds the polling structure with the new name this
        # is required so that it's possible to change the polling
        # mechanism in the middle of the loading process
        self.poll = self.build_poll()

        # retrieves the name of the polling mechanism that is
        # going to be used in the main loop of the current
        # base service, this is going to be used for diagnostics
        poll_name = self.get_poll_name()

        # triggers the loading of the internal structures of
        # the base structure in case the loading has already
        # been done nothing is done (avoids duplicated load)
        self.load()

        # opens the polling mechanism so that its internal structures
        # become ready for the polling cycle, the inverse operation
        # (close) should be performed as part of the cleanup
        self.poll.open(timeout = self.poll_timeout)

        # makes sure that the notify pool is created so that the event
        # notification (required for multi threaded environments) is created
        # and ready to be used (as expected)
        self.nensure()

        # retrieves the complete set of information regarding the current
        # thread that is being used for the starting of the loop, this data
        # may be used for runtime debugging purposes (debug only data)
        cthread = threading.current_thread()
        self.tid = cthread.ident or 0
        self.tname = cthread.getName()
        self._main = self.tname == "MainThread"

        # in case the current thread is the main one, the global main instance
        # is set as the current instance, just in case no main variable is
        # already set otherwise corruption may occur (override of value)
        if self._main and not self._slave and not Base.get_main():
            Base.set_main(self)

        # enters the main loop operation by printing a message
        # to the logger indicating this start, this stage
        # should block the thread until a stop call is made
        self.debug("Starting '%s' service main loop (%.2fs) ..." % (self.name, self.poll_timeout))
        self.debug("Using thread '%s' with tid '%d'" % (self.tname, self.tid))
        self.debug("Using '%s' as polling mechanism" % poll_name)

        # calls the main method to be able to start the main event
        # loop properly as defined by specification
        self.main()

    def stop(self):
        if self.is_paused(): self.finish()
        else: self._running = False

    def pause(self):
        self._running = False
        self._pausing = True

    def resume(self):
        self.debug("Resuming '%s' service main loop (%.2fs) ..." % (self.name, self.poll_timeout))
        self.on_resume()
        self.main()

    def close(self):
        self.stop()

    def finish(self):
        self.debug("Finishing '%s' service main loop" % self.name)
        self.on_stop()
        self.cleanup()
        self.set_state(STATE_STOP)

    def main(self):
        # sets the running flag that controls the running of the
        # main loop and then changes the current state to start
        # as the main loop is going to start, then executes the
        # on start call indicating the (re-)start of the even loop
        self._running = True
        self._pausing = False
        self.set_state(STATE_START)
        self.on_start()

        # runs the event loop, this is a blocking method that should
        # be finished by the end of the execution of by pause
        try:
            self.loop()
            self.finalize()
        except (KeyboardInterrupt, SystemExit, errors.StopError):
            self.info("Finishing '%s' service on user request ..." % self.name)
        except errors.PauseError:
            self.debug("Pausing '%s' service main loop" % self.name)
            self.set_state(STATE_PAUSE)
            self.on_pause()
        except BaseException as exception:
            self.error(exception)
            self.log_stack(method = self.warning)
        except:
            self.critical("Critical level loop exception raised")
            self.log_stack(method = self.error)
        finally:
            if self.is_paused(): return
            self.finish()

    def is_main(self):
        if not self.tid: return True
        return threading.current_thread().ident == self.tid

    def is_running(self):
        return self._running

    def is_started(self):
        return self.get_state() == STATE_START

    def is_stopped(self):
        return self.get_state() == STATE_STOP

    def is_paused(self):
        return self.get_state() == STATE_PAUSE

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

    def cleanup(self, destroy = True):
        # runs the unload operation for the current base container this should
        # unset/unload some of the components for this base infra-structure
        self.unload()

        # destroys the complete set of structures associated with the event
        # notification, this should include both the map of events to binds
        # association and the list of pending notifications to be processed
        self._events.clear()
        del self._notified[:]

        # destroys the current information on the delays that are is longer
        # going to be executed as the poll/system is closing, this is required
        # in order to avoid any possible memory leak with clojures/cycles
        del self._delayed[:]
        del self._delayed_o[:]
        del self._delayed_n[:]

        # runs the expand destroy operation so that the complete set of expanded
        # values get their (temporary) files removed (garbage collection)
        self._expand_destroy()

        # runs the destroy operation on the SSL component of the base
        # element so that no more SSL is available/used (avoids leaks)
        self._ssl_destroy()

        # verifies if there's a valid (and open) notify pool, if that's
        # the case starts the stop process for it so that there's no
        # leaking of task descriptors and other structures
        if self.npool: self.nstop()

        # verifies if there's a valid (and open) task pool, if that's
        # the case starts the stop process for it so that there's no
        # leaking of task descriptors and other structures
        if self.tpool: self.tstop()

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

        # in case the current thread is the main one then in case the
        # instance set as global main is this one unsets the value
        # meaning that the main instance has been unloaded
        if self._main and not self._slave and Base.get_main() == self:
            Base.unset_main()

        # closes the current poll mechanism so that no more issues arise
        # from an open poll system (memory leaks, etc.), note that this is
        # only performed in case the current base instance is the owner of
        # the poll that is going to be closed (works with containers)
        if self.poll_owner: self.poll.close()

        # deletes some of the internal data structures created for the instance
        # and that are considered as they are considered to be no longer required
        self.connections_m.clear()
        self.callbacks_m.clear()
        del self.connections[:]
        del self._extra_handlers[:]

        # runs the destroy operation for the current instance, this should remove
        # the most obscure parts of the current instance
        if destroy: self.destroy()

    def loop(self):
        # iterates continuously while the running flag is set, once
        # it becomes unset the loop breaks at the next execution cycle
        while True:
            # calls the base tick int handler indicating that a new
            # tick loop iteration is going to be started, all the
            # "in between loop" operation should be performed in this
            # callback as this is the "space" they have for execution
            self.ticks()

            # in case running flag is disabled it's time to break the
            # cycle (just before the possible block) as it would imply
            # extra time before we could stop the event loop
            if not self._running: break

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

    def block(self):
        """
        Runs the sub-blocking operation, by "forking" the current loop
        execution into an inner one for a new context.

        The execution of this method is not recommended and should be
        used with extreme care to avoid unwanted behaviour.
        """

        # in case blocking (sub starting) operation is not allowed
        # for the current event loop raises an exception
        if not self.allow_block:
            raise errors.RuntimeError("Blocking is not allowed")

        # saves the current running state and then runs the loop again
        # restoring the same state at the end of the execution
        _running = self._running
        try: self.loop()
        finally: self._running = _running

    def fork(self):
        # ensures that the children value is converted as an
        # integer value as this is the expected structure
        self.children = int(self.children)

        # runs a series of validations to be able to verify
        # if the fork operation should really be performed
        if not self.children: return True
        if not self.children > 0: return True
        if not hasattr(os, "fork"): return True
        if self._forked: return True

        # prints a debug operation about the operation that is
        # going to be performed for the forking
        self.debug("Forking the current process into '%d' children ..." % self.children)

        # calls the on fork method indicating that a new fork
        # operation is soon going to be performed
        self.on_fork()

        # sets the initial pid value to the value of the current
        # master process as this is going to be used for child
        # detection (critical for the correct logic execution)
        pid = os.getpid()

        # iterates of the requested (number of children) to run
        # the concrete fork operation and fork the logic
        for _index in range(self.children):
            pid = os.fork() #@UndefinedVariable
            self._child = pid == 0
            if self._child: self.on_child()
            if self._child: break
            self._childs.append(pid)

        # sets the forked flag, meaning that the current process
        # has been already forked (avoid duplicated operations)
        self._forked = True

        # in case the current process is a child one an immediate
        # valid value should be returned (force logic continuation)
        if self._child: return True

        # registers for some of the common signals to be able to avoid
        # any possible interaction with the joining process
        def handler(signum = None, frame = None): raise errors.StopError("Stop")
        self.bind_signals(handler = handler)

        # sleeps forever, waiting for an interruption of the current
        # process that triggers the children to quit, so that it's
        # able to "join" all of them into the current process
        try: self._wait_forever()
        except: pass

        # prints a debug information about the processes to be joined
        # this indicated the start of the joining process
        self.debug("Joining '%d' children processes ..." % self.children)

        # iterates over the complete set of children to send the proper
        # terminate signal to each of them for proper termination
        for pid in self._childs: os.kill(pid, signal.SIGTERM) #@UndefinedVariable

        # iterates over the complete set of child processed to join
        # them (master responsibility)
        for pid in self._childs: os.waitpid(pid, 0)

        # prints a message about the end of the child process joining
        # this is relevant to make sure everything is ok before exit
        self.debug("Finished joining %d' children processes" % self.children)

        # runs the cleanup operation for the current process this is
        # required to avoid any leaked information
        self.cleanup()

        # returns an invalid value meaning that no control flow should
        # continue, as this is the master process (coordinator)
        return False

    def finalize(self):
        # verifies a series of conditions and raises a proper error in case
        # any of them is verified under the current state
        if self._pausing: raise errors.PauseError("Pause state expected")
        if self._running: raise errors.AssertionError("Not expected running")

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
        for read in reads: self.on_read(read)

    def writes(self, writes, state = True):
        if state: self.set_state(STATE_WRITE)
        for write in writes: self.on_write(write)

    def errors(self, errors, state = True):
        if state: self.set_state(STATE_ERRROR)
        for error in errors: self.on_error(error)

    def datagram(
        self,
        family = socket.AF_INET,
        type = socket.SOCK_DGRAM,
        remote_host = None,
        remote_port = None,
        callback = None
    ):
        """
        Builds a datagram based connection for the provided family and
        type of socket, receiving an optional callback parameter to
        be called once the "connection" object is ready to be used.

        :type family: int
        :param family: The kind of socket family that is going to be
        used in the creation of the datagram "connection".
        :type type: int
        :param type: Socket type (datagram, stream, etc.) to be used
        for the creation of the datagram connection, in principle should
        not be changed from the default value.
        :type remote_host: String
        :param remote_host: The remote host to be used in a possible connect
        (bind) operation in the datagram so that the default send operation
        does not require explicit host setting.
        :type remote_port: String
        :param remote_port: The remote port to be used in a possible connect
        (bind) operation in the datagram so that the default send operation
        does not require explicit port setting.
        :type callback: Function
        :param callback: Callback function to be called once the datagram
        connection is considered to be ready.
        :rtype: Connection
        :return: The datagram based connection that encapsulates the datagram
        based connection logic.
        """

        # creates the socket that it's going to be used for the listening
        # of new connections (client socket) and sets it as non blocking
        _socket = socket.socket(family, type)
        _socket.setblocking(0)

        # sets the various options in the service socket so that it becomes
        # ready for the operation with the highest possible performance
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # verifies if both the host and the port are set and if that's the
        # case runs the connect (send bind) operation in the datagram socket
        # notice that this is not a "real" remote connection
        if remote_host and remote_port: _socket.connect((remote_host, remote_port))

        # creates a new connection object representing the datagram socket
        # that has just been created to be used for upper level operations
        # and then immediately sets it as connected
        connection = self.new_connection(_socket, datagram = True)
        connection.open()
        connection.set_connected()

        # in case a callback is defined schedules its execution for the next
        # tick to avoid possible issues with same tick registration
        if callback: self.delay(lambda: callback(connection, True), immediately = True)

        # returns the connection to the caller method so that it may be used
        # for operation from now on (latter usage)
        return connection

    def connect(
        self,
        host,
        port,
        receive_buffer = None,
        send_buffer = None,
        ssl = False,
        key_file = None,
        cer_file = None,
        ca_file = None,
        ca_root = True,
        ssl_verify = False,
        family = socket.AF_INET,
        type = socket.SOCK_STREAM,
        callback = None,
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

        # runs a series of default operation for the SSL related attributes
        # that are going to be used in the socket creation and wrapping
        key_file = key_file or SSL_KEY_PATH
        cer_file = cer_file or SSL_CER_PATH
        ca_file = ca_file or SSL_CA_PATH

        # determines if the SSL verify flag value is valid taking into account
        # the provided value and defaulting to false value if not valid
        ssl_verify = ssl_verify or False

        # creates the client socket value using the provided family and socket
        # type values and then sets it immediately as non blocking
        _socket = socket.socket(family, type)
        _socket.setblocking(0)

        # in case the SSL option is enabled the socket should be wrapped into
        # a proper SSL socket interface so that it may be operated accordingly
        if ssl: _socket = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            server = False,
            ssl_verify = ssl_verify,
            server_hostname = host
        )

        # sets a series of options in the socket to ensure that it's
        # prepared for the client operations to be performed
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if is_inet: _socket.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
        if receive_buffer: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            receive_buffer
        )
        if send_buffer: _socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            send_buffer
        )
        self._socket_keepalive(_socket)

        # constructs the address tuple taking into account if the
        # socket is unix based or if instead it represents a "normal"
        # one and the host and port must be used instead
        address = port if is_unix else (host, port)

        # creates the connection object using the typical constructor
        # and then sets the SSL host (for verification) if the verify
        # SSL option is defined (secured and verified connection)
        connection = self.new_connection(_socket, address, ssl = ssl)
        if ssl_verify: connection.ssl_host = host

        # schedules the underlying non blocking connect operation to
        # be executed as soon as possible to start the process of
        # connecting for the current connection
        self.delay(
            lambda: self._connect(connection),
            immediately = True
        )

        def on_close(conection):
            callback and callback(connection, False)

        def on_connect(conection):
            connection.unbind("close", on_close)
            callback and callback(connection, True)

        # in case there's a callback defined for the connection establishment
        # then registers such callback for the connect event in the connection
        if callback: connection.bind("connect", on_connect, oneshot = True)
        if callback: connection.bind("close", on_close, oneshot = True)

        # returns the "final" connection, that is now scheduled for connect
        # to the caller method, it may now be used for operations
        return connection

    def acquire(self, connection):
        acquire = lambda: self.on_acquire(connection)
        self.delay(acquire)

    def pregister(self, pool):
        # prints a debug message stating that a new pool is
        # being created for the handling of message events
        self.debug("Started pool, for async handling")

        # tries to retrieve the file descriptor of the event virtual
        # object that is notified for each operation associated with
        # the pool, (primary communication mechanism)
        eventfd = pool.eventfd()
        if not eventfd: self.warning("Starting pool without eventfd")
        if not eventfd: return
        if not self.poll: return
        self.sub_read(eventfd)

        # creates the callback clojure around the current context
        # so that a proper callback can be used for the operations
        pool._callback = lambda e, s: self.pcallback(e, s, pool)

        # registers for a callback operation in the event fd so that
        # it gets properly de-notified as expected when a read operation
        # is performed in it, this operations will be performed upon
        # the request for the read operation
        self.add_callback(eventfd, pool._callback)

        # retrieves the class of the eventfd object and then uses it
        # to retrieve the associated name for logging purposes
        eventfd_cls = eventfd.__class__
        eventfd_name = eventfd_cls.__name__

        # echoes a debug message indicating that a new read event
        # subscription has been created for the event fd of the pool
        self.debug("Subscribed for read operations on event fd (%s)" % eventfd_name)

    def punregister(self, pool):
        # prints a debug message notifying the user that no more
        # async handling is possible using the pool
        self.debug("Stopped existing pool, no more async handling")

        # tries to retrieve the event file descriptor for
        # the pool an in case it exists unsubscribes
        # from it under the current polling system
        eventfd = pool.eventfd()
        if not eventfd: self.warning("Stopping pool without eventfd")
        if not eventfd: return
        if not self.poll: return
        self.unsub_read(eventfd)

        # verifies if the callback operation in the event fd is defined
        # for the pool and if that's not the case returns immediately
        if not hasattr(pool, "_callback"): return

        # unregisters from a callback operation in the event fd so that
        # no more events are handled by the notifier, this is expected
        # in order to avoid any leaks
        self.remove_callback(eventfd, pool._callback)

        # unsets the value of the callback removing its reference from
        # the pool as its no longer going to be used
        del pool._callback

        # echoes a debug message indicating that a new read event
        # unsubscription has been created for the event fd of the pool
        self.debug("Unsubscribed for read operations on event fd")

    def pcallback(self, event, socket, pool):
        # runs a series of pre-validations on the callback so that
        # no operations is performed for such conditions
        if not pool: return
        if not event == "read": return

        # runs the de-notify operation clearing the pool from any
        # possible extra notification (avoid extra counter)
        pool.denotify()

    def nensure(self):
        if self.npool: return
        self.nstart()

    def nstart(self):
        if self.npool: return
        self.npool = netius.pool.NotifyPool()
        self.npool.start()
        self.pregister(self.npool)

    def nstop(self):
        if not self.npool: return
        self.punregister(self.npool)
        self.npool.stop()

    def tensure(self):
        if self.tpool: return
        self.tstart()

    def tstart(self):
        if self.tpool: return
        self.tpool = netius.pool.TaskPool()
        self.tpool.start()
        self.pregister(self.tpool)

    def tstop(self):
        if not self.tpool: return
        self.punregister(self.tpool)
        self.tpool.stop()

    def texecute(self, callable, args = [], kwargs = {}, callback = None):
        self.tensure()
        self.tpool.execute(
            callable,
            args = args,
            kwargs = kwargs,
            callback = callback
        )

    def files(self):
        if not self.fpool: return
        events = self.fpool.pop_all()
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
        self.pregister(self.fpool)

    def fstop(self):
        # verifies if there's an available file pool and
        # if that's the case initializes the stopping of
        # such system, note that this is blocking call as
        # all of the thread will be joined under it
        if not self.fpool: return
        self.punregister(self.fpool)
        self.fpool.stop()

    def on_connection_c(self, connection):
        # prints some debug information about the connection that has
        # just been created (for possible debugging purposes)
        self.debug(
            "Connection '%s' from '%s' created" %
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are %d connections for '%s'" %
            (len(connection.owner.connections), connection.owner.name)
        )

        # triggers the event notifying any listener about the new connection
        # that is now ready for operation to be performed in it
        self.trigger("connection_c", self, connection)

    def on_connection_d(self, connection):
        # prints some debug information about the connection
        # that has just been scheduled for destruction
        self.debug(
            "Connection '%s' from '%s' deleted" %
            (connection.id, connection.owner.name)
        )
        self.debug(
            "There are %d connections for '%s'" %
            (len(connection.owner.connections), connection.owner.name)
        )

        # triggers the event notifying any listener about the
        # deletion/destruction f the connection
        self.trigger("connection_d", self, connection)

    def on_stream_c(self, stream):
        # retrieves the reference to the connection that is associated
        # with the stream that has been created
        connection = stream.connection

        # prints some debug information on the stream that has just been
        # created (may be used for debugging purposes)
        self.debug(
            "Stream '%s' from '%s' created" %
            (stream.identifier, connection.owner.name)
        )

        # notifies any listener of the stream created event about the
        # new stream (as expected per specification)
        self.trigger("stream_c", self, stream)

    def on_stream_d(self, stream):
        # retrieves the reference to the connection that is associated
        # with the stream that has been deleted
        connection = stream.connection

        # prints some debug information on the stream that has just been
        # deleted (may be used for debugging purposes)
        self.debug(
            "Stream '%s' from '%s' deleted" %
            (stream.identifier, connection.owner.name)
        )

        # notifies any listener of the stream deleted event about the
        # new stream (as expected per specification
        self.trigger("stream_d", self, stream)

    def on_fork(self):
        self.trigger("fork", self)

    def on_child(self):
        # triggers the child event indicating that a new child has been
        # created and than any callback operation may now be performed
        self.trigger("child", self)

        # creates a new seed value from a pseudo random value and
        # then adds this new value as the base for randomness in the
        # SSL base infra-structure, required for security
        seed = str(uuid.uuid4())
        seed = legacy.bytes(seed)
        ssl.RAND_add(seed, 0.0)

        # ignores the complete set of signals (avoids signal duplication)
        # and registers for the exit on the term signal that should be
        # sent from the parent process (proper exit/termination)
        self.bind_signals(handler = signal.SIG_IGN)
        self.bind_signals(signals = (signal.SIGTERM,))

    def on_diag(self):
        self.trigger("diag", self)

    def on_start(self):
        self.trigger("start", self)

    def on_stop(self):
        self.trigger("stop", self)

    def on_pause(self):
        self.trigger("pause", self)

    def on_resume(self):
        self.trigger("resume", self)

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
            # the SSL connection handshake must be performed/retried
            if connection.connecting: self._connectf(connection)

            # verifies if there's any pending operations in the
            # connection (eg: SSL handshaking) and performs it trying
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
        # the SSL connection handshake must be performed/retried
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
        if not hasattr(connection, "tuple"): return
        self.on_acquire(connection)

    def on_upgrade(self, connection):
        connection.set_upgraded()

    def on_ssl(self, connection):
        # runs the connection host verification process for the SSL
        # meaning that in case an SSL host value is defined it is going
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

    def info_dict(self, full = False):
        info = dict(
            loaded = self._loaded,
            connections = len(self.connections),
            state = self.get_state_s(),
            poll = self.get_poll_name()
        )
        if full: info.update(
            name = self.name,
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

    def new_connection(
        self,
        socket,
        address = None,
        datagram = False,
        ssl = False
    ):
        """
        Creates a new connection for the provided socket
        object and string based address, the returned
        value should be a workable object.

        :type socket: Socket
        :param socket: The socket object to be encapsulated
        by the object to be created (connection).
        :type address: String
        :param address: The address as a string to be used to
        describe the connection object to be created.
        :type datagram: bool
        :param datagram: If the connection to be created should
        be datagram based or not.
        :type ssl: bool
        :param ssl: If the connection to be created is meant to
        be secured using the SSL framework for encryption.
        :rtype: Connection
        :return: The connection object that encapsulates the
        provided socket and address values.
        """

        return Connection(
            owner = self,
            socket = socket,
            address = address,
            datagram = datagram,
            ssl = ssl
        )

    def add_callback(self, socket, callback):
        callbacks = self.callbacks_m.get(socket, [])
        if callback in callbacks: return
        callbacks.append(callback)
        self.callbacks_m[socket] = callbacks

    def remove_callback(self, socket, callback):
        callbacks = self.callbacks_m.get(socket, [])
        if not callback in callbacks: return
        callbacks.remove(callback)
        if callbacks: return
        del self.callbacks_m[socket]

    def load_config(self, path = "config.json", **kwargs):
        kwargs = self.apply_config(path, kwargs)
        for key, value in legacy.iteritems(kwargs):
            setattr(self, key, value)

    def apply_config(self, path, kwargs):
        if not os.path.exists(path): return kwargs

        self.info("Applying configuration file '%s' ..." % path)

        kwargs = copy.copy(kwargs)
        file = open(path, "rb")
        try: contents = json.load(file)
        finally: file.close()

        for key, value in legacy.iteritems(contents):
            kwargs[key] = value

        return kwargs

    def exec_safe(self, connection, callable, *args, **kwargs):
        try:
            return callable(*args, **kwargs)
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

        return False

    def is_devel(self):
        """
        Verifies if the current running environment is meant to be used
        for development purposes as opposed to a production environment.

        The method should always be used in situations where some critical
        and internal information is meant to be displayed in a development
        environment but hidden in a production one.

        This method should be used at runtime as opposed to the private
        configuration based one.

        :rtype: bool
        :return: If the current environment is development oriented or
        if it's considered to be a production one (invalid result).
        """

        return self.is_debug()

    def is_debug(self):
        if not self.logger: return False
        return self.logger.isEnabledFor(logging.DEBUG)

    def is_info(self):
        if not self.logger: return False
        return self.logger.isEnabledFor(logging.INFO)

    def is_warning(self):
        if not self.logger: return False
        return self.logger.isEnabledFor(logging.WARNING)

    def is_error(self):
        if not self.logger: return False
        return self.logger.isEnabledFor(logging.ERROR)

    def is_critical(self):
        if not self.logger: return False
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
        is_str = isinstance(object, legacy.STRINGS)
        try: message = str(object) if not is_str else object
        except: message = str(object)
        if not self.logger: return
        self.logger.log(level, message)

    def log_python_2(self, object, level = logging.INFO):
        is_str = isinstance(object, legacy.STRINGS)
        try: message = unicode(object) if not is_str else object #@UndefinedVariable
        except: message = str(object).decode("utf-8", "ignore")
        if not self.logger: return
        self.logger.log(level, message)

    def build_poll(self):
        # retrieves the reference to the parent class associated with
        # the current instance, it's going t be used for class methods
        cls = self.__class__

        # verifies if the currently set polling mechanism is open in
        # case it's ther's no need to re-build the polling mechanism
        # otherwise rebuilds the polling mechanism with the current
        # name and returns the new poll object to the caller method
        if self.poll and self.poll.is_open(): return self.poll

        # runs the testing of the poll again and verifies if the polling
        # class has changed in case it did not returns the current poll
        # instance as expected by the current infra-structure
        poll_c = cls.test_poll(preferred = self.poll_name)
        if poll_c == self.poll_c: return self.poll

        # updates the polling class with the new value and re-creates
        # the polling instance with the new polling class returning this
        # new value to the caller method
        self.poll_c = poll_c
        self.poll = self.poll_c()
        return self.poll

    def build_future(self, compat = True, asyncio = True):
        """
        Creates a future object that is bound to the current event
        loop context, this allows for latter access to the owning loop.

        :type compat: bool
        :param compat: If the compatibility mode retrieval should be used
        meaning that a compatible loop instance is retrieved instead.
        :type asyncio: bool
        :param asyncio: If the asyncio loop retrieval strategy should be
        used or if instead the netius native one should be used.
        :rtype: Future
        :return: The generated future that should be bound to the
        current context.
        """

        # creates a normal future object, setting the current loop (global) as
        # the loop, then returns the future to the caller method
        loop = self.get_loop(compat = compat, asyncio = asyncio)
        future = asynchronous.Future(loop = loop)
        return future

    def get_id(self, unique = True):
        base = NAME + "-" + util.camel_to_underscore(self.name)
        if not unique: return base
        return base + "-" + str(self._uuid)

    def get_poll(self):
        return self.poll

    def get_poll_name(self):
        poll = self.get_poll()
        name = poll.name()
        return name

    def get_state(self):
        return self._state

    def set_state(self, state):
        self._state = state

    def get_state_s(self, lower = True):
        """
        Retrieves a string describing the current state
        of the system, this string should be as descriptive
        as possible.

        An optional parameter controls if the string should
        be lower cased or not.

        :type lower: bool
        :param lower: If the returned string should be converted
        into a lower cased version.
        :rtype: String
        :return: A string describing the current sate of the loop
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

        :type name: String
        :param name: The name of the environment variable that is
        meant to be retrieved from the current environment
        :type default: Object
        :param default: The default value to be returned in case
        no value is found for the provided name.
        :type cast: Type
        :param cast: The cast type to be used to cast the value
        of the requested environment variable.
        :type expand: bool
        :param expand: If the variable should be expanded as a file
        object and stored in a temporary storage, for this situation
        the resulting object should be a string with the file path.
        :rtype: Object
        :return: The value of the requested environment variable
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

        The generated file is going to be removed on the cleanup operation
        so that no temporary file leaking occurs (garbage collection).

        In case the force value is provided the the file is created even
        for situations where the provided value is invalid/unset.

        :type value: String
        :param value: The string/bytes based value that is going to be
        expanded into a proper file system based (temporary) file.
        :type encoding: String
        :param encoding: The encoding that is going to be used to convert
        the value into a bytes based one in case the provided value is not
        bytes compliant (and must be converted).
        :type force: bool
        :param force: If the expansion operation should be performed even
        for situations where the value is considered invalid/unset.
        :rtype: String
        :return: The path to the temporary file that has just been generated
        for the expansion of the provided value.
        """

        if not value and not force: return value
        is_bytes = legacy.is_bytes(value)
        if not is_bytes: value = value.encode(encoding)
        value = value.replace(b"\\n", b"\n")
        fd, file_path = tempfile.mkstemp()
        os.close(fd)
        file = open(file_path, "wb")
        try: file.write(value)
        finally: file.close()
        self._expanded.append(file_path)
        return file_path

    def get_protocols(self):
        """
        Retrieves the complete set of protocols (as ALPN strings) that are
        going to be handled by the current protocol infra-structure.

        :rtype: List
        :return: The list containing the complete set of protocols handled
        by the current infra-structure.
        :see: https://tools.ietf.org/html/rfc7301
        """

        return None

    def get_adapter(self, name = "memory", *args, **kwargs):
        """
        Retrieves an instance of a storage adapter described
        by the provided name, note that the dynamic (extra)
        arguments are going to be used in the construction of
        the adapter instance.

        :type name: String
        :param name: The name of the adapter to be retrieved
        this should be equivalent to the adapter class name.
        :rtype: Adapter
        :return: An instance (properly configured) of the
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

        :type name: String
        :param name: The name of the authentication (handler)
        class that should be retrieved.
        :rtype: Auth
        :return: An authentication based class that may be used
        for the interaction of authentication methods.
        """

        name_f = name.title() + "Auth"
        auth_c = getattr(netius.auth, name_f)
        return auth_c

    def get_connection(self, socket):
        """
        "Resolves" the connection associated with the provided socket
        returning the structured connection object for it.

        In case no connection exists the method raises an exception
        invalidating the current logic stack.

        :type socket: Socket
        :param socket: The socket for which the connection is going to
        be returned.
        :rtype: Connection
        :return: The connection object associated with the provided
        socket reference.
        """

        return self.connections_m[socket]

    def _pending(self, connection):
        """
        Tries to perform the pending operations in the connection,
        these operations are set in the pending variable of the
        connection structure, so that it may be read latter on.

        The method returns if there are still pending operations
        after this method tick.

        :type connection: Connection
        :param connection: The connection object to be checked for
        pending operations and that is going to be used in the
        performing of these operations.
        :rtype: bool
        :return: If there are still pending operations to be
        performed in the provided connection.
        """

        # calls the run (tick) starter operation that should start
        # and run all the starters registered for the connection or
        # continue any starter operation that is pending for it
        return connection.run_starter()

    def _notifies(self):
        """
        Runs the notification process for the complete set of
        pending notification in the notified list.

        This tick operation may create tail recursion on callback
        call and so the list is always processed as a queue.

        The number of processed events is returned as part of the
        result.

        :rtype: int
        :return: The number of processed pending events/notifications.
        """

        # starts the counter that is going to be used to count
        # the number of processed notifications, start at zero
        count = 0

        # iterates while there are pending notifications to be
        # processed, the complete set of bind callables will be
        # called for each of the notifications
        while self._notified:
            event, data = self._notified.pop(0)
            binds = self._events.pop(event, [])
            for callable in binds: callable(data)
            count += 1

        # returns the number of processed notifications to the
        # the caller method
        return count

    def _delays(self):
        """
        Calls the complete set of elements that are considered to
        be part of the delayed set of methods to be called.

        These methods are expected to be run before a poll call so
        that they are run outside the handling.

        The calling of the delayed methods takes into account a
        series of assumptions including the loop identifier in order
        to avoid loops in the delayed calls/insertions.

        As part of the delay execution the pending notifications are
        also going to be processed, they must be handled together so
        that proper "recursion" is allowed (tail recursion).
        """

        # runs the merge delay lists operation, so that delay operations
        # inserts from different threads may be used and processed under
        # the current execution (as expected)
        self.delay_m()

        # in case there's no delayed items to be called returns the control
        # flow immediately, note that the notified elements (pending process)
        # are also going to be verified for presence
        if not self._delayed and not self._notified: return

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
        while self._delayed or self._notified:

            # runs the notifies verification cycle and if there's at
            # least one processed event continues the loop meaning that
            # the if test evaluations must be re-processed
            if self._notifies(): continue

            # "pops" the current item from the delayed list to be used
            # in the execution of the current iteration cycle
            callable_t = heapq.heappop(self._delayed)
            callable_o = heapq.heappop(self._delayed_o)

            # unpacks the current callable tuple in iteration into a
            # target (timestamp value) and a method to be called in
            # case the target timestamp is valid (in the past)
            target, _did, method, lid, options = callable_t

            # defines the proper target value that is going to be used
            # for the comparison against the current time reference
            # this is performed by defaulting the value against negative
            # ensuring immediate execution of the associated callable
            if target == None: target = -1

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

            # unpacks the multiple options so that it's possible to determine
            # the way the delayed operation is going to be executed
            run, = options

            # in case the method is not meant to be run, probably canceled
            # the execution of it should be properly ignored
            if not run: continue

            # calls the callback method as the delayed operation is
            # now meant to be run, this is an operation that may change
            # the current list of delayed object (causing cycles) and so
            # must be implemented with the proper precautions, note that
            # proper exception is set so that proper top level handling
            # is defined and logging is performed
            try: method()
            except BaseException as exception:
                self.error(exception)
                self.log_stack(method = self.warning)

        # iterates over all the pending callable tuple values and adds
        # them back to the delayed heap list so that they are called
        # latter on (not ready to be called now)
        for pending, pending_o in zip(pendings, pendings_o):
            heapq.heappush(self._delayed, pending)
            heapq.heappush(self._delayed_o, pending_o)

        # in case the delayed list is empty resets the delay id so that
        # it never gets into a very large number, would break performance
        if not self._delayed: self._did = 0

    def _generate(self, hashed = True):
        """
        Generates a random unique identifier that may be used
        to uniquely identify a certain object or operation.

        This method must be used carefully to avoid any unwanted
        behavior resulting from value collisions.

        :type hashed: bool
        :param hashed: If the identifier should be hashed into
        and hexadecimal string instead of an uuid based identifier.
        :rtype: String
        :return: The random unique identifier generated and that
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
        # rest of the method is dedicated to SSL tricks
        if not connection.ssl: return

        # verifies if the current SSL object is a context oriented one
        # (newest versions) or a legacy oriented one, that does not uses
        # any kind of context object, this is relevant in order to make
        # decisions on how the SSL object may be re-constructed
        has_context = hasattr(_socket, "context")
        has_sock = hasattr(_socket, "_sock")

        # creates the SSL object for the socket as it may have been
        # destroyed by the underlying SSL library (as an error) because
        # the socket is of type non blocking and raises an error, note
        # that the creation of the socket varies between SSL versions
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

        # verifies if the SSL object class is defined in the SSL module
        # and if that's the case an extra wrapping operation is performed
        # in order to comply with new indirection/abstraction methods
        if not hasattr(ssl, "SSLObject"): return
        _socket._sslobj = ssl.SSLObject(_socket._sslobj, owner = _socket)

    def _connectf(self, connection):
        """
        Finishes the process of connecting to the remote end-point
        this should be done in certain steps of the connection.

        The process of finishing the connecting process should include
        the SSL handshaking process.

        :type connection: Connection
        :param connection: The connection that should have the connect
        process tested for finishing.
        """

        # in case the SSL connection is still undergoing the handshaking
        # procedures (marked as connecting) ignores the call as this must
        # be a duplicated call to this method (to be ignored)
        if connection.ssl_connecting: return

        # verifies if there was an error in the middle of the connection
        # operation and if that's the case calls the proper callback and
        # returns the control flow to the caller method
        error = connection.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if error: self.on_error(connection.socket); return

        # checks if the current connection is SSL based and if that's the
        # case starts the handshaking process (async non blocking) otherwise
        # calls the on connect callback with the newly created connection
        if connection.ssl: connection.add_starter(self._ssl_handshake)
        else: self.on_connect(connection)

        # runs the starter process (initial kick-off) so that all the starters
        # registered for the connection may start to be executed, note that if
        # the SSL handshake starter has been registered its first execution is
        # going to be triggered by this call
        connection.run_starter()

    def _socket_keepalive(
        self,
        _socket,
        timeout = None,
        interval = None,
        count = None
    ):
        if timeout == None: timeout = self.keepalive_timeout
        if interval == None: interval = self.keepalive_interval
        if count == None: count = self.keepalive_count
        is_inet = _socket.family in (socket.AF_INET, socket.AF_INET6)
        is_inet and hasattr(_socket, "TCP_KEEPIDLE") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPIDLE, #@UndefinedVariable
                timeout
            )
        is_inet and hasattr(_socket, "TCP_KEEPINTVL") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPINTVL, #@UndefinedVariable
                interval
            )
        is_inet and hasattr(_socket, "TCP_KEEPCNT") and\
            self.socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPCNT, #@UndefinedVariable
                count
            )
        hasattr(_socket, "SO_REUSEPORT") and\
            self.socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEPORT, #@UndefinedVariable
                1
            )

    def _ssl_init(self, strict = True, env = True):
        # initializes the values of both the "main" context for SSL
        # and the map that associated an hostname and a context, both
        # are going to be used (if possible) at runtime for proper
        # resolution of both key and certificated files
        self._ssl_context = None
        self._ssl_contexts = dict()

        # verifies if the current SSL module contains a reference to
        # the SSL context class symbol if not, the control flow is
        # returned to the caller method as it's not possible to created
        # any kind of context information for SSL
        has_context = hasattr(ssl, "SSLContext")
        if not has_context: return

        # retrieves the reference to the environment variables that are going
        # to be used in the construction of the various SSL contexts, note that
        # the secure variable is extremely important to ensure that a proper and
        # secure SSL connection is established with the peer
        secure = self.get_env("SSL_SECURE", True, cast = bool) if env else False
        contexts = self.get_env("SSL_CONTEXTS", {}, cast = dict) if env else {}

        # creates the main/default SSL context setting the default key
        # and certificate information in such context, then verifies
        # if the callback registration method is defined and if it is
        # defined registers a callback for when the hostname information
        # is available, so that proper concrete context may be set, note
        # that in case the strict mode is enabled (default) the context
        # is unset for situation where no callback registration is possible
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self._ssl_ctx_base(self._ssl_context, secure = secure)
        self._ssl_ctx_protocols(self._ssl_context)
        self._ssl_certs(self._ssl_context)
        has_callback = hasattr(self._ssl_context, "set_servername_callback")
        if has_callback: self._ssl_context.set_servername_callback(self._ssl_callback)
        elif strict: self._ssl_context = None

        # retrieves the reference to the map containing the various key
        # and certificate paths for the various defined host names and
        # uses it to create the complete set of SSL context objects
        for hostname, values in legacy.iteritems(contexts):
            context = self._ssl_ctx(values, secure = secure)
            self._ssl_contexts[hostname] = (context, values)

    def _ssl_destroy(self):
        self._ssl_context = None
        self._ssl_contexts = dict()

    def _ssl_callback(self, socket, hostname, context):
        context, values = self._ssl_contexts.get(hostname, (context, None))
        self._ssl_ctx_protocols(context)
        socket.context = context
        if not values: return
        ssl_host = values.get("ssl_host", None)
        ssl_fingerprint = values.get("ssl_fingerprint", None)
        if not ssl_host and not ssl_fingerprint: return
        connection = self.connections_m.get(socket, None)
        if not connection: return
        connection.ssl_host = ssl_host
        connection.ssl_fingerprint = ssl_fingerprint

    def _ssl_ctx(self, values, context = None, secure = True):
        context = context or ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self._ssl_ctx_base(context, secure = secure)
        self._ssl_ctx_protocols(context)
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

    def _ssl_ctx_base(self, context, secure = True):
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

    def _ssl_ctx_protocols(self, context):
        self._ssl_ctx_alpn(context)
        self._ssl_ctx_npn(context)

    def _ssl_ctx_alpn(self, context):
        if not hasattr(ssl, "HAS_ALPN"): return
        if not ssl.HAS_ALPN: return
        if hasattr(context, "set_alpn_protocols"):
            protocols = self.get_protocols()
            protocols and context.set_alpn_protocols(protocols)

    def _ssl_ctx_npn(self, context):
        if not hasattr(ssl, "HAS_NPN"): return
        if not ssl.HAS_NPN: return
        if hasattr(context, "set_npn_protocols"):
            protocols = self.get_protocols()
            protocols and context.set_npn_protocols(protocols)

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
        ssl_verify = False,
        server_hostname = None
    ):
        socket_ssl = self._ssl_wrap(
            _socket,
            key_file = key_file,
            cer_file = cer_file,
            ca_file = ca_file,
            ca_root = ca_root,
            server = server,
            ssl_verify = ssl_verify,
            server_hostname = server_hostname
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
        ssl_verify = False,
        server_hostname = None
    ):
        # tries to determine the value for the check hostname flag to be
        # passed to the wrap function by ensuring that both the SSL verify
        # (certificate is provided) flag and the server hostname string exist
        check_hostname = True if ssl_verify and server_hostname else False

        dir_path = os.path.dirname(__file__)
        root_path = os.path.join(dir_path, "../")
        root_path = os.path.normpath(root_path)
        base_path = os.path.join(root_path, "base")
        extras_path = os.path.join(base_path, "extras")

        key_file = key_file or os.path.join(extras_path, "net.key")
        cer_file = cer_file or os.path.join(extras_path, "net.cer")

        cert_reqs = ssl.CERT_REQUIRED if ssl_verify else ssl.CERT_NONE

        # in case there's no SSL context defined in the current instance
        # then there's no support for contexts and a "direct" socket wrap
        # operation must be performed instead (legacy model)
        if not self._ssl_context:
            return ssl.wrap_socket(
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
            verify_mode = cert_reqs,
            check_hostname = check_hostname
        )

        return self._ssl_context.wrap_socket(
            _socket,
            server_side = server,
            do_handshake_on_connect = False,
            server_hostname = server_hostname
        )

    def _ssl_handshake(self, connection):
        """
        Low level SSL handshake operation that triggers or resumes
        the handshake process.

        It should be able to handle the exceptions raised by the the
        concrete handshake operation so that no exception is raised
        (unhandled) to the upper layers.

        :type connection: Connection
        :param connection: The connection that is going to be used in the
        handshake operation, this should contain a valid/open socket that
        should be registered for both read and write in the poll.
        """

        try:
            # unsets the handshake flag associated with the SSL, meaning
            # that the connection is considered to be currently under the
            # handshaking process (may succeed in the current tick)
            connection.ssl_handshake = False
            connection.ssl_connecting = True

            # tries to runs the handshake process, this represents
            # a series of small operations both of writing and reading
            # that a required to establish and guarantee a secure
            # connection from this moment on, note that this operation
            # may fail (non blocking issues) and further retries must
            # be attempted to finish establishing the connection
            _socket = connection.socket
            _socket.do_handshake()

            # sets the SSL handshake flag in the connection, effectively
            # indicating that the SSL handshake process has finished, note
            # that the connecting flag is also unset (SSL connect finished)
            connection.ssl_handshake = True
            connection.ssl_connecting = False

            # calls the end starter method in the connection so that the
            # connection gets notified that the current starter in process
            # has finished and that the next one should be called as
            # soon as possible to go further in the connection initialization
            connection.end_starter()

            # prints a debug information notifying the developer about
            # the finishing of the handshaking process for the connection
            self.debug("SSL Handshaking completed for connection")

            # calls the proper callback on the connection meaning
            # that SSL is now enabled for that socket/connection and so
            # the communication between peers is now secured
            self.on_ssl(connection)
        except ssl.SSLError as error:
            # tries to retrieve the error code from the argument information
            # in the error, in case the error is defined in the list of
            # valid errors, the handshake is delayed until either a write
            # or read operation is available (retry process)
            error_v = error.args[0] if error.args else None
            if error_v in SSL_VALID_ERRORS:
                if error_v == ssl.SSL_ERROR_WANT_WRITE and\
                    not self.is_sub_write(_socket):
                    self.sub_write(_socket)
                elif self.is_sub_write(_socket):
                    self.unsub_write(_socket)
            else: raise

    def _expand_destroy(self):
        """
        Destroys the complete set of infra-structure (files) associated
        with the expansion operation on environment values.

        This is required to avoid any kind of file leaking, should be run
        on the cleanup operation of the infra-structure.
        """

        # iterates over the complete list of expanded file paths to remove
        # their corresponding files (graceful error handling)
        for expanded in self._expanded:
            try: os.remove(expanded)
            except OSError: pass

        # deletes the complete set of path references from the expanded
        # list so that it is not going to be used any longer
        del self._expanded[:]

    def _level(self, level):
        """
        Converts the provided logging level value into the best
        representation of it, so that it may be used to update
        a logger's level of representation.

        This method takes into account the current interpreter
        version so that no problem occur.

        :type level: String/int
        :param level: The level value that is meant to be converted
        into the best representation possible.
        :rtype: int
        :return: The best representation of the level so that it may
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

    def _wait_forever(self):
        while True: time.sleep(60)

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
        self.owner._thread = self
        try:
            self.owner.start()
        finally:
            self.owner._thread = None
            self.owner = None

def new_loop_main(factory = None, _compat = None, **kwargs):
    factory = factory or Base
    kwargs["_slave"] = kwargs.pop("_slave", True)
    instance = factory(**kwargs)
    return compat_loop(instance) if _compat else instance

def new_loop_asyncio(**kwargs):
    asyncio = asynchronous.get_asyncio()
    if not asyncio: return None
    return asyncio.new_event_loop()

def new_loop(factory = None, _compat = None, asyncio = None, **kwargs):
    _compat = compat.is_compat() if _compat == None else _compat
    asyncio = compat.is_asyncio() if asyncio == None else asyncio
    if asyncio: return new_loop_asyncio(**kwargs)
    else: return new_loop_main(factory = factory, _compat = _compat, **kwargs)

def ensure_main(factory = None, **kwargs):
    if Base.get_main(): return
    factory = factory or Base
    instance = factory(**kwargs)
    Base.set_main(instance)

def ensure_asyncio(**kwargs):
    asyncio = asynchronous.get_asyncio()
    if not asyncio: return None
    return asyncio.get_event_loop()

def ensure_loop(factory = None, asyncio = None, **kwargs):
    asyncio = compat.is_asyncio() if asyncio == None else asyncio
    if asyncio: ensure_asyncio()
    else: ensure_main(factory = factory, **kwargs)

def get_main(factory = None, ensure = True, **kwargs):
    if ensure: ensure_main(factory = factory, **kwargs)
    return Base.get_main()

def get_loop(
    factory = None,
    ensure = True,
    _compat = None,
    asyncio = None,
    **kwargs
):
    _compat = compat.is_compat() if _compat == None else _compat
    asyncio = compat.is_asyncio() if asyncio == None else asyncio
    if ensure: ensure_loop(factory = factory, asyncio = asyncio)
    loop = Base.get_loop(compat = _compat, asyncio = asyncio)
    loop = loop or get_main(factory = factory, **kwargs)
    return loop

def get_event_loop(*args, **kwargs):
    """
    Compatibility alias function with the `get_loop()` function
    to ensure proper compatibility with asyncio.

    :rtype: EventLoop
    :return: The event loop for the current context of execution
    (if any) otherwise None (invalid).
    """

    return get_loop(*args, **kwargs)

def stop_loop(compat = True, asyncio = True):
    loop = get_loop(ensure = False, _compat = compat, asyncio = asyncio)
    if not loop: return
    loop.stop()

def compat_loop(loop):
    """
    Retrieves the asyncio API compatible version of the provided
    loop in case such version exists in the current object, otherwise
    returns the proper object (assumed to be asyncio API compatible).

    :type loop: EventLoop
    :param loop: The base event loop object from which an asyncio
    API compatible object is meant to be retrieved.
    :rtype: EventLoop
    :return: The asyncio API compatible event loop object.
    """

    return loop._compat if hasattr(loop, "_compat") else loop

def get_poll():
    main = get_main()
    if not main: return None
    return main.poll

def build_future(compat = True, asyncio = True):
    main = get_main()
    if not main: return None
    return main.build_future(compat = compat, asyncio = asyncio)

def ensure(coroutine, args = [], kwargs = {}, thread = None):
    loop = get_loop()
    return loop.ensure(
        coroutine,
        args = args,
        kwargs = kwargs,
        thread = thread
    )

def ensure_pool(coroutine, args = [], kwargs = {}):
    return ensure(
        coroutine,
        args = args,
        kwargs = kwargs,
        thread = True
    )

is_diag = config.conf("DIAG", False, cast = bool)
if is_diag: Base = DiagBase
else: Base = AbstractBase
