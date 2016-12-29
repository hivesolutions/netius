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

import os
import math
import socket

import netius

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

DEFAULT_PLACES = 3
""" The default number of places (digits) that are going
to be used for the string representation in the round
based conversion of size units to be performed """

_HOST = None
""" The globally cached value for the current hostname,
this value is used to avoid an excessive blocking in the
get host by name call, as it is a blocking call """

def cstring(value):
    index = value.index("\0")
    if index == -1: return value
    return value[:index]

def chunks(sequence, count):
    for index in range(0, len(sequence), count):
        yield sequence[index:index + count]

def header_down(name):
    values = name.split("-")
    values = [value.lower() for value in values]
    return "-".join(values)

def header_up(name):
    values = name.split("-")
    values = [value.title() for value in values]
    return "-".join(values)

def is_ip4(address):
    address_p = address.split(".", 4)
    if not len(address_p) == 4: return False
    for part in address_p:
        try: part_i = int(part)
        except ValueError: return False
        if part_i < 0: return False
        if part_i > 255: return False
    return True

def is_ip6(address):
    if is_ip4(address): return False
    return True

def assert_ip4(address, allowed, default = True):
    if not allowed: return default
    for item in allowed:
        is_subnet = "/" in item
        if is_subnet: valid = in_subnet_ip4(address, item)
        else: valid = address == item
        if not valid: continue
        return True
    return False

def in_subnet_ip4(address, subnet):
    subnet, length = subnet.split("/", 1)
    size_i = 32 - int(length)
    address_a = ip4_to_addr(address)
    subnet_a = ip4_to_addr(subnet)
    limit_a = subnet_a + pow(2, size_i)
    in_subnet = (address_a & subnet_a) == subnet_a
    in_subnet &= address_a < limit_a
    return in_subnet

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

def string_to_bits(value):
    return bin(netius.legacy.reduce(lambda x, y : (x << 8) + y, (netius.legacy.ord(c) for c in value), 1))[3:]

def integer_to_bytes(number, length = 0):
    if not type(number) in netius.legacy.INTEGERS:
        raise netius.DataError("Invalid data type")

    bytes = []
    number = abs(number)

    while number > 0:
        bytes.append(chr(number & 0xff))
        number >>= 8

    remaining = length - len(bytes)
    remaining = 0 if remaining < 0 else remaining
    for _index in range(remaining): bytes.append("\x00")

    bytes = reversed(bytes)
    bytes_s = "".join(bytes)
    bytes_s = netius.legacy.bytes(bytes_s)

    return bytes_s

def bytes_to_integer(bytes):
    if not type(bytes) == netius.legacy.BYTES:
        raise netius.DataError("Invalid data type")

    number = 0
    for byte in bytes: number = (number << 8) | netius.legacy.ord(byte)
    return number

def random_integer(number_bits):
    """
    Generates a random integer of approximately the
    size of the provided number bits bits rounded up
    to whole bytes.

    :type number_bits: int
    :param number_bits: The number of bits of the generated
    random integer, this value will be used as the basis
    for the calculus of the required bytes.
    :rtype: int
    :return: The generated random integer, should be provided
    with the requested size.
    """

    # calculates the number of bytes to represent the number
    # by dividing the number of bits by a byte and then rounding
    # the value to the next integer value
    number_bytes = math.ceil(number_bits / 8.0)
    number_bytes = int(number_bytes)

    # generates a random data string with the specified
    # number of bytes in length
    random_data = os.urandom(number_bytes)

    # converts the random data into an integer and then
    # makes sure the last bit of the value is correctly
    # filled with data, and returns it to the caller method
    random_integer = bytes_to_integer(random_data)
    random_integer |= 1 << (number_bits - 1)
    return random_integer

def host(default = "127.0.0.1"):
    """
    Retrieves the host for the current machine,
    typically this would be the ipv4 address of
    the main network interface.

    No result type are guaranteed and a local address
    (eg: 127.0.0.1) may be returned instead.

    The returned value is cached to avoid multiple
    blocking calls from blocking the processor.

    :type default: String
    :param default: The default value that is going to
    be returned in case no resolution is possible, take
    into account that this result is going to be cached.
    :rtype: Strong
    :return: The string that contains the host address
    as defined by specification for the current machine.
    """

    global _HOST
    if _HOST: return _HOST
    hostname = socket.gethostname()
    try: _HOST = socket.gethostbyname(hostname)
    except socket.gaierror: _HOST = default
    is_unicode = type(_HOST) == netius.legacy.OLD_UNICODE
    if is_unicode: _HOST = _HOST.encode("utf-8")
    return _HOST

def hostname():
    """
    The name as a simple string o the name of the current
    local machine. This value may or may not be a fully
    qualified domain name for the machine.

    The result of this function call is unpredictable and
    should not be trusted for critical operations.

    :rtype: String
    :return: The name as a string of the current local
    machine, the definition of this value varies.
    """

    return socket.gethostname()

def size_round_unit(
    size_value,
    minimum = DEFAULT_MINIMUM,
    places = DEFAULT_PLACES,
    reduce = True,
    space = False,
    depth = 0
):
    """
    Rounds the size unit, returning a string representation
    of the value with a good rounding precision.
    This method should be used to round data sizing units.

    Note that using the places parameter it's possible to control
    the number of digits (including decimal places) of the
    number that is going to be "generated".

    :type size_value: int/float
    :param size_value: The current size value (in bytes).
    :type minimum: int
    :param minimum: The minimum value to be used.
    :type places: int
    :param places: The target number of digits to be used for
    describing the value to be used for output, this is going
    to be used to calculate the proper number of decimal places.
    :type reduce: bool
    :param reduce: If the final string value should be reduced
    meaning that right decimal zeros should be removed as they
    represent an extra unused value.
    :type space: bool
    :param space: If a space character must be used dividing
    the value from the unit symbol.
    :type depth: int
    :param depth: The current iteration depth value.
    :rtype: String
    :return: The string representation of the data size
    value in a simplified manner (unit).
    """

    # in case the current size value is acceptable (less than
    # the minimum) this is the final iteration and the final
    # string representation is going to be created
    if size_value < minimum:
        # calculates the target number of decimal places taking
        # into account the size (in digits) of the current size
        # value, this may never be a negative number
        log_value = size_value and math.log10(size_value)
        digits = int(log_value) + 1
        places = places - digits
        places = places if places > 0 else 0

        # creates the proper format string that is going to
        # be used in the creation of the proper float value
        # according to the calculated number of places
        format = "%%.%df" % places

        # rounds the size value, then converts the rounded
        # size value into a string based representation
        size_value = round(size_value, places)
        size_value_s = format % size_value

        # forces the reduce flag when the depth is zero, meaning
        # that an integer value will never be decimal, this is
        # required to avoid strange results for depth zero
        reduce = reduce or depth == 0

        # in case the dot value is not present in the size value
        # string adds it to the end otherwise an issue may occur
        # while removing extra padding characters for reduce
        if reduce and not "." in size_value_s: size_value_s += "."

        # strips the value from zero appended to the right and
        # then strips the value also from a possible decimal
        # point value that may be included in it, this is only
        # performed in case the reduce flag is enabled
        if reduce: size_value_s = size_value_s.rstrip("0")
        if reduce: size_value_s = size_value_s.rstrip(".")

        # retrieves the size unit (string mode) for the current
        # depth according to the provided map
        size_unit = SIZE_UNITS_LIST[depth]

        # retrieves the appropriate separator based
        # on the value of the space flag
        separator = space and " " or ""

        # creates the size value string appending the rounded
        # size value string and the size unit and returns it
        # to the caller method as the size value string
        size_value_string = size_value_s + separator + size_unit
        return size_value_string

    # otherwise the value is not acceptable
    # and a new iteration must be ran
    else:
        # re-calculates the new size value, increments the depth
        # and runs the size round unit again with the new values
        new_size_value = float(size_value) / SIZE_UNIT_COEFFICIENT
        new_depth = depth + 1
        return size_round_unit(
            new_size_value,
            minimum = minimum,
            places = places,
            reduce = reduce,
            space = space,
            depth = new_depth
        )

def verify(condition, message = None):
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
    """

    if condition: return
    raise netius.AssertionError(message or "Assertion Error")
