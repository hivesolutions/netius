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

import struct
import random

import netius

def encode_ws(data, final = True, opcode = 0x01, mask = True):
    # converts the boolean based values of the frame into the
    # bit based partials that are going to be used in the build
    # of the final frame container element (as expected)
    final = 0x01 if final else 0x00
    mask = 0x01 if mask else 0x00

    data = netius.legacy.bytes(data)
    data_l = len(data)

    first_byte = (final << 7) + opcode

    encoded_l = list()
    encoded_l.append(netius.legacy.chr(first_byte))

    if data_l <= 125:
        encoded_l.append(netius.legacy.chr(data_l + (mask << 7)))

    elif data_l >= 126 and data_l <= 65535:
        encoded_l.append(netius.legacy.chr(126 + (mask << 7)))
        encoded_l.append(netius.legacy.chr((data_l >> 8) & 255))
        encoded_l.append(netius.legacy.chr(data_l & 255))

    else:
        encoded_l.append(netius.legacy.chr(127 + (mask << 7)))
        encoded_l.append(netius.legacy.chr((data_l >> 56) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 48) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 40) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 32) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 24) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 16) & 255))
        encoded_l.append(netius.legacy.chr((data_l >> 8) & 255))
        encoded_l.append(netius.legacy.chr(data_l & 255))

    if mask:
        mask_bytes = struct.pack("!I", random.getrandbits(32))
        encoded_l.append(mask_bytes)
        encoded_a = bytearray(data_l)
        for i in range(data_l):
            encoded_a[i] = netius.legacy.chri(netius.legacy.ord(data[i]) ^ netius.legacy.ord(mask_bytes[i % 4]))
        data = bytes(encoded_a)

    encoded_l.append(data)
    encoded = b"".join(encoded_l)
    return encoded

def decode_ws(data):
    # calculates the length of the data and runs the initial
    # verification ensuring that such data is larger than the
    # minimum value for a valid websockets frame
    data_l = len(data)
    assert_ws(data_l, 2)

    # retrieves the reference to the second byte in the frame
    # this is the byte that is going to be used in the initial
    # calculus of the length for the current data frame
    second_byte = data[1]

    # verifies if the current frame is a masked one and calculates
    # the number of mask bytes taking that into account
    has_mask = netius.legacy.ord(second_byte) & 128
    mask_bytes = 4 if has_mask else 0

    # retrieves the base length (simplified length) of the
    # frame as the seven last bits of the second byte in frame
    length = netius.legacy.ord(second_byte) & 127
    index_mask_f = 2

    # verifies if the length to be calculated is of type
    # extended (length equals to 126) if that's the case
    # two extra bytes must be taken into account on length
    if length == 126:
        assert_ws(data_l, 4)
        length = 0
        length += netius.legacy.ord(data[2]) << 8
        length += netius.legacy.ord(data[3])
        index_mask_f = 4

    # check if the length to be calculated is of type extended
    # payload length and if that's the case many more bytes
    # (eight) must be taken into account for length calculus
    elif length == 127:
        assert_ws(data_l, 10)
        length = 0
        length += netius.legacy.ord(data[2]) << 56
        length += netius.legacy.ord(data[3]) << 48
        length += netius.legacy.ord(data[4]) << 40
        length += netius.legacy.ord(data[5]) << 32
        length += netius.legacy.ord(data[6]) << 24
        length += netius.legacy.ord(data[7]) << 16
        length += netius.legacy.ord(data[8]) << 8
        length += netius.legacy.ord(data[9])
        index_mask_f = 10

    # calculates the size of the raw data part of the message and
    # in case its smaller than the defined length of the data returns
    # immediately indicating that there's not enough data to complete
    # the decoding of the data (should be re-trying again latter)
    raw_size = data_l - index_mask_f - mask_bytes
    if raw_size < length: raise netius.DataError("Not enough data")

    # in case the frame data is not masked the complete set of contents
    # may be returned immediately to the caller as there's no issue with
    # avoiding the unmasking operation (as the data is not masked)
    if not has_mask: return data[index_mask_f:], b""

    # retrieves the mask part of the data that are going to be
    # used in the decoding part of the process
    mask = data[index_mask_f:index_mask_f + mask_bytes]

    # allocates the array that is going to be used
    # for the decoding of the data with the length
    # that was computed as the data length
    decoded_a = bytearray(length)

    # starts the initial data index and then iterates over the
    # range of decoded length applying the mask to the data
    # (decoding it consequently) to the created decoded array
    i = index_mask_f + 4
    for j in range(length):
        decoded_a[j] = netius.legacy.chri(netius.legacy.ord(data[i]) ^ netius.legacy.ord(mask[j % 4]))
        i += 1

    # converts the decoded array of data into a string and
    # and returns the "partial" string containing the data that
    # remained pending to be parsed
    decoded = bytes(decoded_a)
    return decoded, data[i:]

def assert_ws(data_l, size):
    if data_l < size: raise netius.DataError("Not enough data")
