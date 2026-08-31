#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius.common

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class CalcTest(unittest.TestCase):

    def test_prime(self):
        result = netius.common.calc.prime(16)

        # the number that is generated is as wide as it was asked for
        # and is one that passes the test of primality
        self.assertEqual(result.bit_length(), 16)
        self.assertEqual(netius.common.calc.is_prime(result), True)

        # the generated value is always an odd one, as an even number
        # is never a prime beyond the two
        self.assertEqual(result & 1, 1)

    def test_is_prime(self):
        # a prime is never turned away, as every base of it agrees with
        # the symbol, so this side of the test carries no chance at all
        for number in (3, 7, 13, 97, 1009):
            self.assertEqual(netius.common.calc.is_prime(number), True)

    def test_is_prime_composite(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the base that the test draws is what decides it, so it is held
        # at one that witnesses each of the values rather than left to
        # the chance of a draw, which no run should ever depend on
        with mock.patch.object(
            netius.common.calc, "random_integer_interval", self._base
        ):
            # a number that carries a factor of its own is never a prime,
            # the carmichael one being the case that fools the naive tests
            for number in (9, 15, 21, 561):
                self.assertEqual(netius.common.calc.is_prime(number), False)

    def test_relatively_prime(self):
        self.assertEqual(netius.common.calc.relatively_prime(9, 28), True)

        # the two values share a factor of three, so there is a divisor
        # of them that is greater than the one
        self.assertEqual(netius.common.calc.relatively_prime(12, 18), False)

    def test_gcd(self):
        self.assertEqual(netius.common.calc.gcd(48, 18), 6)

        # the order of the values does not change the divisor, as the
        # smaller of them is moved to the front before the reduction
        self.assertEqual(netius.common.calc.gcd(18, 48), 6)

        # a zero has no divisor of its own, so the other value is the
        # one that answers for the pair
        self.assertEqual(netius.common.calc.gcd(7, 0), 7)
        self.assertEqual(netius.common.calc.gcd(0, 7), 7)

    def test_egcd(self):
        d, x, y = netius.common.calc.egcd(240, 46)

        # the divisor is the one of the plain algorithm and the two
        # coefficients answer the identity that gives them their name
        self.assertEqual(d, netius.common.calc.gcd(240, 46))
        self.assertEqual(240 * x + 46 * y, d)

        d, x, y = netius.common.calc.egcd(17, 5)

        self.assertEqual(d, 1)
        self.assertEqual(17 * x + 5 * y, 1)

        # with a zero there is nothing left to reduce, so the value
        # itself is the divisor and the coefficients are settled
        self.assertEqual(netius.common.calc.egcd(7, 0), (7, 1, 0))

    def test_modinv(self):
        result = netius.common.calc.modinv(3, 11)

        # the inverse is the value that brings the product back to the
        # one under the modulus that was asked for
        self.assertEqual((3 * result) % 11, 1)

        result = netius.common.calc.modinv(17, 43)

        self.assertEqual((17 * result) % 43, 1)

    def test_modinv_missing(self):
        # the two values share a factor, so there is no value that
        # inverts one of them under the other
        self.assertRaises(netius.DataError, lambda: netius.common.calc.modinv(4, 8))

    def test_random_integer_interval(self):
        for _index in range(16):
            result = netius.common.calc.random_integer_interval(10, 100)

            # the value that is generated never leaves the interval that
            # was named, whatever the number of bits that built it
            self.assertEqual(result >= 10, True)
            self.assertEqual(result < 100, True)

    def test_random_primality(self):
        self.assertEqual(netius.common.calc.random_primality(97, 6), True)

    def test_random_primality_composite(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(
            netius.common.calc, "random_integer_interval", self._base
        ):
            # a witness of the non primality is found for a value that is
            # not a prime, which ends the test right away
            self.assertEqual(netius.common.calc.random_primality(561, 6), False)

    def test_jacobi_witness(self):
        result = netius.common.jacobi_witness(12, 2)
        self.assertEqual(result, True)

        result = netius.common.jacobi_witness(3, 2)
        self.assertEqual(result, False)

    def test_jacobi_witness_shared(self):
        # a base that shares a factor with the value under test leaves no
        # residue at all, which is a proof of its own that the value is
        # not a prime, so such a base is a witness and never a liar
        for number in (9, 15, 21, 561):
            self.assertEqual(netius.common.jacobi_witness(3, number), True)

    def test_jacobi(self):
        # the residues of three and of five, which are the values that
        # the definition of the symbol gives for them
        self.assertEqual(netius.common.calc.jacobi(1, 3), 1)
        self.assertEqual(netius.common.calc.jacobi(2, 3), -1)
        self.assertEqual(netius.common.calc.jacobi(4, 5), 1)
        self.assertEqual(netius.common.calc.jacobi(3, 5), -1)
        self.assertEqual(netius.common.calc.jacobi(2, 7), 1)

    def test_jacobi_shared(self):
        # a value that is a multiple of the other leaves no residue at
        # all, which is the zero of the symbol
        self.assertEqual(netius.common.calc.jacobi(9, 3), 0)

        # the two values share a factor without one being a multiple of
        # the other, which is a zero of the symbol as well
        self.assertEqual(netius.common.calc.jacobi(3, 9), 0)
        self.assertEqual(netius.common.calc.jacobi(6, 9), 0)
        self.assertEqual(netius.common.calc.jacobi(10, 15), 0)

    def _base(self, minimum, maximum):
        # stands in for the drawing of a base, giving the one that
        # witnesses every value that the cases put under test
        return 3

    def test_ceil_integer(self):
        result = netius.common.calc.ceil_integer(1.2)

        # the value is rounded up and given back as an integer, so that
        # it may be used where only one of them is taken
        self.assertEqual(result, 2)
        self.assertEqual(netius.legacy.is_string(result), False)
        self.assertEqual(type(result) in netius.legacy.INTEGERS, True)

        # a value that is already a round one is kept as it is, instead
        # of being pushed to the one that follows it
        self.assertEqual(netius.common.calc.ceil_integer(2.0), 2)
        self.assertEqual(netius.common.calc.ceil_integer(-1.2), -1)
