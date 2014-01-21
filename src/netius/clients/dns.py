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

class DNSRequest(object):

    def __init__(self, name, type = "a", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.id = self.generate_id()
        self.name = name
        self.type = type

    def request(self):

        format = "!HBBHHHH"

        result = []
        buffer = []

        first_header = 0x0

        first_header += DNS_QUERY
        first_header += DNS_SQUERY << 1

        second_header = 0x0

        result.append(self.id)
        result.append(first_header)
        result.append(second_header)
        result.append(0x0)
        result.append(0x0)
        result.append(0x0)
        result.append(0x0)

        data = struct.pack(format, *result)
        buffer.append(data)

        data = "".join(buffer)

        return data

    def generate_id(self):
        global IDENTIFIER
        IDENTIFIER = (IDENTIFIER + 1) & 0xffff
        return IDENTIFIER

class DNSClient(netius.DatagramClient):

    def query(self, name, type = "a", *args, **kwargs):
        request = DNSRequest(name, type = type)
        data = request.request()




#    def on_data(self, connection, data):
#        netius.Client.on_data(self, connection, data)
#        connection.parse(data)

if __name__ == "__main__":
    def handler(): pass

    smtp_client = DNSClient()
    smtp_client.query(
        "gmail.com", type = "mx", callback = handler
    )
