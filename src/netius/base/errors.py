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

class NetiusError(RuntimeError):
    """
    The top level base error to be used in the
    netius infra-structure.

    Note that this class inherits from the runtime
    error meaning that all the errors are runtime.
    """

    pass

class DataError(NetiusError):
    """
    Error to be used for situations where the
    data that has been received/sent is invalid.

    This error may be used for situations where
    the data in the buffer is not sufficient for
    parsing the values.
    """

    pass

class ParserError(NetiusError):
    """
    Error caused by a malformed data that invalidated
    the possibility to parse it.

    This error should only be used under a parser infra-
    structure and never outside it.
    """

    pass
