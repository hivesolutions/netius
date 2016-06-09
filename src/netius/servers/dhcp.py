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

import re
import struct

import netius.common

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
            cls._option_broadcast,
            cls._option_requested,
            cls._option_lease,
            cls._option_discover,
            cls._option_offer,
            cls._option_request,
            cls._option_decline,
            cls._option_ack,
            cls._option_nak,
            cls._option_identifier,
            cls._option_renewal,
            cls._option_rebind,
            cls._option_proxy,
            cls._option_end
        )
        cls.options_l = len(cls.options_m)

    def get_info(self):
        buffer = netius.legacy.StringIO()
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
        buffer.write("magic   := %s\n" % self.magic)
        buffer.write("options := %s" % repr(self.options))
        buffer.seek(0)
        info = buffer.read()
        return info

    def print_info(self):
        info = self.get_info()
        print(info)

    def parse(self):
        format = "!BBBBIHHIIII2Q64s128s"

        self.header = self.data[:236]
        self.magic = self.data[236:240]
        self.options = self.data[240:]
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

        self.unpack_options()

    def unpack_options(self):
        self.options_p = {}

        index = 0
        while True:
            byte = self.options[index]
            if netius.legacy.ord(byte) == 0xff: break

            type = byte
            type_i = netius.legacy.ord(type)
            length = netius.legacy.ord(self.options[index + 1])
            payload = self.options[index + 2:index + length + 2]

            self.options_p[type_i] = payload

            index += length + 2

    def get_requested(self):
        payload = self.options_p.get(50, None)
        if not payload: return "0.0.0.0"
        value, = struct.unpack("!I", payload)
        requested = netius.common.addr_to_ip4(value)
        return requested

    def get_type(self):
        payload = self.options_p.get(53, None)
        if not payload: return 0x00
        type = netius.legacy.ord(payload)
        return type

    def get_type_s(self):
        type = self.get_type()
        type_s = netius.common.TYPES_DHCP.get(type, None)
        return type_s

    def get_mac(self):
        addr = self.chaddr[0]
        addr_s = "%012x" % addr
        addr_s = addr_s[:12]
        addr_l = re.findall("..", addr_s)
        mac_addr = ":".join(addr_l)
        return mac_addr

    def response(self, yiaddr, options = {}):
        cls = self.__class__

        host = netius.common.host()

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
        yiaddr = netius.common.ip4_to_addr(yiaddr)
        siaddr = netius.common.ip4_to_addr(host)
        giaddr = self.siaddr
        chaddr = self.chaddr
        sname = b""
        file = b""
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

        for option, values in options.items():
            method = cls.options_m[option - 1]
            if values: option_s = method(**values)
            else: option_s = method()
            buffer.append(option_s)

        buffer.append(end)
        data = b"".join(buffer)

        return data

    @classmethod
    def _str(cls, data):
        data = netius.legacy.bytes(data)
        data_l = len(data)
        size_s = struct.pack("!B", data_l)
        return size_s + data

    @classmethod
    def _pack_m(cls, sequence, format):
        result = []
        for value in sequence:
            value_s = struct.pack(format, value)
            result.append(value_s)

        return b"".join(result)

    @classmethod
    def _option_subnet(cls, subnet = "255.255.255.0"):
        subnet_a = netius.common.ip4_to_addr(subnet)
        subnet_s = struct.pack("!I", subnet_a)
        payload = cls._str(subnet_s)
        return b"\x01" + payload

    @classmethod
    def _option_router(cls, routers = ["192.168.0.1"]):
        routers_a = [netius.common.ip4_to_addr(router) for router in routers]
        routers_s = cls._pack_m(routers_a, "!I")
        payload = cls._str(routers_s)
        return b"\x03" + payload

    @classmethod
    def _option_dns(cls, servers = ["192.168.0.1", "192.168.0.2"]):
        servers_a = [netius.common.ip4_to_addr(server) for server in servers]
        servers_s = cls._pack_m(servers_a, "!I")
        payload = cls._str(servers_s)
        return b"\x06" + payload

    @classmethod
    def _option_name(cls, name = "server.com"):
        payload = cls._str(name)
        return b"\x0f" + payload

    @classmethod
    def _option_broadcast(cls, broadcast = "192.168.0.255"):
        subnet_a = netius.common.ip4_to_addr(broadcast)
        subnet_s = struct.pack("!I", subnet_a)
        payload = cls._str(subnet_s)
        return b"\x1c" + payload

    @classmethod
    def _option_requested(cls, ip = "192.168.0.11"):
        ip_a = netius.common.ip4_to_addr(ip)
        ip_s = struct.pack("!I", ip_a)
        payload = cls._str(ip_s)
        return b"\x32" + payload

    @classmethod
    def _option_lease(cls, time = 3600):
        time_s = struct.pack("!I", time)
        payload = cls._str(time_s)
        return b"\x33" + payload

    @classmethod
    def _option_discover(cls):
        return b"\x35\x01\x01"

    @classmethod
    def _option_offer(cls):
        return b"\x35\x01\x02"

    @classmethod
    def _option_request(cls):
        return b"\x35\x01\x03"

    @classmethod
    def _option_decline(cls):
        return b"\x35\x01\x04"

    @classmethod
    def _option_ack(cls):
        return b"\x35\x01\x05"

    @classmethod
    def _option_nak(cls):
        return b"\x35\x01\x06"

    @classmethod
    def _option_identifier(cls, identifier = "192.168.0.1"):
        subnet_a = netius.common.ip4_to_addr(identifier)
        subnet_s = struct.pack("!I", subnet_a)
        payload = cls._str(subnet_s)
        return b"\x36" + payload

    @classmethod
    def _option_renewal(cls, time = 3600):
        time_s = struct.pack("!I", time)
        payload = cls._str(time_s)
        return b"\x3a" + payload

    @classmethod
    def _option_rebind(cls, time = 3600):
        time_s = struct.pack("!I", time)
        payload = cls._str(time_s)
        return b"\x3b" + payload

    @classmethod
    def _option_proxy(cls, url = "http://localhost/proxy.pac"):
        length = len(url)
        length_o = netius.legacy.chr(length)
        return b"\xfc" + length_o + netius.legacy.bytes(url)

    @classmethod
    def _option_end(cls):
        return b"\xff"

class DHCPServer(netius.DatagramServer):

    def serve(self, port = 67, type = netius.UDP_TYPE, *args, **kwargs):
        netius.DatagramServer.serve(self, port = port, type = type, *args, **kwargs)

    def on_data(self, address, data):
        netius.DatagramServer.on_data(self, address, data)

        request = DHCPRequest(data)
        request.parse()

        self.on_data_dhcp(address, request)

    def on_data_dhcp(self, address, request):
        mac = request.get_mac()
        type = request.get_type()
        type_s = request.get_type_s()

        self.debug("Received %s message from '%s'" % (type_s, mac))

        if not type in (0x01, 0x03): raise netius.NetiusError(
            "Invalid operation type '%d'", type
        )

        type_r = self.get_type(request)
        options = self.get_options(request)
        yiaddr = self.get_yiaddr(request)
        verb = self.get_verb(type_r)
        verb = verb.capitalize()

        options[type_r] = None

        self.debug("%s address '%s' ..." % (verb, yiaddr))

        response = request.response(yiaddr, options = options)
        self.send_dhcp(response)

    def get_verb(self, type_r):
        return netius.common.VERBS_DHCP[type_r - 7]

    def send_dhcp(self, data, *args, **kwargs):
        address = ("255.255.255.255", self.port + 1)
        return self.send(data, address, *args, **kwargs)

    def get_type(self, request):
        raise netius.NetiusError("Not implemented")

    def get_options(self, request):
        raise netius.NetiusError("Not implemented")

    def get_yiaddr(self, request):
        raise netius.NetiusError("Not implemented")

if __name__ == "__main__":
    import logging
    server = DHCPServer(level = logging.INFO)
    server.serve(env = True)
