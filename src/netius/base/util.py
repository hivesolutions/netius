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

import re

from . import errors

FIRST_CAP_REGEX = re.compile("(.)([A-Z][a-z]+)")
""" Regular expression that ensures that the first
token of each camel string is properly capitalized """

ALL_CAP_REGEX = re.compile("([a-z0-9])([A-Z])")
""" The generalized transition from lower case to
upper case letter regex that will provide a way of
putting the underscore in the middle of the transition """

def camel_to_underscore(camel, separator = "_"):
    """
    Converts the provided camel cased based value into
    a normalized underscore based string.

    This is useful as most of the python string standards
    are compliant with the underscore strategy.

    :type camel: String
    :param camel: The camel cased string that is going to be
    converted into an underscore based string.
    :type separator: String
    :param separator: The separator token that is going to
    be used in the camel to underscore conversion.
    :rtype: String
    :return: The underscore based string resulting from the
    conversion of the provided camel cased one.
    """

    value = FIRST_CAP_REGEX.sub(r"\1" + separator + r"\2", camel)
    value = ALL_CAP_REGEX.sub(r"\1" + separator + r"\2", value)
    value = value.lower()
    return value

def verify(condition, message = None, exception = None):
    """
    Ensures that the requested condition returns a valid value
    and if that's no the case an exception raised breaking the
    current execution logic.

    :type condition: bool
    :param condition: The condition to be evaluated and that may
    trigger an exception raising.
    :type message: String
    :param message: The message to be used in the building of the
    exception that is going to be raised in case of condition failure.
    :type exception: Class
    :param exception: The exception class that is going to be used
    to build the exception to be raised in case the condition
    verification operation fails.
    """

    if condition: return
    exception = exception or errors.AssertionError
    raise exception(message or "Assertion Error")
