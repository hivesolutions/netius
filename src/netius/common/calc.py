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

import util

def prime(self, number_bits):
    """
    Generates a prime number with the given number of bits
    in length. This is a brute force based generation as a
    random number is generated and then tested for primality.

    @type number_bits: int
    @param number_bits: The number of bits to be used in
    the prime number generation.
    @rtype: int
    @return: The generated prime number, that should have
    been verified for primality.
    """

    # iterates continuously, trying to find a large enough
    # prime number as requested by the call
    while True:
        # generates a random number and then makes sure that
        # it's an odd number (last bit to one)
        integer = util.random_integer(number_bits)
        integer |= 1

        # verifies if the generated integer value is a prime
        # using the primality testing strategy, and in case
        # it's breaks the current loop as a prime has been
        # found with the pre-defined number of bits
        if is_prime(integer): break

    # returns the (generated) and verified prime integer
    # to the caller method, may be used for exponent
    return integer

def is_prime(self, number):
    return self.random_primality(number, 5)

def relatively_prime(self, first, second):
    # retrieves the greatest common divisor between the
    # two values and verifies if the value is one, for
    # such situations they are "relative primes"
    divisor = gcd(first, second)
    return divisor == 1

def gcd(first, second):
    """
    Calculates the greatest common divisor of p value and q value.
    This method uses the classic euclidean algorithm.

    @type first: int
    @param first: The first prime number to obtain
    the greatest common divisor.
    @type second: int
    @param second: The second prime number to obtain
    the greatest common divisor.
    @rtype: int
    @return: The greatest common divisor between both values.
    """

    # in case the p value is smaller than
    # the q value
    if first < second: return gcd(second, first)

    # in case the q value is zero
    if second == 0:
        # returns the p value
        # because there is no division by zero
        return first

    # calculates the next "second" value that is going
    # to be used in next iteration and runs the next
    # iteration for those calculus
    next = abs(first % second)
    return gcd(second, next)
