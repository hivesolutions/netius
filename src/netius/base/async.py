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

import sys

import inspect
import functools

class Future(object):

    def __init__(self):
        self.status = 0
        self._result = None
        self._exception = None
        self.cleanup()

    def cleanup(self):
        self.done_callbacks = []
        self.partial_callbacks = []
        self.ready_callbacks = []
        self.closed_callbacks = []

    def cancelled(self):
        return self.status == 2

    def running(self):
        return self.status == 0

    def done(self):
        return self.status == 1

    def result(self):
        return self._result

    def exception(self, timeout = None):
        return self._exception

    def partial(self, value):
        self._partial_callbacks(value)

    def add_done_callback(self, function):
        self.done_callbacks.append(function)

    def add_partial_callback(self, function):
        self.partial_callbacks.append(function)

    def add_ready_callback(self, function):
        self.ready_callbacks.append(function)

    def add_closed_callback(self, function):
        self.closed_callbacks.append(function)

    def approve(self, cleanup = True):
        self.set_result(None, cleanup = cleanup)

    def cancel(self, cleanup = True):
        self.set_exception(None, cleanup = cleanup)

    def set_result(self, result, cleanup = True):
        self.status = 1
        self._result = result
        self._done_callbacks()
        cleanup and self.cleanup()

    def set_exception(self, exception, cleanup = True):
        self.status = 2
        self._exception = exception
        self._done_callbacks()
        cleanup and self.cleanup()

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

    def _done_callbacks(self):
        for callback in self.done_callbacks: callback(self)

    def _partial_callbacks(self, value):
        for callback in self.partial_callbacks: callback(self, value)

def coroutine(function):

    if inspect.isgeneratorfunction(function):
        routine = function
    else:
        @functools.wraps(function)
        def routine(*args, **kwargs):
            result = function(*args, **kwargs)

            is_future = isinstance(result, Future)
            is_generator = inspect.isgenerator(result)

            if is_future or is_generator:
                for value in result: yield value
            else:
                yield result

    routine._is_coroutine = True
    return routine

def sleep(timeout, future = None):
    from .common import get_loop
    loop = get_loop()
    yield loop.sleep(timeout, future = future)

def wait(event, future = None):
    from .common import get_loop
    loop = get_loop()
    yield loop.wait(event, future = future)

def notify(event, data = None):
    from .common import get_loop
    loop = get_loop()
    return loop.notify(event, data = data)

is_neo = sys.version_info[0] >= 3 and sys.version_info[1] >= 3
if is_neo: from .async_neo import * #@UnusedWildImport
