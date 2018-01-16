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

import copy

import netius.common
import netius.servers

class DHCPServerS(netius.servers.DHCPServer):

    def __init__(self, pool = None, options = {}, *args, **kwargs):
        netius.servers.DHCPServer.__init__(self, *args, **kwargs)

        self.pool = pool or netius.common.AddressPool("192.168.0.61", "192.168.0.69")
        self.options = {}
        self.lease = 3600

        self._build(options)

    def get_type(self, request):
        type = request.get_type()
        requested = request.get_requested()
        mac = request.get_mac()

        if type == 0x01: result = netius.common.OFFER_DHCP
        elif type == 0x03:
            current = self.pool.assigned(mac) or requested
            is_owner = self.pool.is_owner(mac, current)
            if is_owner: result = netius.common.ACK_DHCP
            else: result = netius.common.NAK_DHCP

        return result

    def get_options(self, request):
        options = copy.copy(self.options)
        return options

    def get_yiaddr(self, request):
        type = request.get_type()
        if type == 0x01: yiaddr = self._reserve(request)
        elif type == 0x03: yiaddr = self._confirm(request)
        return yiaddr

    def _build(self, options):
        lease = options.get("lease", {})
        self.lease = lease.get("time", 3600)

        for key, value in netius.legacy.iteritems(options):
            key_i = netius.common.OPTIONS_DHCP.get(key, None)
            if not key_i: continue
            self.options[key_i] = value

    def _reserve(self, request):
        mac = request.get_mac()
        return self.pool.reserve(
            owner = mac,
            lease = self.lease
        )

    def _confirm(self, request):
        requested = request.get_requested()
        mac = request.get_mac()
        current = self.pool.assigned(mac) or requested
        is_valid = self.pool.is_valid(current)
        if is_valid: self.pool.touch(current, self.lease)
        return current

if __name__ == "__main__":
    import logging
    host = netius.common.host()
    pool = netius.common.AddressPool("172.16.0.80", "172.16.0.89")
    options = dict(
        router = dict(routers = ["172.16.0.6"]),
        subnet = dict(subnet = "255.255.0.0"),
        dns = dict(
            servers = ["172.16.0.11", "172.16.0.12"]
        ),
        identifier = dict(identifier = host),
        broadcast = dict(broadcast = "172.16.255.255"),
        name = dict(name = "hive"),
        lease = dict(time = 3600),
        renewal = dict(time = 1800),
        rebind = dict(time = 2700),
        proxy = dict(url = "http://172.16.0.25:8080/proxy.pac")
    )
    server = DHCPServerS(
        pool = pool,
        options = options,
        level = logging.INFO
    )
    server.serve(env = True)
else:
    __path__ = []
