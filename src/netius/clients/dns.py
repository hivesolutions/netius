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

import struct

import netius

IDENTIFIER = 0x0000
""" The global class identifier value that is going to
be used when assigning new values to the request """

DNS_QUERY = 0x0

DNS_RESPONSE = 0x1

DNS_SQUERY = 0x0

DNS_IQUERY = 0x1

DNS_STATUS = 0x2

DNS_AA = 0x04

DNS_TC = 0x02

DNS_RD = 0x01

DNS_TYPES = dict(
    A = 0x01,
    NS = 0x02,
    MD = 0x03,
    MF = 0x04,
    CNAME = 0x05,
    SOA = 0x06,
    MB = 0x07,
    MG = 0x08,
    MR = 0x09,
    NULL = 0x0a,
    WKS = 0x0b,
    PTR = 0x0c,
    HINFO = 0x0d,
    MINFO = 0x0e,
    MX = 0x0f,
    TXT = 0x10,
)

DNS_CLASSES = dict(
    IN = 0x01
)

DNS_TYPES_R = dict(zip(DNS_TYPES.values(), DNS_TYPES.keys()))
DNS_CLASSES_R = dict(zip(DNS_TYPES.values(), DNS_TYPES.keys()))

class DNSRequest(object):

    def __init__(self, name, type = "a", cls = "in"):
        self.id = self._generate_id()
        self.name = name
        self.type = type
        self.cls = cls

    def request(self):

        format = "!HBBHHHH"

        result = []
        buffer = []

        first_flags = 0x0

        first_flags += DNS_QUERY << 7
        first_flags += DNS_SQUERY << 3
        first_flags |= DNS_RD

        second_flags = 0x0

        result.append(self.id)
        result.append(first_flags)
        result.append(second_flags)
        result.append(0x1)
        result.append(0x0)
        result.append(0x0)
        result.append(0x0)

        data = struct.pack(format, *result)
        buffer.append(data)

        query = self._query(
            self.name,
            type = self.type,
            cls = self.cls
        )
        buffer.append(query)

        data = "".join(buffer)

        return data

    def _query(self, name, type = "a", cls = "in"):
        type_i = DNS_TYPES.get(type.upper(), 0x00)
        clsi = DNS_CLASSES.get(cls.upper(), 0x00)

        format = "!HH"

        data = self._lstring(name)
        data += struct.pack(format, type_i, clsi)

        return data

    def _lstring(self, value):
        buffer = []
        format = "!B"

        parts = value.split(".")
        for part in parts:
            part_l = len(part)
            prefix = struct.pack("!B", part_l)
            part_s = prefix + part
            buffer.append(part_s)

        buffer.append("\0")
        data = "".join(buffer)
        return data

    def _generate_id(self):
        global IDENTIFIER
        IDENTIFIER = (IDENTIFIER + 1) & 0xffff
        return IDENTIFIER

class DNSResponse(object):

    def __init__(self, data):
        self.data = data

    def parse(self):

        format = "!HBBHHHH"

        self.header = self.data[:12]
        result = struct.unpack(format, self.header)

        self.id = result[0]
        self.first_flags = result[1]
        self.second_flags = result[2]
        self.qdcount = result[3]
        self.ancount = result[4]
        self.nscount = result[5]
        self.arcount = result[6]

        self.queries = []
        self.answers = []
        self.name_servers = []
        self.authorities = []

        index = 12

        for _index in range(self.qdcount):
            index, query = self.parse_qd(self.data, index)
            self.queries.append(query)

        for _index in range(self.ancount):
            index, answer = self.parse_an(self.data, index)
            self.answers.append(answer)

        print self.answers

    def parse_qd(self, data, index):
        index, name = self.parse_label(data, index)
        index, type = self.parse_short(data, index)
        index, cls = self.parse_short(data, index)
        type_s = DNS_TYPES_R.get(type, "undefined")
        cls_s = DNS_CLASSES_R.get(cls, "undefined")
        return (index, (name, type_s, cls_s))

    def parse_an(self, data, index):
        index, name = self.parse_label(data, index)
        index, type = self.parse_short(data, index)
        index, cls = self.parse_short(data, index)
        index, ttl = self.parse_long(data, index)
        index, size = self.parse_short(data, index)
        payload = data[index:index + size]
        index += size
        type_s = DNS_TYPES_R.get(type, "undefined")
        cls_s = DNS_CLASSES_R.get(cls, "undefined")
        return (index, (name, type_s, cls_s, ttl, payload))

    def parse_ns(self, data, index):
        pass

    def parse_ar(self, data, index):
        pass

    def parse_label(self, data, index):
        buffer = []

        while True:
            initial = data[index]
            if initial == "\0": index += 1; break

            initial_i = ord(initial)
            is_pointer = initial_i & 0xc0

            if is_pointer:
                index, _data = self.parse_pointer(data, index)
                data = ".".join(buffer) if buffer else ""
                data += _data
                return (index, data)

            _data = data[index + 1:index + initial_i + 1]

            buffer.append(_data)
            index += initial_i + 1

        data = ".".join(buffer)
        return (index, data)

    def parse_pointer(self, data, index):
        slice = data[index:index + 2]

        offset, = struct.unpack("!H", slice)
        offset &= 0x3fff

        _index, label = self.parse_label(data, offset)

        return (index + 2, label)

    def parse_byte(self, data, index):
        _data = data[index:index + 1]
        short, = struct.unpack("!B", _data)
        return (index + 1, short)

    def parse_short(self, data, index):
        _data = data[index:index + 2]
        short, = struct.unpack("!H", _data)
        return (index + 2, short)

    def parse_long(self, data, index):
        _data = data[index:index + 4]
        short, = struct.unpack("!L", _data)
        return (index + 4, short)

class DNSClient(netius.DatagramClient):

    def query(self, name, type = "a", cls = "in", *args, **kwargs):
        request = DNSRequest(name, type = type, cls = cls)
        data = request.request()

        address = ("172.16.0.11", 53)
        self.send(data, address)

    def on_data(self, address, data):
        netius.DatagramClient.on_data(self, address, data)
        response = DNSResponse(data)
        response.parse()

if __name__ == "__main__":
    def handler(): pass

    smtp_client = DNSClient()
    smtp_client.query(
        "gmail.com", type = "mx", callback = handler
    )
