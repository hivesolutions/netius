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

import os
import tempfile
import unittest

import netius.common

from netius.base import common


class RSATest(unittest.TestCase):

    def test_open_private_key(self):
        private_key = netius.common.open_private_key(self._key_path())

        # the key that ships with the package is a complete one, carrying
        # both of the primes and the values derived from them
        self.assertEqual(private_key["bits"], 2048)
        self.assertEqual(private_key["public_exponent"], 65537)
        for name in ("modulus", "private_exponent", "prime_1", "prime_2"):
            self.assertNotEqual(private_key[name], None)

    def test_open_private_key_data(self):
        file = open(self._key_path(), "rb")
        try:
            data = file.read()
        finally:
            file.close()

        # a key may be read from a payload as much as from a file, which is
        # what a key that travels in the environment requires, the armour of
        # it being taken off before the structure is read
        data = netius.common.open_pem_data(data)
        private_key = netius.common.open_private_key_data(data)
        self.assertEqual(private_key["bits"], 2048)

    def test_write_private_key(self):
        private_key = netius.common.open_private_key(self._key_path())

        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            netius.common.write_private_key(path, private_key)
            result = netius.common.open_private_key(path)
        finally:
            os.remove(path)

        # a key that is written and read back is the one that was given, so
        # that the encoding of it loses nothing
        self.assertEqual(result, private_key)

    def test_write_public_key(self):
        private_key = netius.common.open_private_key(self._key_path())
        public_key = netius.common.private_to_public(private_key)

        # only the two values that may be published are part of the public
        # form, the ones that would give the private one away being dropped
        self.assertEqual(sorted(public_key.keys()), ["modulus", "public_exponent"])

        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            netius.common.write_public_key(path, public_key)
            result = netius.common.open_public_key(path)
        finally:
            os.remove(path)

        # the two values that were written are the ones read back, the size
        # of the key being derived from the modulus on the way in
        self.assertEqual(result["modulus"], public_key["modulus"])
        self.assertEqual(result["public_exponent"], public_key["public_exponent"])
        self.assertEqual(result["bits"], 2048)

    def test_pem_to_der(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            netius.common.pem_to_der(self._key_path(), path)
            file = open(path, "rb")
            try:
                data = file.read()
            finally:
                file.close()
        finally:
            os.remove(path)

        # the binary form carries no armour of its own, so it starts with the
        # sequence that the encoding of the structure leads with
        self.assertEqual(data[:1], b"\x30")
        self.assertNotEqual(len(data), 0)

    def test_assert_private(self):
        private_key = netius.common.open_private_key(self._key_path())

        # a key whose values agree with each other holds together, which is
        # what the verification of it means
        self.assertEqual(
            netius.common.assert_private(private_key, number_bits=2048), None
        )

    def test_assert_private_broken(self):
        # every one of the derived values is verified against the primes, so
        # a key that carries a wrong one is refused
        for name in ("modulus", "exponent_1", "exponent_2", "coefficient"):
            private_key = netius.common.open_private_key(self._key_path())
            private_key[name] += 1

            self.assertRaises(
                netius.AssertionError, netius.common.assert_private, private_key
            )

        # and so is one whose size is not the one that was asked for, as the
        # strength of it would not be the expected one
        private_key = netius.common.open_private_key(self._key_path())

        self.assertRaises(
            netius.AssertionError,
            netius.common.assert_private,
            private_key,
            1024,
        )

    def test_rsa_private(self):
        # a small key is the one built, as the cost of the generation grows
        # steeply with the size and the paths taken are the same ones
        private_key = netius.common.rsa_private(256)

        self.assertEqual(private_key["bits"], 256)
        self.assertEqual(private_key["version"], 0)
        self.assertEqual(
            private_key["modulus"],
            private_key["prime_1"] * private_key["prime_2"],
        )

        # the key that comes out of the generation holds together, which is
        # the whole of what the generation is for
        self.assertEqual(
            netius.common.assert_private(private_key, number_bits=256), None
        )

    def test_rsa_primes(self):
        prime_1, prime_2 = netius.common.rsa_primes(64)

        # both of the primes are of the size that was asked for and they are
        # not the same one, as a key built from a square is trivially broken
        self.assertEqual(netius.common.rsa_bits(prime_1), 64)
        self.assertEqual(netius.common.rsa_bits(prime_2), 64)
        self.assertNotEqual(prime_1, prime_2)

    def test_rsa_exponents(self):
        prime_1, prime_2 = netius.common.rsa_primes(64)
        public_exponent, private_exponent = netius.common.rsa_exponents(
            prime_1, prime_2, 64
        )

        # the public exponent is the one that is conventionally used, and the
        # private one is its inverse under the totient of the modulus
        self.assertEqual(public_exponent, 65537)

        totient = (prime_1 - 1) * (prime_2 - 1)
        self.assertEqual(public_exponent * private_exponent % totient, 1)

    def test_rsa_sign(self):
        private_key = netius.common.open_private_key(self._key_path())
        public_key = netius.common.private_to_public(private_key)

        signature = netius.common.rsa_sign(b"Hello World", private_key)
        result = netius.common.rsa_verify(signature, public_key)

        # what was signed with the private key is recovered with the public
        # one, the padding of the front being dropped by the caller
        self.assertEqual(result.lstrip(b"\0"), b"Hello World")

    def test_rsa_crypt_invalid(self):
        private_key = netius.common.open_private_key(self._key_path())

        # a value that is not a number cannot be raised to a power, so it is
        # refused instead of failing further down
        self.assertRaises(
            TypeError, netius.common.rsa_crypt, "value", 65537, private_key["modulus"]
        )

        # one that is larger than the modulus could not be recovered, as the
        # arithmetic of it happens under that modulus
        self.assertRaises(
            OverflowError,
            netius.common.rsa_crypt,
            private_key["modulus"] ** 2,
            65537,
            private_key["modulus"],
        )

    def _key_path(self):
        # the private key that ships with the package, used so that no key
        # has to be generated for the cases that need a large one
        return os.path.join(os.path.dirname(common.__file__), "extras", "net.key")

    def test_rsa_crypt(self):
        number = 87521618088882533792115812
        exponent = 36510217105848231284079274231564906186307560780534247831648648175045225318561460162728717234530889577546652846221026215879731017938647097448942278391102846302059960991452569135619524616218782987723300816771871234796688783233883245022643852052966438968493009984572453713313165894751634193657763224930190644678
        modulus = 96932149016243683313202436463884391894442557094585987087679466243837140612162774296465245821614029972754395721149915741918184810668111591608828515674917153485786305039311784635247807314685477198540013198150331209390992944093549127578416635618276838812255204836659792055944277295324948158500484872595001982643
        expected = 77582017281983556473055444885999671275845710142539492742164750164915723397427639169767703318619952155855354799282839237590830862415463205074741285319459521280599333234352017115848949043330478158462953508557273618244552244536252761419615268258174029143566887421875425091295665101338067462122465562948190873420
        result = netius.common.rsa_crypt(number, exponent, modulus)
        self.assertEqual(result, expected)
