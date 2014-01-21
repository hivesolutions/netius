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



        print self.ancount

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
