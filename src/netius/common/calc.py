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

import math
import random

import netius

import util

def prime(number_bits):
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

def is_prime(number):
    return random_primality(number, 5)

def relatively_prime(first, second):
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
    @param first: The first number to obtain the greatest
    common divisor using the euclidean algorithm.
    @type second: int
    @param second: The second number to obtain the greatest
    common divisor using the euclidean algorithm.
    @rtype: int
    @return: The greatest common divisor between both values.
    @see: http://en.wikipedia.org/wiki/Euclidean_algorithm
    """

    # in case the p value is smaller than the q value
    # reveses the order of the arguments and re-computes
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

def egcd(first, second):
    """
    Extended version of the greatest common divisor created
    by Euclid. Computes additional coefficients of the
    Bézout's identity.

    @type first: int
    @param first: The first number to obtain the greatest
    common divisor using the euclidean algorithm.
    @type second: int
    @param second: The second number to obtain the greatest
    common divisor using the euclidean algorithm.
    @rtype: Tuple
    @return: A tuple containing the various coefficients calculated
    for this extended approach of the greatest common divisor.
    @see: http://en.wikipedia.org/wiki/Extended_Euclidean_algorithm
    """

    if second == 0: return (first, 1, 0)

    q = abs(first % second)
    r = long(first / second)
    d, k, l = egcd(second, q)

    return (d, l, k - l * r)

def modinv(first, second):
    """
    Uses the extended greatest common divisor algorithm to compute
    the modulus of an inverted value against another.

    The execution of this method is equivalent to (1 / first mod second)
    using mathematical terms.

    @type first: int
    @param first: The first value, that is going to be inverted before
    the modulus operation is performed.
    @type second: int
    @param second: The second value that is going to be used as the basis
    for the modulus operation.
    @rtype: int
    @return: The result of the computation of inverted modulus according
    to its mathematical definition.
    """

    d, l, _e = egcd(first, second)
    if d != 1: raise netius.DataError("Modular inverse does not exist")
    else: return l % second





def random_integer_interval(min_value, max_value):
    # sets the default minimum number of bits, even if the
    # range is too small
    max_number_bits = 32

    # calculates the range of the random numbers
    # to generate
    range = max_value - min_value

    # converts the range into bits
    range_bits = math.log(range, 2)

    # converts the range into bytes
    range_bytes = ceil_integer(range_bits / 8.0)

    # converts the range into bits, but verifies that there
    # is at least a minimum number of bits
    range_bits = max(range_bytes * 8, max_number_bits * 2)

    # generates the random number of bits to be used
    number_bits = random.randint(max_number_bits, range_bits)

    # generates the random integer with the number of bits generated
    # and applying modulo of the range
    random_base_value = util.random_integer(number_bits) % range

    # creates the random value adding the minimum value to the
    # random base value
    random_value = random_base_value + min_value

    # returns the random value
    return random_value

def random_primality(number, k):
    # the property of the jacobi witness function
    q = 0.5

    # calculates t to ha
    t = ceil_integer(k / math.log(1 / q, 2))

    # iterates over the range of t value plus one
    for _index in range(t + 1):
        # generates a random number in the interval
        random_number = random_integer_interval(1, number - 1)

        # in case the random number is a jacobi witness
        # then the number is not prime
        if jacobi_witness(random_number, number):
            # returns false (invalid)
            return False

    # returns true (valid)
    return True

def jacobi_witness(x, n):
    """
    Checks if the given x value is witness to n value
    non primality.
    This check is made according to euler's theorem.

    @type x: int
    @param x: The value to be checked for witness.
    @type n: int
    @param n: The value to be checked for primality.
    @rtype: bool
    @return: The result of the checking.
    """

    # calculates the j value from jacobi
    j = jacobi(x, n) % n

    # calculates the f value
    f = pow(x, (n - 1) / 2, n)

    # in case the j value and the f value are the same,
    # returns invalid as it is not considered to be a valid
    # witness, otherwise returns invalid (is a witness)
    if j == f: return False
    else: return True

def jacobi(a, b):
    """
    Calculates the value of the jacobi symbol, using the
    given a and b values.

    @type a: int
    @param a: The a value.
    @type b: int
    @param b: The b value.
    @rtype: int
    @return: The calculated jacobi symbol.
    @see: http://en.wikipedia.org/wiki/Jacobi_symbol
    """

    if a % b == 0: return 0

    result = 1

    while a > 1:
        if a & 1:
            if ((a - 1) * (b - 1) >> 2) & 1: result = -result

            b, a = a, b % a
        else:
            if ((b ** 2 - 1) >> 3) & 1: result = -result
            a >>= 1

    return result

def ceil_integer(value):
    """
    Retrieves the ceil of a value and then converts it
    into a valid integer for integer computation.
    The conversion to integer ensures that the ceil
    is compatible with certain (integer) operations.

    @type value: int
    @param value: The value to apply the ceil.
    @rtype: int
    @return: The ceil of the given value "casted" as an
    integer.
    """

    value = math.ceil(value)
    value = int(value)
    return value
