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
import pprint
import tempfile
import unittest

import netius
import netius.common
import netius.sh.rsa

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

NUMBER_BITS = 1024


class SHRSATest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base_path = tempfile.mkdtemp()
        self.private_key = netius.common.open_private_key_b64(PRIVATE_KEY)
        self.public_key = netius.common.private_to_public(self.private_key)
        self.private_path = os.path.join(self.base_path, "private.key")
        self.public_path = os.path.join(self.base_path, "public.key")
        netius.common.write_private_key(self.private_path, self.private_key)
        netius.common.write_public_key(self.public_path, self.public_key)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base_path)

    def test_read_private(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._read(netius.sh.rsa.read_private, self.private_path)

        # the key read from the PEM file is the very same one that has been
        # loaded from its base64 counterpart, printed as a plain structure
        self.assertEqual(result, pprint.pformat(self.private_key) + "\n")

    def test_read_public(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        result = self._read(netius.sh.rsa.read_public, self.public_path)

        # the public key gains the number of bits of the modulus, as that
        # value is only inferred while the key is being read from the file
        self.assertEqual("'modulus': %d" % self.public_key["modulus"] in result, True)
        self.assertEqual(
            "'public_exponent': %d" % self.public_key["public_exponent"] in result, True
        )
        self.assertEqual("'bits': %d" % NUMBER_BITS in result, True)

    def test_private_to_public(self):
        target_path = os.path.join(self.base_path, "target.pub")

        netius.sh.rsa.private_to_public(self.private_path, target_path)

        public_key = netius.common.open_public_key(target_path)

        # the public part is derived from the private key and written to the
        # target path, sharing both the modulus and the public exponent
        self.assertEqual(public_key["modulus"], self.private_key["modulus"])
        self.assertEqual(
            public_key["public_exponent"], self.private_key["public_exponent"]
        )
        self.assertEqual(public_key["bits"], NUMBER_BITS)

    def _read(self, method, path):
        with mock.patch("sys.stdout", netius.legacy.StringIO()) as stdout:
            method(path)
        return stdout.getvalue()
