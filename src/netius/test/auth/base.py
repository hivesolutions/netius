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
import shutil
import tempfile
import unittest

import netius
import netius.auth


class AuthTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_auth(self):
        # the base class provides no authentication of its own, so the
        # class level method must refuse any attempt made against it
        self.assertRaises(netius.NotImplemented, netius.auth.Auth.auth)

    def test_meta(self):
        self.assertEqual(netius.auth.Auth.meta(), {})

    def test_auth_assert(self):
        self.assertEqual(netius.auth.AllowAuth.auth_assert(), None)

        # an authentication that does not succeed is turned into a
        # security error, instead of a simple invalid return value
        self.assertRaises(netius.SecurityError, netius.auth.DenyAuth.auth_assert)
        self.assertRaises(netius.NotImplemented, netius.auth.Auth.auth_assert)

    def test_verify(self):
        encoded = netius.auth.Auth.generate("secret")

        self.assertEqual(netius.auth.Auth.verify(encoded, "secret"), True)
        self.assertEqual(netius.auth.Auth.verify(encoded, "secret_"), False)

        # a value that carries no salt is verified against the digest of
        # the password alone, as there's nothing to append to it
        encoded = netius.auth.Auth.generate("secret", salt=None)

        self.assertEqual(netius.auth.Auth.verify(encoded, "secret"), True)
        self.assertEqual(netius.auth.Auth.verify(encoded, "secret_"), False)

        # the type of the digest is normalized before the hash is built,
        # so that an upper cased one is still a valid value
        self.assertEqual(netius.auth.Auth.verify(encoded.upper(), "secret"), False)
        self.assertEqual(
            netius.auth.Auth.verify("SHA256:" + encoded.split(":")[1], "secret"), True
        )

        # the plain type is the only one for which the two values are
        # compared literally, with no digest being computed for them
        self.assertEqual(netius.auth.Auth.verify("secret", "secret"), True)
        self.assertEqual(netius.auth.Auth.verify("secret", "secret_"), False)

        # the salt takes part in the digest, so the password on its own
        # does not verify against a value that was salted
        encoded = netius.auth.Auth.generate("secret", salt="extra")

        self.assertEqual(netius.auth.Auth.verify(encoded, "secret"), True)
        self.assertEqual(
            netius.auth.Auth.verify(encoded, "secretextra"),
            False,
        )

    def test_generate(self):
        encoded = netius.auth.Auth.generate("secret")
        type, salt, digest = encoded.split(":")

        self.assertEqual(type, "sha256")
        self.assertEqual(salt, "6e6574697573")
        self.assertEqual(len(digest), 64)

        # the plain type gives the password back unchanged, as no digest
        # is ever computed for that kind of value
        self.assertEqual(netius.auth.Auth.generate("secret", type="plain"), "secret")

        # a value generated without salt carries only the type and the
        # digest, there being no salt to place in between them
        encoded = netius.auth.Auth.generate("secret", salt=None)

        self.assertEqual(encoded.count(":"), 1)
        self.assertEqual(encoded.startswith("sha256:"), True)

        # the type drives the hash that is used, so a different one
        # produces a digest of a different length
        encoded = netius.auth.Auth.generate("secret", type="md5", salt=None)

        self.assertEqual(len(encoded.split(":")[1]), 32)

        # the salt is part of what is hashed, meaning that the same
        # password salted differently gives a different digest
        first = netius.auth.Auth.generate("secret", salt="first")
        second = netius.auth.Auth.generate("secret", salt="second")

        self.assertNotEqual(first.split(":")[2], second.split(":")[2])

    def test_unpack(self):
        self.assertEqual(
            netius.auth.Auth.unpack("secret"), ("plain", None, None, "secret")
        )
        self.assertEqual(
            netius.auth.Auth.unpack("sha256:digest"), ("sha256", None, "digest", None)
        )
        self.assertEqual(
            netius.auth.Auth.unpack("sha256:6e6574697573:digest"),
            ("sha256", "netius", "digest", None),
        )

        # a plain password that carries the separator is still unpacked
        # as a plain one, instead of raising an unexpected exception
        self.assertEqual(
            netius.auth.Auth.unpack("plain:secret"),
            ("plain", None, "secret", "plain:secret"),
        )

        # the value that is generated must be the exact reverse of the
        # one that is unpacked, closing the round trip of the two
        encoded = netius.auth.Auth.generate("secret")
        type, salt, digest, plain = netius.auth.Auth.unpack(encoded)

        self.assertEqual(type, "sha256")
        self.assertEqual(salt, "netius")
        self.assertEqual(plain, None)
        self.assertEqual(encoded.endswith(digest), True)

    def test_get_file(self):
        path = self._store("simple.txt", b"hello world")

        self.assertEqual(netius.auth.Auth.get_file(path), b"hello world")

        # the encoding turns the byte based contents into a string one,
        # decoded according to the encoding that was requested
        self.assertEqual(
            netius.auth.Auth.get_file(path, encoding="utf-8"), "hello world"
        )

        # the contents are only remembered when the cache flag is set, so
        # that a change to the file is still visible for the other reads
        self.assertEqual(netius.auth.Auth.get_file(path, cache=True), b"hello world")

        self._store("simple.txt", b"hello mundo")

        self.assertEqual(netius.auth.Auth.get_file(path), b"hello mundo")
        self.assertEqual(netius.auth.Auth.get_file(path, cache=True), b"hello world")

        # a file that is not there raises, as there are no contents to
        # be given back for such a path
        self.assertRaises(
            IOError, netius.auth.Auth.get_file, os.path.join(self.base, "missing.txt")
        )

    def test_is_simple(self):
        self.assertEqual(netius.auth.Auth.is_simple(), False)
        self.assertEqual(netius.auth.AllowAuth.is_simple(), True)

    def test_auth_i(self):
        auth = netius.auth.AllowAuth()

        self.assertEqual(auth.auth_i(), True)

        # the constructor binds the instance method as the authentication
        # one, so that the instance shadows the class level method
        self.assertEqual(auth.auth(), True)

        auth = netius.auth.DenyAuth()

        self.assertEqual(auth.auth_i(), False)

        auth = netius.auth.Auth()

        self.assertRaises(netius.NotImplemented, auth.auth_i)

    def test_auth_assert_i(self):
        auth = netius.auth.AllowAuth()

        self.assertEqual(auth.auth_assert_i(), None)
        self.assertEqual(auth.auth_assert(), None)

        auth = netius.auth.DenyAuth()

        self.assertRaises(netius.SecurityError, auth.auth_assert_i)
        self.assertRaises(netius.SecurityError, auth.auth_assert)

    def test_is_simple_i(self):
        self.assertEqual(netius.auth.Auth().is_simple_i(), False)
        self.assertEqual(netius.auth.AllowAuth().is_simple_i(), True)

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return path
