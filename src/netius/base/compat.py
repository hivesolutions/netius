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

from . import async

class AbstractLoop(object):
    """
    Top level abstract class that adds compatibility support for
    the asyncio event loop strategy.
    """

    def time(self):
        return time.time()

    def call_at(self, when, callback, *args):
        delay = when - self.time()
        return self.call_later(delay, callback, *args)

    def call_later(self, delay, callback, *args):
        """
        Calls the provided callback with the provided parameters after the defined
        delay (in seconds), should ensure proper sleep operation.

        :type delay: float
        :param delay: The delay in seconds after which the callback is going to be
        called with the provided arguments.
        :type callback: Function
        :param callback: The function to be called after the provided delay.
        :rtype: Handle
        :return: The handle object to the operation, that may be used to cancel it.
        """

        # creates the callable to be called after the timeout, note the
        # clojure around the "normal" arguments (allows proper propagation)
        callable = lambda: callback(*args)

        # schedules the delay call of the created callable according to
        # the provided (amount of) sleep time
        self.delay(callable, timeout = delay)

        # creates the handle to control the operation and then returns the
        # object to the caller method, allowing operation
        handle = async.Handle()
        return handle

    def create_future(self):
        """
        Creates a future object that is bound to the current event loop context,
        this allows for latter access to the owning loop.

        This behaviour is required to ensure compatibility with the "legacy"
        asyncio support, ensuring seamless compatibility.

        :rtype: Future
        :return: The generated future that should be bound to the current context.
        """

        # creates a normal future object, setting the current instance as
        # the loop, then returns the future to the caller method
        future = async.Future()
        future._loop = self
        return future

    def get_debug(self):
        return self.is_debug()
