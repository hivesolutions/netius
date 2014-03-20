#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import time

REQUEST_TIMEOUT = 10
""" The timeout until a request is considered to be
expired and is discarded from the request related
structures, this is crucial to avoid memory leaks """

class Request(object):

    IDENTIFIER = 0x0000
    """ The global class identifier value that is going to
    be used when assigning new values to the request """

    def __init__(self, timeout = REQUEST_TIMEOUT):
        self.id = self.__class__._generate_id()
        self.timeout = time.time() + timeout

    @classmethod
    def _generate_id(cls):
        cls.IDENTIFIER
        cls.IDENTIFIER = (cls.IDENTIFIER + 1) & 0xffff
        return cls.IDENTIFIER

class Response(object):
    pass
