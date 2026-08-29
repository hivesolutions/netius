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

import netius.common


class TLSTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.certificate = netius.common.open_pem_key(
            netius.SSL_CER_PATH, token="CERTIFICATE"
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_fingerprint(self):
        key_der = netius.common.open_pem_key(netius.SSL_KEY_PATH)
        result = netius.fingerprint(key_der)
        self.assertEqual(result, "5b4e55fa5ba652a9cb0c3be2dcfa303b5ae647d6")

        cer_der = netius.common.open_pem_key(netius.SSL_CER_PATH, token="CERTIFICATE")
        result = netius.fingerprint(cer_der)
        self.assertEqual(result, "55ed3769f523281134d87393ffda7f78c9dff786")

    def test_fingerprint_hash(self):
        key_der = netius.common.open_pem_key(netius.SSL_KEY_PATH)

        # the hash that is asked for is the one that builds the digest, so
        # that a stronger one may be used in the place of the default
        result = netius.fingerprint(key_der, hash="sha256")
        self.assertEqual(
            result, "700e8c6ee8794c06bb6b6cd04d2ae8ae0c3469e0d20e7d0df8537f5ef1b078bf"
        )

    def test_match_fingerprint(self):
        result = netius.match_fingerprint(
            self.certificate, "55ed3769f523281134d87393ffda7f78c9dff786"
        )

        # a fingerprint that is the expected one ends the verification
        # without any value being given back for it
        self.assertEqual(result, None)

        result = netius.match_fingerprint(
            self.certificate,
            "1104ee6370db0201d8c60712daf7fe7b154ca7c1c85a26d40b19b7cd2cfa7e2a",
            hash="sha256",
        )

        self.assertEqual(result, None)

        self.assertRaises(
            netius.SecurityError,
            lambda: netius.match_fingerprint(self.certificate, "invalid"),
        )

    def test_match_fingerprint_devel(self):
        with netius.conf_override("LEVEL", "INFO"):
            message = self._match_message(self.certificate, "invalid")

        # outside of a development environment the two fingerprints are
        # kept out of the message, so that nothing about them leaks
        self.assertEqual("invalid" in message, False)

        with netius.conf_override("LEVEL", "DEBUG"):
            message = self._match_message(self.certificate, "invalid")

        # under a development one both of them are named, so that the
        # mismatch may be understood from the message alone
        self.assertEqual("invalid" in message, True)
        self.assertEqual("55ed3769f523281134d87393ffda7f78c9dff786" in message, True)

    def test_match_hostname(self):
        certificate = dict(
            subject=((("commonName", "domain.com"),),),
            subjectAltName=(
                ("DNS", "api.domain.com"),
                ("DNS", "embed.domain.com"),
                ("DNS", "instore.domain.com"),
                ("DNS", "domain.com"),
                ("DNS", "www.domain.com"),
            ),
            version=3,
        )
        netius.match_hostname(certificate, "domain.com")
        self.assertRaises(
            BaseException,
            lambda: netius.match_hostname(certificate, "other.domain.com"),
        )

    def test_match_hostname_common_name(self):
        certificate = dict(
            subject=((("organizationName", "Hive"), ("commonName", "domain.com")),),
            version=3,
        )

        # with no alternative name in the certificate the common name of
        # the subject is the one that answers for the host, the entries
        # of it that are not a common name being skipped
        self.assertEqual(netius.match_hostname(certificate, "domain.com"), None)
        self.assertRaises(
            BaseException, lambda: netius.match_hostname(certificate, "other.com")
        )

    def test_match_hostname_entry(self):
        certificate = dict(
            subjectAltName=(("IP Address", "127.0.0.1"), ("DNS", "domain.com")),
            version=3,
        )

        # an alternative name that is not a DNS one is skipped, the match
        # being decided by the DNS entry that follows it
        self.assertEqual(netius.match_hostname(certificate, "domain.com"), None)

    def test_match_hostname_missing(self):
        # a certificate that carries no name at all is never able to answer
        # for a host, whatever the host that is asked for
        self.assertRaises(
            BaseException, lambda: netius.match_hostname(dict(version=3), "domain.com")
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

    def test_dnsname_match_empty(self):
        # a domain that carries no value is unable to match anything, the
        # refusal happening before the value is split
        self.assertEqual(netius.dnsname_match("", "domain.com"), False)
        self.assertEqual(netius.dnsname_match(None, "domain.com"), False)

    def test_dnsname_match_wildcards(self):
        # a single wildcard is the most that the first label of a name may
        # carry, one that carries more is refused instead of being matched
        self.assertRaises(
            netius.SecurityError,
            lambda: netius.dnsname_match("*a*.domain.com", "was.domain.com"),
        )

        # the limit is the one that the caller asks for, so a name of two
        # of them is matched once the limit allows for it
        result = netius.dnsname_match(
            "*a*.domain.com", "was.domain.com", max_wildcards=2
        )
        self.assertEqual(result, True)

    def test_dnsname_match_partial(self):
        # the wildcard may be only a part of the label, in which case the
        # remainder of it still has to be matched literally
        self.assertEqual(netius.dnsname_match("w*.domain.com", "www.domain.com"), True)
        self.assertEqual(netius.dnsname_match("w*.domain.com", "api.domain.com"), False)

        # the wildcard never crosses a label, so a name of a deeper level
        # is not matched by a single one of them
        self.assertEqual(
            netius.dnsname_match("*.domain.com", "www.api.domain.com"), False
        )

    def test_dnsname_match_idna(self):
        # an internationalized label is compared literally, as the wildcard
        # of one of them is not meant to be expanded
        self.assertEqual(
            netius.dnsname_match("xn--*.domain.com", "xn--*.domain.com"), True
        )
        self.assertEqual(
            netius.dnsname_match("xn--*.domain.com", "xn--bcher.domain.com"), False
        )

    def test_dump_certificate(self):
        certificate = dict(subjectAltName=(("DNS", "domain.com"),), version=3)

        with netius.conf_override("SSL_PATH", self.base):
            netius.dump_certificate(certificate, b"binary")

        # the first of the alternative names is the one that names the file
        # that carries the binary version of the certificate
        self.assertEqual(self._read("domain.com.der"), b"binary")

    def test_dump_certificate_name(self):
        path = os.path.join(self.base, "certificates")

        with netius.conf_override("SSL_PATH", path):
            netius.dump_certificate(dict(version=3), b"binary", name="custom")

            # the directory that holds the certificates is created when it
            # is not there, so that the dump is never refused for it
            self.assertEqual(os.path.exists(path), True)

            netius.dump_certificate(dict(version=3), b"binary")

        # the name that is given takes precedence over the one of the
        # certificate, which falls back to a generic one of its own
        self.assertEqual(
            self._read(os.path.join("certificates", "custom.der")), b"binary"
        )
        self.assertEqual(
            self._read(os.path.join("certificates", "certificate.der")), b"binary"
        )

    def test_dump_certificate_invalid(self):
        with netius.conf_override("SSL_PATH", self.base):
            self.assertEqual(netius.dump_certificate(None, b"binary"), None)
            self.assertEqual(netius.dump_certificate(dict(version=3), None), None)

        # neither of the two dumps is able to name a file, so nothing is
        # written and the directory is left empty
        self.assertEqual(os.listdir(self.base), [])

    def _match_message(self, *args, **kwargs):
        # runs the match of a fingerprint giving back the message of the
        # error that it raises, so that the contents of it may be asserted
        try:
            netius.match_fingerprint(*args, **kwargs)
        except netius.SecurityError as exception:
            return str(exception)
        return None

    def _read(self, name):
        file = open(os.path.join(self.base, name), "rb")
        try:
            return file.read()
        finally:
            file.close()
