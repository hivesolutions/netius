#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius.common

class TlsTest(unittest.TestCase):

    def test_fingerprint(self):
        key_der = netius.common.open_pem_key(netius.SSL_KEY_PATH)
        result = netius.fingerprint(key_der)
        self.assertEqual(result, "5b4e55fa5ba652a9cb0c3be2dcfa303b5ae647d6")

        cer_der = netius.common.open_pem_key(netius.SSL_CER_PATH, token = "CERTIFICATE")
        result = netius.fingerprint(cer_der)
        self.assertEqual(result, "55ed3769f523281134d87393ffda7f78c9dff786")

    def test_match_hostname(self):
        certificate = dict(
            subject = ((("commonName", "domain.com"),),),
            subjectAltName = (
                ("DNS", "api.domain.com"),
                ("DNS", "embed.domain.com"),
                ("DNS", "instore.domain.com"),
                ("DNS", "domain.com"),
                ("DNS", "www.domain.com")
            ),
            version = 3
        )
        netius.match_hostname(certificate, "domain.com")
        self.assertRaises(
            BaseException,
            lambda: netius.match_hostname(certificate, "other.domain.com")
        )

    def test_dnsname_match(self):
        result = netius.dnsname_match("domain.com", "domain.com")
        self.assertEqual(result, True)

        result = netius.dnsname_match("other.domain.com", "domain.com")
        self.assertEqual(result, False)

        result = netius.dnsname_match("*.com", "domain.com")
        self.assertEqual(result, True)

        result = netius.dnsname_match("*.net", "domain.com")
        self.assertEqual(result, False)
