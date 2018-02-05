#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius.common

class SSDPClient(netius.DatagramClient):
    """
    Client implementation of the SSDP protocol meant to be
    used under the UPnP standard for discovery and control of
    internet activated devices.

    Using this implementation it should be possible to discover
    and control devices like routes, media centers, etc.

    :see: http://en.wikipedia.org/wiki/Simple_Service_Discovery_Protocol
    """

    def on_data(self, connection, data):
        netius.DatagramClient.on_data(self, connection, data)
        self.parser = netius.common.HTTPParser(self, type = netius.common.RESPONSE)
        self.parser.bind("on_headers", self.on_headers_parser)
        self.parser.parse(data)
        self.parser.destroy()

    def on_headers_parser(self):
        headers = self.parser.get_headers()
        self.trigger("headers", self, self.parser, headers)

    def discover(self, target, *args, **kwargs):
        return self.method(
            "M-SEARCH",
            target,
            "ssdp:discover",
            *args,
            **kwargs
        )

    def method(
        self,
        method,
        target,
        namespace,
        mx = 3,
        path = "*",
        params = None,
        headers = None,
        data = None,
        host = "239.255.255.250",
        port = 1900,
        version = "HTTP/1.1",
        connection = None,
        asynchronous = True,
        callback = None
    ):
        address = (host, port)

        headers = headers or dict()
        headers["ST"] = target
        headers["Man"] = "\"" + namespace + "\""
        headers["MX"] = str(mx)
        headers["Host"] = "%s:%d" % address

        buffer = []
        buffer.append("%s %s %s\r\n" % (method, path, version))
        for key, value in netius.legacy.iteritems(headers):
            key = netius.common.header_up(key)
            if not isinstance(value, list): value = (value,)
            for _value in value: buffer.append("%s: %s\r\n" % (key, _value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        self.send(buffer_data, address)
        data and self.send(data, address)

if __name__ == "__main__":
    def on_headers(client, parser, headers):
        print(headers)
        client.close()

    client = SSDPClient()
    client.discover("urn:schemas-upnp-org:device:InternetGatewayDevice:1")
    client.bind("headers", on_headers)
else:
    __path__ = []
