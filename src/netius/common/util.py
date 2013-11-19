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

import socket

def cstring(value):
    index = value.index("\0")
    if index == -1: return value
    return value[:index]

def header_up(name):
    values = name.split("-")
    values = [value.title() for value in values]
    return "-".join(values)

def addr_to_ip4(number):
    first = int(number / 16777216) % 256
    second = int(number / 65536) % 256
    third = int(number / 256) % 256
    fourth = int(number) % 256
    return "%s.%s.%s.%s" % (first, second, third, fourth)

def ip4_to_addr(value):
    first, second, third, fourth = value.split(".", 3)
    first_a = int(first) * 16777216
    second_a = int(second) * 65536
    third_a = int(third) * 256
    fourth_a = int(fourth)
    return first_a + second_a + third_a + fourth_a

def host():
    """
    Retrieves the host for the current machine,
    typically this would be the ipv4 address of
    the main network interface.

    No result type are guaranteed and a local address
    (eg: 127.0.0.1) may be returned instead.

    @rtype: Strong
    @return: The string that contains the host address
    as defined by specification for the current machine.
    """

    hostname = socket.gethostname()
    host = socket.gethostbyname(hostname)
    return host
