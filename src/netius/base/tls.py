#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import re
import os
import ssl
import hashlib

from . import config
from . import errors

def fingerprint(certificate, hash = "sha1"):
    digest = hashlib.new(hash, certificate)
    return digest.hexdigest()

def match_fingerprint(certificate, exp_fingerprint, hash = "sha1"):
    cert_fingerprint = fingerprint(certificate, hash = hash)
    if cert_fingerprint == exp_fingerprint: return
    if config._is_devel():
        extra = ", expected '%s' got '%s'" %\
            (exp_fingerprint, cert_fingerprint)
    else:
        extra = ""
    raise errors.SecurityError(
        "Missmatch in certificate fingerprint" + extra
    )

def match_hostname(certificate, hostname):
    if hasattr(ssl, "match_hostname"):
        return ssl.match_hostname(certificate, hostname)

    dns_names = []
    subject_alt_name = certificate.get("subjectAltName", ())

    for key, value in subject_alt_name:
        if not key == "DNS": continue
        if dnsname_match(value, hostname): return
        dns_names.append(value)

    if not dns_names:
        for subject in certificate.get("subject", ()):
            for key, value in subject:
                if not key == "commonName": continue
                if dnsname_match(value, hostname): return
                dns_names.append(value)

    if len(dns_names) > 1:
        raise errors.SecurityError(
            "Hostname %s doesn't match either of %s" %\
            (hostname, ", ".join(map(str, dns_names)))
        )
    elif len(dns_names) == 1:
        raise errors.SecurityError(
            "Hostname %s doesn't match %s" %\
            (hostname, dns_names[0])
        )
    else:
        raise errors.SecurityError(
            "No appropriate commonName or subjectAltName fields were found"
        )

def dnsname_match(domain, hostname, max_wildcards = 1):
    # creates the initial list of pats that are going to be used in
    # the final match operation for wildcard matching
    pats = []

    # in case no valid domain is passed an invalid result is returned
    # immediately indicating that no match was possible
    if not domain: return False

    # splits the provided domain value around its components, taking
    # into account the typical dot separator
    parts = domain.split(".")
    base = parts[0]
    remainder = parts[1:]

    # determines the number of wildcard characters present in the
    # base value for discovery in case this value overflow the maximum
    # number of wildcards allowed raises an error
    wildcards = base.count("*")
    if wildcards > max_wildcards: raise errors.SecurityError(
        "Too many wildcards in certificate DNS name: " + str(domain)
    )

    # in case there are no wildcards in the domain name runs the
    # "normal" hostname validation process against the domain name
    if wildcards == 0:
        return domain.lower() == hostname.lower()

    if base == "*":
        pats.append("[^.]+")
    elif base.startswith("xn--") or hostname.startswith("xn--"):
        pats.append(re.escape(base))
    else:
        pats.append(re.escape(base).replace(r"\*", "[^.]*"))

    for fragment in remainder:
        pats.append(re.escape(fragment))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return True if pat.match(hostname) else False

def dump_certificate(certificate, certificate_binary, name = None):
    # runs some pre-validation operations so that the dump parameters
    # that are required are considered valid
    if not certificate: return
    if not certificate_binary: return

    # tries to retrieve the main subject name from the subject
    # alternative names, there may be no value and if that's the
    # case a default value is used instead
    subject_alt_name = certificate.get("subjectAltName", ())
    if subject_alt_name: subject_name = subject_alt_name[0][1]
    else: subject_name = "certificate"

    # "calculates" the final name for the certificate, taking
    # into account the provided parameter and subject name, the
    # constructs the file name value with the der suffix
    name = name or subject_name
    file_name = name + ".der"

    # retrieves ths proper ssl path (where data is going to be
    # stored) and creates such directory (if required)
    ssl_path = config.conf("SSL_PATH", "/tmp/ssl")
    file_path = os.path.join(ssl_path, file_name)
    if not os.path.exists(ssl_path): os.makedirs(ssl_path)

    # opens the file for writing and then dumps the certificate
    # binary information into the file, closing it afterwards
    file = open(file_path, "wb")
    try: file.write(certificate_binary)
    finally: file.close()
