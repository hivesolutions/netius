#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius.extra

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

RESULT = b"DKIM-Signature: v=1; a=rsa-sha256; c=simple/simple; d=netius.hive.pt;\r\n\
 i=email@netius.hive.pt; l=13; q=dns/txt; s=20160523113052;\r\n\
 t=1464003802; h=Header;\r\n\
 bh=sIAi0xXPHrEtJmW97Q5q9AZTwKC+l1Iy+0m8vQIc/DY=; b=Pr7dVjQIX3ovG78v1X45seFwA/+uyIAofJbxn5iXTRBA5Mv+YVdiI9QMm/gU1ljoSGqqC+hvLS4iB2N1kC4fGuDxXOyNaApOLSA2hl/mBpzca6SNyu6CYvUDdhmfD+8TsYMe6Vy8UY9lWpPYNgfb9BhORqPvxiC8A8F9ScTVT/s=\r\nHeader: Value\r\n\r\nHello World"

REGISTRY = {
    "netius.hive.pt" : dict(
        key_b64 = PRIVATE_KEY,
        selector = "20160523113052",
        domain = "netius.hive.pt"
    )
}

class RelaySMTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.extra.RelaySMTPServer()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_dkim(self):
        self.server.dkim = REGISTRY
        result = self.server.dkim_contents(
            MESSAGE,
            email = "email@netius.hive.pt",
            creation = 1464003802
        )

        self.assertEqual(result, RESULT)
