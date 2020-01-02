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

import inspect
import functools

from . import errors
from . import legacy
from . import async_old

try: import asyncio
except ImportError: asyncio = None

class Future(async_old.Future):
    """
    Specialized Future class that supports the async/await
    syntax to be used in a future, so that it becomes compliant
    with the basic Python asyncio strategy for futures.

    Using this future it should be possible to ``await Future()`
    for a simpler usage.
    """

    def __iter__(self):
        while not self.done():
            self._blocking = True
            yield self
        if self.cancelled():
            raise errors.RuntimeError("Future canceled")
        if self.exception():
            raise self.exception()
        return self.result()

    def __await__(self):
        while not self.done():
            self._blocking = True
            yield self
        if self.cancelled():
            raise errors.RuntimeError("Future canceled")
        if self.exception():
            raise self.exception()
        return self.result()

class AwaitWrapper(object):
    """
    Wrapper class meant to be used to encapsulate "old"
    generator based objects as async generator objects that
    are eligible to be used with the async/await syntax.

    It's also possible to pass simple values instead of
    generator functions and still use the wrapper.
    """

    _is_generator = True
    """ Hard coded static flag that allows the underlying
    infra-structure to know that this type is considered
    to be generator compliant """

    def __init__(self, generator, generate = False):
        if generate: generator = self.generate(generator)
        self.generator = generator
        self.is_generator = legacy.is_generator(generator)

    def __await__(self):
        if self.is_generator: return self._await_generator()
        else: return self._await_basic()

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.generator)

    def next(self):
        return self.__next__()

    def generate(self, value):
        yield value

    def _await_generator(self):
        value = yield from self.generator
        return value

    def _await_basic(self):
        return self.generator
        yield

class CoroutineWrapper(object):
    """
    Wrapper class meant to encapsulate a coroutine object
    as a standard iterator sequence to be used in chain/iterator
    like execution environment.

    This is only required for the native coroutine objects
    so that they can comply with the required netius interface.
    """

    def __init__(self, coroutine):
        self.coroutine = coroutine
        self._buffer = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._buffer: return self._buffer.pop(0)
        return self.coroutine.send(None)

    def next(self):
        return self.__next__()

    def restore(self, value):
        if self._buffer == None: self._buffer = []
        self._buffer.append(value)

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

            # in case the returned value is either a future or a generator
            # the complete set of yielded elements are propagated and
            # the result is stored as the "new" result
            if is_future_ or is_generator:
                result = yield from result

            # returns the "final" result to the caller method as expected
            # this allows generated propagation
            return result

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        generator = routine(*args, **kwargs)
        awaitable = AwaitWrapper(generator)
        return awaitable

    wrapper._is_coroutine = True
    return wrapper

def ensure_generator(value):
    if legacy.is_generator(value):
        return True, value

    if hasattr(inspect, "iscoroutine") and\
        inspect.iscoroutine(value): #@UndefinedVariable
        return True, CoroutineWrapper(value)

    return False, value

def get_asyncio():
    return asyncio

def is_coroutine(callable):
    if hasattr(callable, "_is_coroutine"):
        return True

    if hasattr(inspect, "iscoroutinefunction") and\
        inspect.iscoroutinefunction(callable): #@UndefinedVariable
        return True

    return False

def is_coroutine_object(generator):
    if legacy.is_generator(generator):
        return True

    if hasattr(inspect, "iscoroutine") and\
        inspect.iscoroutine(generator): #@UndefinedVariable
        return True

    return False

def is_coroutine_native(generator):
    if hasattr(inspect, "iscoroutine") and\
        inspect.iscoroutine(generator): #@UndefinedVariable
        return True

    return False

def is_future(future):
    if isinstance(future, async_old.Future): return True
    if asyncio and isinstance(future, asyncio.Future): return True
    return False

def _sleep(timeout, compat = True):
    from .common import get_loop
    loop = get_loop()
    compat &= hasattr(loop, "_sleep")
    sleep = loop._sleep if compat else loop.sleep
    result = yield from sleep(timeout)
    return result

def _wait(event, timeout = None, future = None):
    from .common import get_loop
    loop = get_loop()
    result = yield from loop.wait(
        event,
        timeout = timeout,
        future = future
    )
    return result

def sleep(*args, **kwargs):
    generator = _sleep(*args, **kwargs)
    return AwaitWrapper(generator)

def wait(*args, **kwargs):
    generator = _wait(*args, **kwargs)
    return AwaitWrapper(generator)

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

    generator = _coroutine_return(coroutine)
    return AwaitWrapper(generator)

def _coroutine_return(coroutine):
    for value in coroutine:
        yield value
        future = value
    return future.result()
