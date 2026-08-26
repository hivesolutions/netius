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
import netius.sh.dkim

try:
    import unittest.mock as mock
except ImportError:
    mock = None

PRIVATE_KEY = b"MIICVwIAAoGAgRWSX07LB0VzpDy14taaO1b+juQVhQpyKy/fxaLupohy4UDOxHJU\
Iz7jzR6B8l93KXWqxG5UZK2CduL6TKJGQZ+jGkTk0YU3d3r5kwPNOX1o+qhICJF8\
tcWZcw1MUV816sxJ3hi6RTz7faRvJtj9J2SM2cY3eq0xQSM/dvD1fqUCAwEAAQKB\
gDaUp3qTN3fQnxAf94x9z2Mt6p8CxDKn8xRdvtGzjhNueJzUKVmZOghZLDtsHegd\
A6bNMTKzsA2N7C9W1B0ZNHkmc6cbUyM/gXPLzpErFF4c5sTYAaJGKK+3/3BrrliG\
6vgzTXt3KZRlInfrumZRo4h7yE/IokfmzBwjbyP7N3lhAkDpfTwLidRBTgYVz5yO\
/7j55vl2GN80xDk0IDfO17/O8qyQlt+J6pksE0ojTkAjD2N4rx3dL4kPgmx80r/D\
AdNNAkCNh4LBukRUMT+ulfngrnzQ4QDnCUXpANKpe3HZk4Yfysj1+zrlWFilzO3y\
t/RpGu4GtH1LUNQNjrp94CcBNPy5AkBW6KCTAuiYrjwhnjd+Gr11d33fcX6Tm35X\
Yq6jNTdWBooo/5+RLFt7RmrQHW5OHoo9/6C0Fd+EgF11UNTD90f5AkBBB6/0FgNJ\
cCujq7PaIjKlw40nm2ItEry5NUh1wcxSFVpLdDl2oiZxYH1BFndOSBpwqEQd9DDL\
Xfag2fryGge5AkCFPjggILI8jZZoEW9gJoyqh13fkf+WjtwL1mLztK2gQcrvlyUd\
/ddIy8ZEkmGRiHMcX0SGdsEprW/EpbhSdakC"

MESSAGE = b"Header: Value\r\n\r\nHello World"

RESULT = dict(
    selector="20160523113052",
    selector_full="20160523113052._domainkey.netius.hive.pt.",
    private_pem="-----BEGIN RSA PRIVATE KEY-----\n",
    dns_txt='20160523113052._domainkey.netius.hive.pt. IN TXT "k=rsa; p=key"',
)


class SHDKIMTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.key_path = os.path.join(self.base_path, "private.key")
        private_key = netius.common.open_private_key_b64(PRIVATE_KEY)
        netius.common.write_private_key(self.key_path, private_key)
        self.email_path = os.path.join(self.base_path, "message.eml")

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base_path)

    def test_generate(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(
            netius.common, "dkim_generate", return_value=RESULT
        ) as dkim_generate:
            result = self._generate("netius.hive.pt")

        self.assertEqual(dkim_generate.call_count, 1)
        self.assertEqual(dkim_generate.call_args[0], ("netius.hive.pt",))
        self.assertEqual(dkim_generate.call_args[1]["suffix"], None)
        self.assertEqual(dkim_generate.call_args[1]["number_bits"], 1024)

        # only the DNS record and the private key are printed, the selector
        # is already part of the record and so it's not printed on its own
        self.assertEqual(
            result, "%s\n%s\n" % (RESULT["dns_txt"], RESULT["private_pem"])
        )

    def test_generate_arguments(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(
            netius.common, "dkim_generate", return_value=RESULT
        ) as dkim_generate:
            self._generate("netius.hive.pt", "mail", "512")

        # the number of bits arrives from the shell as a string and has to
        # be cast so that the key generation is able to make use of it
        self.assertEqual(dkim_generate.call_args[1]["suffix"], "mail")
        self.assertEqual(dkim_generate.call_args[1]["number_bits"], 512)

    def test_generate_key(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._generate("netius.hive.pt", None, "512")

        self.assertEqual("._domainkey.netius.hive.pt. IN TXT " in result, True)
        self.assertEqual('"k=rsa; p=' in result, True)
        self.assertEqual("-----BEGIN RSA PRIVATE KEY-----" in result, True)
        self.assertEqual("-----END RSA PRIVATE KEY-----" in result, True)

    def test_sign(self):
        self._write(self.email_path, MESSAGE)

        netius.sh.dkim.sign(
            self.email_path, self.key_path, "20160523113052", "netius.hive.pt"
        )

        contents = self._read(self.email_path)

        # the signature is prepended to the message, meaning that the file is
        # rewritten in place with the very same contents it had before
        self.assertEqual(contents.startswith(b"DKIM-Signature: v=1;"), True)
        self.assertEqual(contents.endswith(MESSAGE), True)
        self.assertEqual(b"s=20160523113052;" in contents, True)
        self.assertEqual(b"d=netius.hive.pt;" in contents, True)

    def test_sign_strip(self):
        self._write(self.email_path, b"\r\n  " + MESSAGE)

        netius.sh.dkim.sign(
            self.email_path, self.key_path, "20160523113052", "netius.hive.pt"
        )

        contents = self._read(self.email_path)

        # the leading whitespace is removed before the signing takes place,
        # otherwise the headers would not be recognised as such, the body
        # hash is the one of the message with no whitespace prefix
        self.assertEqual(contents.endswith(MESSAGE), True)
        self.assertEqual(b"\r\n  " + MESSAGE in contents, False)
        self.assertEqual(
            b"bh=sIAi0xXPHrEtJmW97Q5q9AZTwKC+l1Iy+0m8vQIc/DY=;" in contents, True
        )

    def _generate(self, *args, **kwargs):
        with mock.patch("sys.stdout", netius.legacy.StringIO()) as stdout:
            netius.sh.dkim.generate(*args, **kwargs)
        return stdout.getvalue()

    def _read(self, path):
        file = open(path, "rb")
        try:
            return file.read()
        finally:
            file.close()

    def _write(self, path, contents):
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
