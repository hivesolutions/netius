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

import uuid

class NetiusError(Exception):
    """
    The top level base error to be used in the
    netius infra-structure.

    Note that this class inherits from the runtime
    error meaning that all the errors are runtime.
    """

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args)
        message = args[0] if len(args) > 0 else ""
        code = args[1] if len(args) > 1 else 500
        kwargs["message"] = kwargs.get("message", message)
        kwargs["code"] = kwargs.get("code", code)
        self.kwargs = kwargs
        self.message = kwargs["message"]
        self.code = kwargs["code"]
        self._uid = None

    def get_kwarg(self, name, default = None):
        return self.kwargs.get(name, default)

    @property
    def uid(self):
        if self._uid: return self._uid
        self._uid = uuid.uuid4()
        return self._uid

class RuntimeError(NetiusError):
    """
    Error to be used for situations where an exception
    is raised during a typical runtime situation.

    This error class is meant to be used as the parent
    class in every exception raised during normal execution.
    """

    pass

class StopError(RuntimeError):
    """
    Error to be used for situations where a stop
    intention is meant to be raised to upper layers.

    This error represent an operation and not a real
    error and should be used as such.
    """

    pass

class PauseError(RuntimeError):
    """
    Error to be used for situations where a pause
    intention is meant to be raised to upper layers.

    This error represent an operation and not a real
    error and should be used as such.
    """

    pass

class WakeupError(RuntimeError):
    """
    Error used to send a wakeup intent from one context
    or thread to another.

    This is especially useful on the context of signal
    handling where an interruption may happen at any time.
    """

    pass

class DataError(RuntimeError):
    """
    Error to be used for situations where the
    data that has been received/sent is invalid.

    This error may be used for situations where
    the data in the buffer is not sufficient for
    parsing the values.
    """

    pass

class ParserError(RuntimeError):
    """
    Error caused by a malformed data that invalidated
    the possibility to parse it.

    This error should only be used under a parser infra-
    structure and never outside it.
    """

    def __init__(self, *args, **kwargs):
        kwargs["message"] = kwargs.get("message", "Parser error")
        kwargs["code"] = kwargs.get("code", 400)
        RuntimeError.__init__(self, *args, **kwargs)

class GeneratorError(RuntimeError):
    """
    Error generated by a problem in the generation of
    and encoded data (reverse of parser error).

    This error should be raise only in a generator of
    an encoded stream buffer.
    """

    pass

class SecurityError(RuntimeError):
    """
    Error caused by a failed security verification this
    errors should be properly audited in order to avoid
    extra problems that may arise from them.

    This kind of problems is considered to be runtime
    as they should not be related with programming.
    """

    pass

class NotImplemented(RuntimeError):
    """
    Error caused by the non implementation of a certain
    method/feature at a certain level. This may mean that
    the wrong level of abstraction is being called or a
    certain feature is pending development.

    This kind of problems is considered to be development
    as they may be related with programming.
    """

    pass

class AssertionError(RuntimeError):
    """
    Error raised for failure to meet any pre-condition or
    assertion for a certain data set.
    """

    pass
