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

import time
import socket

from . import errors
from . import asynchronous

asyncio = asynchronous.get_asyncio() if asynchronous.is_neo() else None
BaseLoop = asyncio.AbstractEventLoop if asyncio else object
BaseTransport = asyncio.BaseTransport if asyncio else object

class CompatLoop(BaseLoop):
    """
    Top level compatibility class that adds compatibility support
    for the asyncio event loop strategy.

    This is required to be able to access netius event loop on a
    asyncio like manner.

    :see: https://docs.python.org/3/library/asyncio-eventloop.html
    """

    def __init__(self, loop):
        self._loop = loop
        self._task_factory = asynchronous.Task
        self._executor = asynchronous.ThreadPoolExecutor(loop)

    def __getattr__(self, name):
        if hasattr(self._loop, name):
            return getattr(self._loop, name)
        raise AttributeError("'%s' not found" % name)

    def time(self):
        return time.time()

    def call_soon(self, callback, *args):
        return self._call_delay(callback, args, immediately = True)

    def call_soon_threadsafe(self, callback, *args):
        return self._call_delay(callback, args, immediately = True, safe = True)

    def call_at(self, when, callback, *args):
        delay = when - self.time()
        return self._call_delay(callback, args, timeout = delay)

    def call_later(self, delay, callback, *args):
        """
        Calls the provided callback with the provided parameters after
        the defined delay (in seconds), should ensure proper sleep operation.

        :type delay: float
        :param delay: The delay in seconds after which the callback is going
        to be called with the provided arguments.
        :type callback: Function
        :param callback: The function to be called after the provided delay.
        :rtype: Handle
        :return: The handle object to the operation, that may be used to cancel it.
        """

        return self._call_delay(callback, args, timeout = delay)

    def create_future(self):
        return self._loop.build_future()

    def create_task(self, coroutine):
        future = self._loop.ensure(coroutine)
        task = self._task_factory(future)
        return task

    def create_connection(self, *args, **kwargs):
        coroutine = self._create_connection(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def getaddrinfo(self, *args, **kwargs):
        coroutine = self._getaddrinfo(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def getnameinfo(self, *args, **kwargs):
        coroutine = self._getnameinfo(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def run_until_complete(self, future):
        self._set_current_task(future)
        try: return self._loop.run_coroutine(future)
        finally: self._unset_current_task()

    def run_in_executor(self, *args, **kwargs):
        coroutine = self._run_in_executor(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def close(self):
        self._loop.close()

    def get_debug(self):
        return self._loop.is_debug()

    def set_debug(self, enabled):
        pass

    def set_default_executor(self, executor):
        self._executor = executor

    def get_task_factory(self):
        return self._task_factory

    def set_task_factory(self, factory):
        self._task_factory = factory

    def is_running(self):
        return self._loop.is_running()

    def is_closed(self):
        return self._loop.is_stopped()

    def _getaddrinfo(
        self,
        host,
        port,
        family = 0,
        type = 0,
        proto = 0,
        flags = 0
    ):
        future = self.create_future()
        result = socket.getaddrinfo(
            host,
            port,
            family,
            type,
            proto,
            flags = flags
        )
        self._loop.delay(lambda: future.set_result(result), immediately = True)
        yield future

    def _getnameinfo(self, sockaddr, flags = 0):
        raise errors.NotImplemented("Missing implementation")

    def _run_in_executor(self, executor, func, *args):
        executor = executor or self._executor
        future = executor.submit(func, *args)
        yield future

    def _create_connection(
        self,
        protocol_factory,
        host = None,
        port = None,
        ssl = None,
        family = 0,
        proto = 0,
        flags = 0,
        sock = None,
        local_addr = None,
        server_hostname = None,
        *args,
        **kwargs
    ):
        family = family or socket.AF_INET

        future = self.create_future()

        def connect(connection):
            protocol = protocol_factory()
            transport = CompatTransport(connection)
            transport._set_compat(protocol)
            future.set_result((transport, protocol))

        connection = self._loop.connect(
            host,
            port,
            ssl = ssl,
            family = family,
            ensure_loop = False
        )
        connection.bind("connect", connect)

        yield future

    def _set_current_task(self, task):
        asyncio = asynchronous.get_asyncio()
        if not asyncio: return
        asyncio.Task._current_tasks[self] = task

    def _unset_current_task(self):
        asyncio = asynchronous.get_asyncio()
        if not asyncio: return
        asyncio.Task._current_tasks.pop(self, None)

    def _call_delay(
        self,
        callback,
        args,
        timeout = None,
        immediately = False,
        verify = False,
        safe = False
    ):
        # creates the callable to be called after the timeout, note the
        # clojure around the "normal" arguments (allows proper propagation)
        callable = lambda: callback(*args)

        # schedules the delay call of the created callable according to
        # the provided set of options expected by the delay operation the
        # callback tuple is returned so that a proper handle may be created
        callable_t = self._loop.delay(
            callable,
            timeout = timeout,
            immediately = immediately,
            verify = verify,
            safe = safe
        )

        # creates the handle to control the operation and then returns the
        # object to the caller method, allowing operation cancellation
        handle = asynchronous.Handle(callable_t = callable_t)
        return handle

    def _sleep(self, timeout, future = None):
        # verifies if a future variable is meant to be re-used
        # or if instead a new one should be created for the new
        # sleep operation to be executed
        future = future or self.create_future()

        # creates the callable that is going to be used to set
        # the final value of the future variable
        callable = lambda: future.set_result(timeout)

        # delays the execution of the callable so that it is executed
        # after the requested amount of timeout, note that the resolution
        # of the event loop will condition the precision of the timeout
        future._loop.call_later(timeout, callable)
        return future

    @property
    def _thread_id(self):
        return self._loop.tid

class CompatTransport(BaseTransport):
    """
    Decorator class to be used to add the functionality of a
    transport layer as defined by the asyncio.

    Allows adding the functionality to an internal netius
    (or equivalent) object.
    """

    def __init__(self, connection):
        self._connection = connection
        self._protocol = None

    def close(self):
        self._connection.close()

    def abort(self):
        self._connection.close()

    def write(self, data):
        self._connection.send(data)

    def get_extra_info(self, name, default = None):
        if name == "socket": return self._connection.socket
        else: return default

    def set_protocol(self, protocol):
        self._set_protocol(protocol, mark = False)

    def get_protocol(self):
        return self._protocol

    def is_closing(self):
        return self._connection.is_closed()

    def _on_data(self, connection, data):
        self._protocol.data_received(data)

    def _on_close(self, connection):
        self._protocol.eof_received()
        self._protocol.connection_lost(None)

    def _set_compat(self, protocol):
        self._set_binds()
        self._set_protocol(protocol)

    def _set_binds(self):
        self._connection.bind("data", self._on_data)
        self._connection.bind("close", self._on_close)

    def _set_protocol(self, protocol, mark = True):
        self._protocol = protocol
        if mark: self._protocol.connection_made(self)
