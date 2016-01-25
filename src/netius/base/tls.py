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
import ssl

from . import errors

def match_hostname(certificate, hostname):
    if hasattr(ssl, "match_hostname"):
        return ssl.match_hostname(certificate, hostname)

    dns_names = []
    subject_alt_name = certificate.get("subjectAltName", ())

    for key, value in subject_alt_name:
        if not key == "DNS": continue
        if _dnsname_match(value, hostname): return
        dns_names.append(value)

    if not dns_names:
        for subject in certificate.get("subject", ()):
            for key, value in subject:
                if not key == "commonName": continue
                if _dnsname_match(value, hostname): return
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

def _dnsname_match(dn, hostname, max_wildcards = 1):
    pats = []
    if not dn: return False

    parts = dn.split(r".")
    base = parts[0]
    remainder = parts[1:]

    wildcards = base.count("*")
    if wildcards > max_wildcards: raise errors.SecurityError(
        "Too many wildcards in certificate DNS name: " + str(dn)
    )

    if not wildcards:
        return dn.lower() == hostname.lower()

    if base == "*":
        pats.append("[^.]+")
    elif base.startswith("xn--") or hostname.startswith("xn--"):
        pats.append(re.escape(base))
    else:
        pats.append(re.escape(base).replace(r"\*", "[^.]*"))

    for fragment in remainder:
        pats.append(re.escape(fragment))

    pat = re.compile(r"\A" + r"\.".join(pats) + r"\Z", re.IGNORECASE)
    return pat.match(hostname)
