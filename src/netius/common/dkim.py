#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import re
import time
import base64
import hashlib
import datetime
import cStringIO

import netius

import asn
import rsa
import util

LINE_REGEX = re.compile(r"\r?\n")
""" The regular expression that is going to be used in the
separation of the various lines of the message for the proper
parsing of it, notice the carriage return and new line support """

SPACE_REGEX = re.compile(r"[\t ]")

HEADER_NAME_REGEX = re.compile(r"([\x21-\x7e]+?):")

def rfc822_parse(message, exclude = ()):
    """
    Parse a message in rfc822 format. This format is similar to
    the mime one with only some small changes. The returning value
    for this function a set of dictionary tuples and the body of
    the processed message as a standard encoded string.

    @type message: String
    @param message: The message in rfc822 format, with both Carriage
    return and line feed support.
    @rtype: Tuple
    @return Returns a tuple of headers and body where headers is
    a list of (name and value) pairs.
    """

    # starts both the line index value and the list that will
    # hold the ordered header values for the message
    index = 0
    headers = []

    # strips the message from any possible starting line characters
    # this sometimes happens for message transmission
    message = message.lstrip()

    # splits the various lines of the message around the various
    # pre-defined separator tokens
    lines = LINE_REGEX.split(message)

    # iterates over all the lines to process the complete set of
    # headers currently defined for the message and determine the
    # start (line) index for the message body
    for line in lines:
        # in case an empty/invalid line has been reached the
        # end of headers have been found (must break the loop)
        if not line: break

        # verifies if this is a continuation line, these lines
        # start with either a space or a tab character, for those
        # situations the contents of the current line must be
        # added to the previously parsed header
        if SPACE_REGEX.match(line[0]):
            headers[-1][1] += line + "\r\n"

        # otherwise it's a "normal" header parsing step and the typical
        # header regular expression match strategy is going to be used
        else:
            # tries to run the matching process for message header names
            # against the message line, to be able to "extract" the header
            match = HEADER_NAME_REGEX.match(line)

            # in case there was a valid match for the header tag, processed
            # it by separating the name from the value of the header and
            # creating the proper header tuple adding it to the list of headers
            if match:
                name = match.group(1)
                value = line[match.end(0):] + "\r\n"
                headers.append([name, value])

            # otherwise in case the line is a from line formatted
            # using an old fashion strategy tolerates it (compatibility)
            elif line.startswith("From "): pass

            # as a fallback raises a parser error as no parsing of header
            # was possible for the message (major problem)
            else: raise netius.ParserError("Unexpected header value")

        # increments the current line index counter, as one more
        # line has been processed by the parser
        index += 1

    # joins the complete set of "remaining" body lines creating the string
    # representing the body, and uses it to create the headers and body
    # tuple that is going to be returned to the caller method
    body_lines = lines[index + 1:]
    body = "\r\n".join(body_lines)
    return (headers, body)

def dkim_sign(message, selector, domain, private_key, identity = None, separator = ":"):
    identity = identity or "@" + domain

    headers, body = rfc822_parse(message)

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

    creation = time.time()
    creation = int(creation)
    creation_s = str(creation)

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
        ("h", separator.join(sign_names)),
        ("bh", body_hash),
        ("b", ""),
    ]

    signature = "DKIM-Signature: " + "; ".join("%s=%s" % field for field in sign_fields)
    signature = dkim_fold(signature)

    hash = hashlib.sha256()
    for name, value in sign_headers:
        hash.update(name)
        hash.update(":")
        hash.update(value)

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

    base = "\x00\x01" + "\xff" * delta_l + "\x00" + digest_info
    base_i = util.bytes_to_integer(base)

    signature_i = rsa.rsa_crypt(base_i, exponent, modulus)
    signature_s = util.integer_to_bytes(signature_i, length = modulus_l)

    signature += base64.b64encode(signature_s)
    return signature + "\r\n"

def dkim_headers(headers):
    # returns the headers exactly the way they were parsed
    # as this is the simple strategy approach
    return headers

def dkim_body(body):
    # remove the complete set of empty lines in the body
    # and adds only one line to the end of it as requested
    return re.sub("(\r\n)*$", "\r\n", body)

def dkim_fold(header, length = 72):
    """
    Folds a header line into multiple line feed separated lines
    at column length defined (defaults to 72).

    This is required so that the header field is defined according
    to the dkim rules and the default mime encoding.

    @type header: String
    @param header: The string value of the header that is going to
    be folded into multiple lines.
    @type length: int
    @param length: The maximum length of a column until it gets
    broken into multiple lines (in case it's possible).
    @rtype: String
    @return: The folded string value for the header after the correct
    processing of the string value.
    """

    index = header.rfind("\r\n ")
    if index == -1: pre = ""
    else:
        index += 3
        pre = header[:index]
        header = header[index:]

    while len(header) > length:
        index = header[:length].rfind(" ")
        if index == -1: _index = index
        else: _index = index + 1
        pre += header[:index] + "\r\n "
        header = header[_index:]

    return pre + header

def dkim_generate(domain, suffix = None, number_bits = 1024):
    date_time = datetime.datetime.utcnow()

    identifier = date_time.strftime("%Y%m%d%H%M%S")
    if suffix: identifier += "." + suffix

    identifier_full = "%s._domainkey.%s." % (identifier, domain)

    private_key = rsa.rsa_private(number_bits)
    rsa.assert_private(private_key)
    public_key = rsa.private_to_public(private_key)

    buffer = cStringIO.StringIO()
    try:
        rsa.write_private_key(buffer, private_key)
        private_pem = buffer.getvalue()
    finally:
        buffer.close()

    public_data = rsa.asn_public_key(public_key)
    public_b64 = base64.b64encode(public_data)

    dns_txt = "%s IN TXT \"k=rsa; p=%s\"" % (identifier_full, public_b64)

    return dict(
        identifier = identifier,
        identifier_full = identifier_full,
        private_pem = private_pem,
        dns_txt = dns_txt
    )
