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

import xml.dom.minidom

import netius.clients

def upnp_map(ext_port, int_port, host, protocol = "TCP", description = "netius"):
    """
    Defines a router port forwarding rule using an UPnP based
    request that tries to find the first available router.

    In case there's no available router with UPnP features the
    client may become idle, leaking memory.

    :see: http://www.upnp.org/specs/gw/UPnP-gw-WANIPConnection-v1-Service.pdf
    """

    message = """<?xml version="1.0"?>
        <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"
            s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
            <s:Body>
                <u:AddPortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">
                    <NewRemoteHost></NewRemoteHost>
                    <NewExternalPort>%d</NewExternalPort>
                    <NewProtocol>%s</NewProtocol>
                    <NewInternalPort>%d</NewInternalPort>
                    <NewInternalClient>%s</NewInternalClient>
                    <NewEnabled>1</NewEnabled>
                    <NewPortMappingDescription>%s</NewPortMappingDescription>
                    <NewLeaseDuration>0</NewLeaseDuration>
                </u:AddPortMapping>
            </s:Body>
    </s:Envelope>""" % (ext_port, protocol, int_port, host, description)

    def on_location(connection, parser, request):
        data = request["data"]
        document = xml.dom.minidom.parseString(data)
        nodes = document.getElementsByTagName("controlURL")
        path = nodes[0].childNodes[0].data
        base_url = "http://%s:%d" % connection.address
        url = base_url + path
        netius.clients.HTTPClient.post_s(
            url,
            headers = dict(
                SOAPACTION = "\"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping\""
            ),
            data = message,
            async = False
        )
        client = connection.owner
        client.close()

    def on_headers(client, parser, headers):
        location = headers.get("Location", None)
        if not location: raise netius.DataError("No location found")
        http_client = netius.clients.HTTPClient()
        http_client.get(location, on_result = on_location)
        client.close()

    client = netius.clients.SSDPClient()
    client.bind("headers", on_headers)
    client.discover("urn:schemas-upnp-org:device:InternetGatewayDevice:1")
