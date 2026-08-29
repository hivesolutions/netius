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

import netius.auth


class PasswdAuthTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_auth(self):
        path = self._store("simple", "root:%s\n" % netius.auth.Auth.generate("root"))

        self.assertEqual(netius.auth.PasswdAuth.auth("root", "root", path=path), True)
        self.assertEqual(netius.auth.PasswdAuth.auth("root", "root_", path=path), False)

        # a username that is not part of the file is refused instead of
        # raising, as the lookup gives no password for it
        self.assertEqual(netius.auth.PasswdAuth.auth("dummy", "root", path=path), False)

        # the password of the file may also be a plain one, in which case
        # the two values are compared literally
        path = self._store("plain", "root:root\n")

        self.assertEqual(netius.auth.PasswdAuth.auth("root", "root", path=path), True)
        self.assertEqual(netius.auth.PasswdAuth.auth("root", "root_", path=path), False)

    def test_get_passwd(self):
        path = self._store("simple", "root:first\n\nextra:second\n")

        passwd = netius.auth.PasswdAuth.get_passwd(path, cache=False)

        # the empty line of the file is skipped, only the two lines that
        # carry a username taking part in the result
        self.assertEqual(passwd, dict(root="first", extra="second"))

        # only the first separator of the line splits it, so that a
        # password that carries one is not truncated by the parsing
        path = self._store("encoded", "root:sha256:6e6574697573:digest\n")

        passwd = netius.auth.PasswdAuth.get_passwd(path, cache=False)

        self.assertEqual(passwd["root"], "sha256:6e6574697573:digest")

        # the result is remembered when the cache flag is set, so a change
        # to the file is only visible for an uncached retrieval
        path = self._store("cached", "root:first\n")

        self.assertEqual(netius.auth.PasswdAuth.get_passwd(path)["root"], "first")

        self._store("cached", "root:second\n")

        self.assertEqual(netius.auth.PasswdAuth.get_passwd(path)["root"], "first")
        self.assertEqual(
            netius.auth.PasswdAuth.get_passwd(path, cache=False)["root"], "second"
        )

        # a file that is not there raises, as there's no set of passwords
        # to be built from such a path
        self.assertRaises(
            IOError,
            netius.auth.PasswdAuth.get_passwd,
            os.path.join(self.base, "missing"),
        )

    def test_auth_i(self):
        path = self._store("simple", "root:%s\n" % netius.auth.Auth.generate("root"))

        auth = netius.auth.PasswdAuth(path=path)

        # the path of the instance is the one used for the lookup, so
        # that no explicit path has to be given for the authentication
        self.assertEqual(auth.auth_i("root", "root"), True)
        self.assertEqual(auth.auth_i("root", "root_"), False)
        self.assertEqual(auth.auth("root", "root"), True)

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents.encode("utf-8"))
        finally:
            file.close()
        return path
