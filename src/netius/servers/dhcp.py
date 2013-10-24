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

class DHCPRequest(object):

    def __init__(self, data):
        self.data = data

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
        buffer.write("sname   := %s\n" % self.sname)
        for addr in self.chaddr_s:
            buffer.write("chaddr  := %s\n" % addr)
        buffer.write("file    := %s\n" % self.file)
        buffer.write("options := %s" % self.options)
        buffer.seek(0)
        return buffer

    def print_info(self):
        info = self.get_info()
        info_s = info.read()
        print info_s
        print "------------ // ------------"

    def parse(self):
        format = "!BBBBIHHIIII4I64s128s"

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
        self.chaddr = result[11:15]
        self.sname = result[15]
        self.file = result[16]

        self.sname = netius.common.cstring(self.sname)
        self.file = netius.common.cstring(self.file)

        self.ciaddr_s = netius.common.addr_to_ip4(self.ciaddr)
        self.yiaddr_s = netius.common.addr_to_ip4(self.yiaddr)
        self.siaddr_s = netius.common.addr_to_ip4(self.siaddr)
        self.giaddr_s = netius.common.addr_to_ip4(self.giaddr)
        self.chaddr_s = [netius.common.addr_to_ip4(addr) for addr in self.chaddr]

    def response(self):
        pass

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

        #self.socket.sendto(, address)

    def on_connection_d(self, connection):
        netius.DatagramServer.on_connection_d(self, connection)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.close()

if __name__ == "__main__":
    import logging
    server = DHCPServer(level = logging.INFO)
    server.serve(host = "0.0.0.0", port = 67)
