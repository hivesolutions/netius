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

from . import errors

REQUEST_TIMEOUT = 10.0
""" The timeout until a request is considered to be
expired and is discarded from the request related
structures, this is crucial to avoid memory leaks """

class Request(object):
    """
    Abstract request structure used to represent
    a request in a server/client model, this allows
    for easy identification and response (callback).
    """

    IDENTIFIER = 0x0000
    """ The global class identifier value that is going to
    be used when assigning new values to the request """

    def __init__(self, timeout = REQUEST_TIMEOUT, callback = None):
        self.id = self.__class__._generate_id()
        self.timeout = time.time() + timeout
        self.callback = callback

    @classmethod
    def _generate_id(cls):
        cls.IDENTIFIER
        cls.IDENTIFIER = (cls.IDENTIFIER + 1) & 0xffff
        return cls.IDENTIFIER

class Response(object):
    """
    Top level abstract representation of a response to
    be sent based on a previously created request, the
    input of this object should be raw data and a relation
    between the request and the response is required.

    The association/relation between the response and the
    request should be done using the original request
    generated identifier.
    """

    def __init__(self, data, request = None):
        self.data = data
        self.request = request

    def parse(self):
        pass

    def get_request(self):
        return self.request

    def get_id(self):
        raise errors.NetiusError("Not implemented")
