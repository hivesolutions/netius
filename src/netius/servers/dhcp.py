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
import cStringIO

import netius.common

SUBNET_OPTION = 1
ROUTER_OPTION = 2
DNS_OPTION = 3
NAME_OPTION = 4
REQUESTED_OPTION = 5
LEASE_OPTION = 6
OFFER_OPTION = 6
END_OPTION = 6

class DHCPRequest(object):

    options_m = None
    options_l = None

    def __init__(self, data):
        self.data = data

        cls = self.__class__
        cls.generate()

    @classmethod
    def generate(cls):
        if cls.options_m: return
        cls.options_m = (
            cls._option_subnet,
            cls._option_router,
            cls._option_dns,
            cls._option_name,
            cls._option_requested,
            cls._option_lease,
            cls._option_offer,
            cls._option_end
        )
        cls.options_l = len(cls.options_m)

    def get_info(self):
        buffer = cStringIO.StringIO()
        buffer.write("op      := %d\n" % self.op)
        buffer.write("htype   := %d\n" % self.htype)
        buffer.write("hlen    := %d\n" % self.hlen)
        buffer.write("hops    := %d\n" % self.hops)
        buffer.write("xid     := 0x%x\n" % self.xid)
        buffer.write("secs    := %d\n" % self.secs)
        buffer.write("flags   := 0x%x\n" % self.flags)
        buffer.write("ciaddr  := %s\n" % self.ciaddr_s)
        buffer.write("yiaddr  := %s\n" % self.yiaddr_s)
        buffer.write("siaddr  := %s\n" % self.siaddr_s)
        buffer.write("giaddr  := %s\n" % self.giaddr_s)
        buffer.write("chaddr  := %x\n" % self.chaddr[0])
        buffer.write("chaddr  := %x\n" % self.chaddr[1])
        buffer.write("sname   := %s\n" % self.sname)
        buffer.write("file    := %s\n" % self.file)
        buffer.write("options := %s" % repr(self.options))
        buffer.seek(0)
        return buffer

    def print_info(self):
        info = self.get_info()
        info_s = info.read()
        print info_s
        print "------------ // ------------"

    def parse(self):
        format = "!BBBBIHHIIII2Q64s128s"

        self.header = self.data[:236]
        self.options = self.data[236:]
        result = struct.unpack(format, self.header)
        self.op = result[0]
        self.htype = result[1]
        self.hlen = result[2]
        self.hops = result[3]
        self.xid = result[4]
        self.secs = result[5]
        self.flags = result[6]
        self.ciaddr = result[7]
        self.yiaddr = result[8]
        self.siaddr = result[9]
        self.giaddr = result[10]
        self.chaddr = result[11:13]
        self.sname = result[13]
        self.file = result[14]

        self.ciaddr_s = netius.common.addr_to_ip4(self.ciaddr)
        self.yiaddr_s = netius.common.addr_to_ip4(self.yiaddr)
        self.siaddr_s = netius.common.addr_to_ip4(self.siaddr)
        self.giaddr_s = netius.common.addr_to_ip4(self.giaddr)

    def response(self, options = {}):
        cls = self.__class__

        format = "!BBBBIHHIIII2Q64s128sI"
        result = []
        buffer = []

        op = 0x02
        htype = 0x01
        hlen = 0x06
        hops = 0x00
        xid = self.xid
        secs = 0x0000
        flags = self.flags
        ciaddr = self.ciaddr
        yiaddr = netius.common.ip4_to_addr("172.16.0.99")
        siaddr = netius.common.ip4_to_addr("172.16.0.25") # tenho de o conseguir sacar de algum lado (o meu ip)
        giaddr = self.siaddr
        chaddr = self.chaddr
        sname = ""
        file = ""
        magic = 0x63825363

        end = self._option_end()

        result.append(op)
        result.append(htype)
        result.append(hlen)
        result.append(hops)
        result.append(xid)
        result.append(secs)
        result.append(flags)
        result.append(ciaddr)
        result.append(yiaddr)
        result.append(siaddr)
        result.append(giaddr)
        result.append(chaddr[0])
        result.append(chaddr[1])
        result.append(sname)
        result.append(file)
        result.append(magic)

        data = struct.pack(format, *result)
        buffer.append(data)

        for option, values in options.iteritems():
            method = cls.options_m[option - 1]
            if values: option_s = method(**values)
            else: option_s = method()
            buffer.append(option_s)

        buffer.append(end)
        data = "".join(buffer)

        return data

    @classmethod
    def _str(cls, data):
        data_l = len(data)
        size_s = struct.pack("!B", data_l)
        return size_s + data

    @classmethod
    def _pack_m(cls, sequence, format):
        result = []
        for value in sequence:
            value_s = struct.pack(format, value)
            result.append(value_s)

        return "".join(result)

    @classmethod
    def _option_subnet(cls, subnet = "255.255.255.0"):
        subnet_a = netius.common.ip4_to_addr(subnet)
        subnet_s = struct.pack("!I", subnet_a)
        payload = cls._str(subnet_s)
        return "\x01" + payload

    @classmethod
    def _option_router(cls, routers = ["192.168.0.1"]):
        routers_a = [netius.common.ip4_to_addr(router) for router in routers]
        routers_s = cls._pack_m(routers_a, "!I")
        payload = cls._str(routers_s)
        return "\x03" + payload

    @classmethod
    def _option_dns(cls, servers = ["192.168.0.1", "192.168.0.2"]):
        servers_a = [netius.common.ip4_to_addr(server) for server in servers]
        servers_s = cls._pack_m(servers_a, "!I")
        payload = cls._str(servers_s)
        return "\x06" + payload

    @classmethod
    def _option_name(cls, name = "server.com"):
        payload = cls._str(name)
        return "\x0f" + payload

    @classmethod
    def _option_requested(cls, ip = "192.168.0.11"):
        ip_a = netius.common.ip4_to_addr(ip)
        ip_s = struct.pack("!I", ip_a)
        payload = cls._str(ip_s)
        return "\x32" + payload

    @classmethod
    def _option_lease(cls, time = 3600):
        time_s = struct.pack("!I", time)
        payload = cls._str(time_s)
        return "\x33" + payload

    @classmethod
    def _option_offer(cls):
        return "\x35\x01\x02"

    @classmethod
    def _option_end(cls):
        return "\xff"

class DHCPServer(netius.DatagramServer):

    def __init__(self, rules = {}, name = None, handler = None, *args, **kwargs):
        netius.DatagramServer.__init__(
            self,
            name = name,
            handler = handler,
            *args,
            **kwargs
        )
        self.rules = rules

    def serve(self, port = 67, type = netius.UDP_TYPE, *args, **kwargs):
        netius.DatagramServer.serve(self, port = port, type = type, *args, **kwargs)

    def on_data(self, address, data):
        netius.DatagramServer.on_data(self, address, data)

        request = DHCPRequest(data)
        request.parse()
        request.print_info()

        options = {
            DNS_OPTION : None,
            NAME_OPTION : dict(name = "tobias.com")
        }

        response = request.response(options)
        self.socket.sendto(response, address)  #### @TODO ISTO AINDA NAO ESTA A LIDAR COM OS PROBLEMAS NAS FALHAS DOS WRITES !!!!

    def on_connection_d(self, connection):
        netius.DatagramServer.on_connection_d(self, connection)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.close()

if __name__ == "__main__":
    import logging
    server = DHCPServer(level = logging.INFO)
    server.serve(env = True)
