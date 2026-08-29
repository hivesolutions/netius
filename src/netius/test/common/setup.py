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
import unittest

import netius.clients
import netius.common


class CommonTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.original = None

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        if not self.original:
            return
        netius.clients.HTTPClient.method_s = self.original
        self.original = None

    def test_ensure_setup(self):
        self._patch_result(dict(code=None, message="Connection closed"))

        # a download that never reaches a response must not break the setup
        # of the package, as the CA file is an optional resource
        self.assertEqual(netius.common.ensure_setup(), None)

    def test_ensure_ca(self):
        self._patch_result(dict(code=None, message="Connection closed"))
        self._store("test_present.ca", b"contents")

        try:
            netius.common.ensure_ca(path="test_present.ca")
            file = open("test_present.ca", "rb")
            try:
                data = file.read()
            finally:
                file.close()
        finally:
            os.unlink("test_present.ca")

        # a CA file that's already in place is not downloaded again, so the
        # contents that were there before are kept untouched
        self.assertEqual(data, b"contents")

    def test_ensure_ca_error(self):
        self._patch_result(dict(code=None, message="Connection closed"))

        try:
            netius.common.ensure_ca(path="test_missing.ca")
        except Exception as exception:
            message = str(exception)
        else:
            message = None

        # the failure of a download that never reached a response is reported
        # with the reason for it, instead of breaking while the message of
        # the error is being built (there's no status code for such a case)
        self.assertNotEqual(message, None)
        self.assertEqual("Error while downloading CA file" in message, True)
        self.assertEqual("Connection closed" in message, True)
        self.assertEqual(os.path.exists("test_missing.ca"), False)

    def test_ensure_ca_tolerant(self):
        self._patch_result(dict(code=404, message=None))

        # the tolerant mode swallows the failure, so that a caller for which
        # the CA file is optional is not broken by a download that fails
        self.assertEqual(
            netius.common.ensure_ca(path="test_missing.ca", raise_e=False), None
        )
        self.assertEqual(os.path.exists("test_missing.ca"), False)

    def test__download_ca(self):
        if netius.conf("NO_NETWORK", False, cast=bool):
            self.skipTest("Network access is disabled")

        netius.common.ensure_ca(path="test.ca")
        file = open("test.ca", "rb")
        try:
            data = file.read()
        finally:
            file.close()
            os.unlink("test.ca")

        self.assertNotEqual(data, None)
        self.assertNotEqual(len(data), 0)

    def _patch_result(self, result):
        # replaces the request method of the HTTP client by one that returns
        # a fixed result, so that no network access is required by the test
        self.original = netius.clients.HTTPClient.__dict__["method_s"]

        def method_s(cls, *args, **kwargs):
            return result

        netius.clients.HTTPClient.method_s = classmethod(method_s)

    def _store(self, path, contents):
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
