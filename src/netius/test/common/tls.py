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
import netius.common

from netius.common import tls


class TLSContextDictTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.owner = self._make_owner()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_init(self):
        self._store("first.com")

        contexts = tls.LetsEncryptDict(
            self.owner, ["first.com", "second.com"], letse_path=self.base
        )

        # only the domain whose certificate and key are both in place gets a
        # context, the one that is missing them being skipped
        self.assertEqual("first.com" in contexts, True)
        self.assertEqual("second.com" in contexts, False)

        # every domain that was asked for is remembered, so that a reload is
        # able to pick up the ones whose files appear later on
        self.assertEqual(contexts.domains, set(["first.com", "second.com"]))

    def test_reload(self):
        self._store("first.com")
        contexts = tls.LetsEncryptDict(self.owner, ["first.com"], letse_path=self.base)
        context = contexts["first.com"][0]

        # a reload that finds no change at all rebuilds nothing, so the very
        # same context keeps being served for the domain
        self.assertEqual(contexts.reload(), False)
        self.assertEqual(contexts["first.com"][0], context)

    def test_reload_changed(self):
        self._store("first.com")
        contexts = tls.LetsEncryptDict(self.owner, ["first.com"], letse_path=self.base)
        context = contexts["first.com"][0]

        # the certificate is renewed, which the modification time of it is
        # what signals to the reload
        self._store("first.com", mtime=contexts.mtimes["first.com"] + 10)

        self.assertEqual(contexts.reload(), True)
        self.assertNotEqual(contexts["first.com"][0], context)

    def test_reload_added(self):
        contexts = tls.LetsEncryptDict(self.owner, ["first.com"], letse_path=self.base)

        # the domain had no files when the dictionary was built, so it got
        # no context of its own at that moment
        self.assertEqual("first.com" in contexts, False)

        self._store("first.com")

        # once the certificate is issued the reload picks it up, without the
        # process having to be restarted for it
        self.assertEqual(contexts.reload(), True)
        self.assertEqual("first.com" in contexts, True)

    def test_has_definition(self):
        contexts = tls.LetsEncryptDict(self.owner, [], letse_path=self.base)

        # a domain with neither of the files, and one with only the
        # certificate, are both incomplete and so not usable
        self.assertEqual(contexts.has_definition("first.com"), False)

        os.makedirs(os.path.join(self.base, "first.com"))
        self._write(os.path.join(self.base, "first.com", "fullchain.pem"))
        self.assertEqual(contexts.has_definition("first.com"), False)

        self._write(os.path.join(self.base, "first.com", "privkey.pem"))
        self.assertEqual(contexts.has_definition("first.com"), True)

    def test_cer_path(self):
        contexts = tls.TLSContextDict(self.owner, [])

        # the base dictionary defines no layout of its own, so the paths of
        # a domain are the responsibility of the implementation that follows
        self.assertRaises(netius.NotImplemented, contexts.cer_path, "first.com")
        self.assertRaises(netius.NotImplemented, contexts.key_path, "first.com")

    def test_cer_path_letse(self):
        contexts = tls.LetsEncryptDict(self.owner, [], letse_path=self.base)

        # the layout is the one that certbot produces, with the files of a
        # domain under a directory that is named after it
        self.assertEqual(
            contexts.cer_path("first.com"),
            os.path.join(self.base, "first.com", "fullchain.pem"),
        )
        self.assertEqual(
            contexts.key_path("first.com"),
            os.path.join(self.base, "first.com", "privkey.pem"),
        )

    def _make_owner(self):
        # builds an owner stand-in that answers the environment probe and
        # hands out a new context for every request, so that the rebuilding
        # of one may be observed by identity
        class Owner(object):

            def get_env(self, name, default, cast=None):
                return default

            def _ssl_ctx(self, values, secure=1):
                return object()

        return Owner()

    def _store(self, domain, mtime=None):
        domain_path = os.path.join(self.base, domain)
        if not os.path.exists(domain_path):
            os.makedirs(domain_path)
        for name in ("fullchain.pem", "privkey.pem"):
            path = os.path.join(domain_path, name)
            self._write(path)
            if mtime == None:
                continue
            os.utime(path, (mtime, mtime))

    def _write(self, path):
        file = open(path, "wb")
        try:
            file.write(b"contents")
        finally:
            file.close()
