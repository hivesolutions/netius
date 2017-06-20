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

import netius

from . import util

INTEGER = 0x02
BIT_STRING = 0x03
OCTET_STRING = 0x04
NULL = 0x05
OBJECT_IDENTIFIER = 0x06
SEQUENCE = 0x30

ASN1_OBJECT = [
    (SEQUENCE, [
        (SEQUENCE, [
            OBJECT_IDENTIFIER,
            NULL
        ]),
        BIT_STRING
    ])
]

ASN1_RSA_PUBLIC_KEY = [
    (SEQUENCE, [
        INTEGER,
        INTEGER
    ])
]

ASN1_RSA_PRIVATE_KEY = [
    (SEQUENCE, [
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER,
        INTEGER
    ])
]

RSAID_PKCS1 = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"
HASHID_SHA1 = b"\x2b\x0e\x03\x02\x1a"
HASHID_SHA256 = b"\x60\x86\x48\x01\x65\x03\x04\x02\x01"

def asn1_parse(template, data):
    """
    Parse a data structure according to asn.1 template,
    the provided template should respect the predefined
    structure. The provided data is going to be validated
    against the template format and a exception raised in
    case the data is not conformant.

    :type template: List/Tuple
    :param template: A list of tuples comprising the asn.1 template.
    :type: List
    :param data: A list of bytes to parse.
    """

    # starts the index value at the zero value and the creates the
    # the list that is going to hold the various partial values for
    # generated during the parsing of the structure
    index = 0
    result = []

    # iterates over the complete set of items in the current
    # template structure to "apply" them to the current values
    # so that they are correctly parsed/verified
    for item in template:
        # verifies if the data type for the current template
        # item to be parser is tuple and based on that defined
        # the current expected data type and children values
        is_tuple = type(item) == tuple
        if is_tuple: dtype, children = item
        else: dtype = item; children = None

        # retrieves the value (as an ordinal) for the current
        # byte and increments the index for the parser
        tag = netius.legacy.ord(data[index])
        index += 1

        # in case the current type is not of the expect type,
        # must raise an exception indicating the problem to
        # the top level layers (should be properly handled)
        if not tag == dtype:
            raise netius.ParserError("Unexpected tag (got 0x%02x, expecting 0x%02x)" % (tag, dtype))

        # retrieves the ordinal value of the current byte as
        # the length of the value to be parsed and then increments
        # the pointer of the buffer reading process
        length = netius.legacy.ord(data[index])
        index += 1

        # in case the last bit of the length byte is set the,
        # the byte designates the length of the byte sequence that
        # defines the length of the current value to be read instead
        if length & 0x80:
            number = length & 0x7f
            length = util.bytes_to_integer(data[index:index + number])
            index += number

        if tag == BIT_STRING:
            result.append(data[index:index + length])
            index += length

        elif tag == OCTET_STRING:
            result.append(data[index:index + length])
            index += length

        elif tag == INTEGER:
            number = util.bytes_to_integer(data[index:index + length])
            index += length
            result.append(number)

        elif tag == NULL:
            util.verify(length == 0)
            result.append(None)

        elif tag == OBJECT_IDENTIFIER:
            result.append(data[index:index + length])
            index += length

        elif tag == SEQUENCE:
            part = asn1_parse(children, data[index:index + length])
            result.append(part)
            index += length

        else:
            raise netius.ParserError("Unexpected tag in template 0x%02x" % tag)

    return result

def asn1_length(length):
    """
    Returns a string representing a field length in asn.1 format.
    This value is computed taking into account the multiple byte
    representation of very large values.

    :type length: int
    :param length:The integer based length value that is going to
    be used in the conversion to a string representation.
    :rtype: String
    :return: The string based representation of the provided length
    integer value according to the asn.1 specification.
    """

    util.verify(length >= 0)
    if length < 0x7f: return netius.legacy.chr(length)

    result = util.integer_to_bytes(length)
    number = len(result)
    result = netius.legacy.chr(number | 0x80) + result
    return result

def asn1_gen(node):
    generator = asn1_build(node)
    return b"".join(generator)

def asn1_build(node):
    """
    Builds an asn.1 data structure based on pairs of (type, data),
    this function may be used as a generator of a buffer.

    :type node: Tuple
    :param node: The root node of the structure that is going to be
    used as reference for the generation of the asn.1 buffer.
    """

    tag, value = node

    if tag == BIT_STRING:
        yield netius.legacy.chr(BIT_STRING) + asn1_length(len(value)) + value

    elif tag == OCTET_STRING:
        yield netius.legacy.chr(OCTET_STRING) + asn1_length(len(value)) + value

    elif tag == INTEGER:
        value = util.integer_to_bytes(value)
        yield netius.legacy.chr(INTEGER) + asn1_length(len(value)) + value

    elif tag == NULL:
        util.verify(value == None)
        yield netius.legacy.chr(NULL) + asn1_length(0)

    elif tag == OBJECT_IDENTIFIER:
        yield netius.legacy.chr(OBJECT_IDENTIFIER) + asn1_length(len(value)) + value

    elif tag == SEQUENCE:
        buffer = []
        for item in value:
            generator = asn1_build(item)
            data = b"".join(generator)
            buffer.append(data)
        result = b"".join(buffer)
        yield netius.legacy.chr(SEQUENCE) + asn1_length(len(result)) + result

    else:
        raise netius.GeneratorError("Unexpected tag in template 0x%02x" % tag)
