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

SIZE_UNITS_LIST = (
    "B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"
)
""" The size units list that contains the complete set of
units indexed by the depth they represent """

SIZE_UNIT_COEFFICIENT = 1024
""" The size unit coefficient as an integer value, this is
going to be used in each of the size steps as divisor """

DEFAULT_MINIMUM = 1024
""" The default minimum value meaning that this is the
maximum value that one integer value may have for the
size rounding operation to be performed """

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

def size_round_unit(
    size_value,
    minimum = DEFAULT_MINIMUM,
    space = False,
    depth = 0
):
    """
    Rounds the size unit, returning a string representation
    of the value with a good rounding precision.
    This method should be used to round data sizing units.

    @type size_value: int
    @param size_value: The current size value (in bytes).
    @type minimum: int
    @param minimum: The minimum value to be used.
    @type space: bool
    @param space: If a space character must be used dividing
    the value from the unit symbol.
    @type depth: int
    @param depth: The current iteration depth value.
    @rtype: String
    @return: The string representation of the data size
    value in a simplified manner (unit).
    """

    # in case the current size value is acceptable (less than
    # the minimum) this is the final iteration and the final
    # string representation is going to be created
    if size_value < minimum:
        # rounds the size value, then converts the rounded
        # size value into a string based representation
        rounded_size_value = int(size_value)
        rounded_size_value_string = str(rounded_size_value)

        # retrieves the size unit (string mode) for the current
        # depth according to the provided map
        size_unit = SIZE_UNITS_LIST[depth]

        # retrieves the appropriate separator based
        # on the value of the space flag
        separator = space and " " or ""

        # creates the size value string appending the rounded
        # size value string and the size unit and returns it
        # to the caller method as the size value string
        size_value_string = rounded_size_value_string + separator + size_unit
        return size_value_string

    # otherwise the value is not acceptable
    # and a new iteration must be ran
    else:
        # re-calculates the new size value, increments the depth
        # and runs the size round unit again with the new values
        new_size_value = size_value / SIZE_UNIT_COEFFICIENT
        new_depth = depth + 1
        return size_round_unit(
            new_size_value,
            minimum = minimum,
            space = space,
            depth = new_depth
        )
