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

import netius
import netius.sh.auth

try:
    import unittest.mock as mock
except ImportError:
    mock = None

DIGEST = "31b213469bee6fa17e07390e4f3124ef5fb320e7acd8eacbf58ed2bfde63db9a"

DIGEST_PLAIN = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

DIGEST_MD5 = "baddf52697306303627b97b2721e964a"


class SHAuthTest(unittest.TestCase):

    def test_generate(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._generate("hello")

        # the default hash is salted with the name of the library and the
        # salt travels in the digest, hexadecimal encoded, so that the
        # verification of a password is able to reproduce it
        self.assertEqual(result, "sha256:6e6574697573:%s\n" % DIGEST)

    def test_generate_type(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._generate("hello", "md5", "salt")

        self.assertEqual(result, "md5:73616c74:%s\n" % DIGEST_MD5)

    def test_generate_plain(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._generate("hello", "plain")

        # the plain type is not a hash at all and so the password is echoed
        # back without any kind of transformation being applied to it
        self.assertEqual(result, "hello\n")

    def test_generate_no_salt(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._generate("hello", "sha256", "")

        # an empty salt removes the middle component of the digest, meaning
        # that the password is hashed exactly as it has been provided
        self.assertEqual(result, "sha256:%s\n" % DIGEST_PLAIN)

    def _generate(self, *args, **kwargs):
        with mock.patch("sys.stdout", netius.legacy.StringIO()) as stdout:
            netius.sh.auth.generate(*args, **kwargs)
        return stdout.getvalue()
