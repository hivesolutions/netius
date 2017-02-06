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

import inspect
import functools

from . import legacy

class AwaitWrapper(object):

    def __init__(self, generator):
        self.generator = generator

    def __await__(self):
        value = yield from self.generator
        return value

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.generator)

    def next(self):
        return self.__next__()

class AyncWrapper(object):

    def __init__(self, async_iter):
        self.async_iter = async_iter
        self.current = None

    def __iter__(self):
        return self

    def __next__(self):
        try:
            if self.current == None: self.current = self.async_iter.asend(None)
            try: return next(self.current)
            except StopIteration as exception:
                self.current = None
                return exception.args[0]
        except StopAsyncIteration: #@UndefinedVariable
            raise StopIteration

    def next(self):
        return self.__next__()

class CoroutineWrapper(object):

    def __init__(self, coroutine):
        self.coroutine = coroutine

    def __iter__(self):
        return self

    def __next__(self):
        return self.coroutine.send(None)

    def next(self):
        return self.__next__()

def coroutine(function):

    from .async import Future

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
            is_future = isinstance(result, Future)
            is_generator = inspect.isgenerator(result)

            # in case the returned value is either a future or a generator
            # the complete set of yielded elements are propagated and
            # the result is stored as the "new" result
            if is_future or is_generator:
                result = yield from result

            # returns the "final" result to the caller method as expected
            # this allows generated propagation
            return result

    routine._is_coroutine = True
    return routine

def ensure_generator(value):
    if legacy.is_generator(value):
        return True, value

    if hasattr(inspect, "isasyncgen") and\
        inspect.isasyncgen(value): #@UndefinedVariable
        return True, AyncWrapper(value)

    if hasattr(inspect, "iscoroutine") and\
        inspect.iscoroutine(value): #@UndefinedVariable
        return True, CoroutineWrapper(value)

    return False, value

def is_coroutine(callable):
    if hasattr(coroutine, "_is_coroutine"):
        return True

    if hasattr(inspect, "iscoroutine") and\
        inspect.iscoroutine(callable): #@UndefinedVariable
        return True

    if hasattr(inspect, "iscoroutinefunction") and\
        inspect.iscoroutinefunction(callable): #@UndefinedVariable
        return True

    return False

def _sleep(timeout):
    from .common import get_loop
    loop = get_loop()
    yield loop.sleep(timeout)
    return timeout

def _wait(event, timeout = None, future = None):
    from .common import get_loop
    loop = get_loop()
    yield loop.wait(event, timeout = timeout, future = future)

def sleep(*args, **kwargs):
    generator = _sleep(*args, **kwargs)
    return AwaitWrapper(generator)

def wait(*args, **kwargs):
    generator = _wait(*args, **kwargs)
    return AwaitWrapper(generator)
