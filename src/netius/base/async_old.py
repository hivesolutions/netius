#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import sys

import inspect
import functools

from . import errors
from . import legacy

class Future(object):
    """
    Base future object that represents a promise that a certain
    operation is going to be accomplished.

    Should be used as a placeholder for the callbacks for error
    and success and the for the final result of the execution.

    Most of the implementation takes inspiration on the reference
    Python implementation on futures.

    :see: https://en.wikipedia.org/wiki/Futures_and_promises
    """

    def __init__(self, loop = None):
        self.status = 0
        self._loop = loop
        self._blocking = False
        self._result = None
        self._exception = None
        self.cleanup()

    def __iter__(self):
        while not self.done(): yield self
        if self.cancelled():
            raise errors.RuntimeError("Future canceled")
        if self.exception():
            raise self.exception()

    def cleanup(self):
        self.done_callbacks = []
        self.partial_callbacks = []
        self.ready_callbacks = []
        self.closed_callbacks = []

    def running(self):
        return self.status == 0

    def done(self):
        return self.status in (1, 2)

    def cancelled(self):
        return self.status == 2

    def finished(self):
        return self.done()

    def result(self):
        if self.cancelled():
            raise errors.RuntimeError("Already canceled")
        return self._result

    def exception(self, timeout = None):
        return self._exception

    def partial(self, value):
        self._partial_callbacks(value)

    def add_done_callback(self, function):
        self.done_callbacks.append(function)
        if not self.finished(): return
        self._done_callbacks()

    def add_partial_callback(self, function):
        self.partial_callbacks.append(function)

    def add_ready_callback(self, function):
        self.ready_callbacks.append(function)

    def add_closed_callback(self, function):
        self.closed_callbacks.append(function)

    def approve(self, cleanup = True):
        self.set_result(None, cleanup = cleanup)

    def cancel(self, cleanup = True, force = False):
        if not force and not self.running(): return False
        self.status = 2
        self._done_callbacks(cleanup = cleanup)
        return True

    def set_result(self, result, cleanup = True, force = False):
        if not force and not self.running():
            raise errors.AssertionError("Future not running")
        self.status = 1
        self._result = result
        self._done_callbacks(cleanup = cleanup)

    def set_exception(self, exception, cleanup = True, force = False):
        if not force and not self.running():
            raise errors.AssertionError("Future not running")
        self.status = 1
        self._exception = exception
        self._done_callbacks(cleanup = cleanup)

    @property
    def ready(self):
        ready = True
        for callback in self.ready_callbacks: ready &= callback()
        return ready

    @property
    def closed(self):
        closed = False
        for callback in self.closed_callbacks: closed |= callback()
        return closed

    def _done_callbacks(self, cleanup = True, delayed = True):
        if not self.done_callbacks: return
        if delayed and self._loop:
            return self._delay(
                lambda: self._done_callbacks(
                    cleanup = cleanup,
                    delayed = False
                )
            )
        for callback in self.done_callbacks: callback(self)
        if cleanup: self.cleanup()

    def _partial_callbacks(self, value, delayed = True):
        if not self.partial_callbacks: return
        if delayed and self._loop: return self._delay(
            lambda: self._partial_callbacks(value, delayed = False)
        )
        for callback in self.partial_callbacks: callback(self, value)

    def _wrap(self, future):
        self.status = future.status
        self.done_callbacks = future.done_callbacks
        self.partial_callbacks = future.partial_callbacks
        self.ready_callbacks = future.ready_callbacks
        self.closed_callbacks = future.closed_callbacks
        self._loop = future._loop
        self._blocking = future._blocking
        self._result = future._result
        self._exception = future._exception

    def _delay(self, callable):
        has_delay = hasattr(self._loop, "delay")
        if has_delay: return self._loop.delay(callable, immediately = True)
        return self._loop.call_soon(callable)

class Task(Future):

    def __init__(self, future = None):
        Future.__init__(self)
        self._future = future
        self._source_traceback = None
        if future: self._wrap(future)

class Handle(object):

    def __init__(self, callable_t = None):
        self._callable_t = callable_t

    def cancel(self):
        if not self._callable_t: return
        options = self._callable_t[4]
        options[0] = False

class Executor(object):

    def submit(self, callable, *args, **kwargs):
        raise errors.NotImplemented("Missing implementation")

class ThreadPoolExecutor(Executor):

    def __init__(self, owner):
        self.owner = owner

    def submit(self, callable, *args, **kwargs):
        future = self.owner.build_future()
        callback = lambda result: self.owner.delay_s(
            lambda: future.set_result(result)
        )
        self.owner.texecute(
            callable,
            args = args,
            kwargs = kwargs,
            callback = callback
        )
        return future

def coroutine(function):

    if inspect.isgeneratorfunction(function):
        routine = function
    else:
        @functools.wraps(function)
        def routine(*args, **kwargs):
            # calls the underlying function with the expected arguments
            # and keyword arguments (proper call propagation)
            result = function(*args, **kwargs)

            # verifies the data type of the resulting object so that a
            # proper yielding operation or return will take place
            is_future_ = is_future(result)
            is_generator = inspect.isgenerator(result)

            # in case the result is either a future or a generator the
            # complete set of values are properly yield to the caller
            # method as expected
            if is_future_ or is_generator:
                for value in result: yield value

            # otherwise the single resulting value is yield to the
            # caller method (simple propagation)
            else:
                yield result

    routine._is_coroutine = True
    return routine

def async_test_all(factory = None, close = True):

    def decorator(function):

        from . import common
        from . import asynchronous

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            function_c = asynchronous.coroutine(function)
            future = function_c(*args, **kwargs)
            loop = common.get_main(factory = factory)
            return loop.run_coroutine(future, close = close)

        return wrapper

    return decorator

def async_test(function):
    decorator = async_test_all()
    return decorator(function)

def ensure_generator(value):
    if legacy.is_generator(value): return True, value
    return False, value

def get_asyncio():
    return None

def is_coroutine(callable):
    if hasattr(callable, "_is_coroutine"): return True
    return False

def is_coroutine_object(generator):
    if legacy.is_generator(generator): return True
    return False

def is_coroutine_native(generator):
    return False

def is_future(future):
    if isinstance(future, Future): return True
    return False

def is_neo():
    return sys.version_info[0] >= 3 and sys.version_info[1] >= 3

def is_asynclib():
    return sys.version_info[0] >= 3 and sys.version_info[1] >= 4

def is_await():
    return sys.version_info[0] >= 3 and sys.version_info[1] >= 6

def wakeup(force = False):
    from .common import get_loop
    loop = get_loop()
    return loop.wakeup(force = force)

def sleep(timeout, compat = True, future = None):
    from .common import get_loop
    loop = get_loop()
    compat &= hasattr(loop, "_sleep")
    sleep = loop._sleep if compat else loop.sleep
    for value in sleep(timeout, future = future): yield value

def wait(event, timeout = None, future = None):
    from .common import get_loop
    loop = get_loop()
    for value in loop.wait(event, timeout = timeout, future = future): yield value

def notify(event, data = None):
    from .common import get_loop
    loop = get_loop()
    return loop.notify(event, data = data)

def coroutine_return(coroutine):
    """
    Allows for the abstraction of the return value of a coroutine
    object to be the result of the future yield as the first element
    of the generator.

    This allows the possibility to provide compatibility with the legacy
    not return allowed generators.

    :type coroutine: CoroutineObject
    :param coroutine: The coroutine object that is going to be yield back
    and have its last future result returned from the generator.
    """

    for value in coroutine: yield value
