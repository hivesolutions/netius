#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import re
import time
import base64
import hashlib
import datetime

import netius

from . import asn
from . import rsa
from . import util
from . import mime

def dkim_sign(
    message,
    selector,
    domain,
    private_key,
    identity = None,
    separator = ":",
    creation = None
):
    separator = netius.legacy.bytes(separator)
    identity = identity or "@" + domain

    headers, body = mime.rfc822_parse(message, strip = False)

    if not identity.endswith(domain):
        raise netius.GeneratorError("Identity must end with domain")

    headers = dkim_headers(headers)
    body = dkim_body(body)

    include_headers = [name.lower() for name, _value in headers]
    sign_headers = [header for header in headers if header[0].lower() in include_headers]
    sign_names = [name for name, _value in sign_headers]

    hash = hashlib.sha256()
    hash.update(body)

    body_digest = hash.digest()
    body_hash = base64.b64encode(body_digest)
    body_hash = netius.legacy.str(body_hash)

    creation = creation or time.time()
    creation = int(creation)
    creation_s = str(creation)

    names = separator.join(sign_names)
    names = netius.legacy.str(names)

    sign_fields = [
        ("v", "1"),
        ("a", "rsa-sha256"),
        ("c", "simple/simple"),
        ("d", domain),
        ("i", identity),
        ("l", len(body)),
        ("q", "dns/txt"),
        ("s", selector),
        ("t", creation_s),
        ("h", names),
        ("bh", body_hash),
        ("b", ""),
    ]

    signature = "DKIM-Signature: " + "; ".join("%s=%s" % field for field in sign_fields)
    if isinstance(signature, netius.legacy.UNICODE):
        signature = signature.encode("utf-8")
    signature = dkim_fold(signature)

    hash = hashlib.sha256()
    for name, value in sign_headers:
        hash.update(name)
        hash.update(b":")
        hash.update(value + b"\r\n")

    hash.update(signature)
    digest = hash.digest()

    digest_info = asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.SEQUENCE, [
                (asn.OBJECT_IDENTIFIER, asn.HASHID_SHA256),
                (asn.NULL, None),
            ]),
            (asn.OCTET_STRING, digest),
        ])
    )

    modulus = private_key["modulus"]
    exponent = private_key["private_exponent"]
    modulus_s = util.integer_to_bytes(modulus)
    modulus_l = len(modulus_s)

    digest_l = len(digest_info)
    delta_l = modulus_l - digest_l - 3
    delta_l = 0 if delta_l < 0 else delta_l

    if digest_l + 3 > modulus_l:
        raise netius.GeneratorError("Hash too large for modulus")

    base = b"\x00\x01" + b"\xff" * delta_l + b"\x00" + digest_info
    base_i = util.bytes_to_integer(base)

    signature_i = rsa.rsa_crypt(base_i, exponent, modulus)
    signature_s = util.integer_to_bytes(signature_i, length = modulus_l)

    signature += base64.b64encode(signature_s) + b"\r\n"
    return signature

def dkim_headers(headers):
    # returns the headers exactly the way they were parsed
    # as this is the simple strategy approach
    return headers

def dkim_body(body):
    # remove the complete set of empty lines in the body
    # and adds only one line to the end of it as requested
    return re.sub(b"(\r\n)*$", b"\r\n", body)

def dkim_fold(header, length = 72):
    """
    Folds a header line into multiple line feed separated lines
    at column length defined (defaults to 72).

    This is required so that the header field is defined according
    to the dkim rules and the default mime encoding.

    :type header: String
    :param header: The string value of the header that is going to
    be folded into multiple lines.
    :type length: int
    :param length: The maximum length of a column until it gets
    broken into multiple lines (in case it's possible).
    :rtype: String
    :return: The folded string value for the header after the correct
    processing of the string value.
    """

    index = header.rfind(b"\r\n ")
    if index == -1: pre = b""
    else:
        index += 3
        pre = header[:index]
        header = header[index:]

    while len(header) > length:
        index = header[:length].rfind(b" ")
        if index == -1: _index = index
        else: _index = index + 1
        pre += header[:index] + b"\r\n "
        header = header[_index:]

    return pre + header

def dkim_generate(domain, suffix = None, number_bits = 1024):
    date_time = datetime.datetime.utcnow()

    selector = date_time.strftime("%Y%m%d%H%M%S")
    if suffix: selector += "." + suffix

    selector_full = "%s._domainkey.%s." % (selector, domain)

    private_key = rsa.rsa_private(number_bits)
    rsa.assert_private(private_key, number_bits = number_bits)
    public_key = rsa.private_to_public(private_key)

    buffer = netius.legacy.BytesIO()
    try:
        rsa.write_private_key(buffer, private_key)
        private_pem = buffer.getvalue()
        private_pem = netius.legacy.str(private_pem)
    finally:
        buffer.close()

    public_data = rsa.asn_public_key(public_key)
    public_b64 = base64.b64encode(public_data)
    public_b64 = netius.legacy.str(public_b64)

    dns_txt = "%s IN TXT \"k=rsa; p=%s\"" % (selector_full, public_b64)

    return dict(
        selector = selector,
        selector_full = selector_full,
        private_pem = private_pem,
        dns_txt = dns_txt
    )
