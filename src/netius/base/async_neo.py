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

import inspect
import functools

def coroutine(function):

    from .async import Future

    if inspect.isgeneratorfunction(function):
        routine = function
    else:
        @functools.wraps(function)
        def routine(*args, **kwargs):
            result = function(*args, **kwargs)

            is_future = isinstance(result, Future)
            is_generator = inspect.isgenerator(result)

            if is_future or is_generator:
                result = yield from result

            return result

    routine._is_coroutine = True
    return routine

def sleep(timeout):
    from .common import get_loop
    loop = get_loop()
    yield loop.sleep(timeout)
    return timeout
