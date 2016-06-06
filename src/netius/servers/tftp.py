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

import struct

import netius.common

class TFTPRequest(object):

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
            cls._option_rrq,
            cls._option_wrq,
            cls._option_data,
            cls._option_ack,
            cls._option_error
        )
        cls.options_l = len(cls.options_m)

    def get_info(self):
        buffer = netius.legacy.StringIO()
        buffer.write("op      := %d\n" % self.op)
        buffer.write("payload := %s" % repr(self.payload))
        buffer.seek(0)
        info = buffer.read()
        return info

    def print_info(self):
        info = self.get_info()
        print(info)

    def parse(self):
        cls = self.__class__

        format = "!H"

        self.header = self.data[:2]
        self.payload = self.data[2:]
        result = struct.unpack(format, self.header)
        self.op = result[0]

    def get_type(self):
        return self.op

    def get_type_s(self):
        type = self.get_type()
        type_s = netius.common.TYPES_TFTP.get(type, None)
        return type_s

    def response(self, options = {}):
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
    def _option_rrq(cls):
        #@todo: find the zero termination of the name
        # 
        subnet_a = netius.common.ip4_to_addr(subnet)
        subnet_s = struct.pack("!I", subnet_a)
        payload = cls._str(subnet_s)
        return b"\x01" + payload

    @classmethod
    def _option_wrq(cls):
        raise netius.NotImplemented("Option not implemented")

    @classmethod
    def _option_data(cls):
        raise netius.NotImplemented("Option not implemented")

    @classmethod
    def _option_ack(cls):
        pass

    @classmethod
    def _option_error(cls):
        raise netius.NotImplemented("Option not implemented")

class TFTPServer(netius.DatagramServer):
    """
    Abstract trivial ftp server implementation that handles simple
    file system based file serving.

    @see: http://tools.ietf.org/html/rfc1350
    """

    def __init__(self, base_path = "", *args, **kwargs):
        netius.DatagramServer.__init__(self, *args, **kwargs)
        self.base_path = base_path

    def serve(self, port = 69, *args, **kwargs):
        netius.DatagramServer.serve(self, port = port, *args, **kwargs)

    def on_data(self, address, data):
        netius.DatagramServer.on_data(self, address, data)

        request = TFTPRequest(data)
        request.parse()
        request.print_info()

        self.on_data_tftp(address, request)

    def on_data_tftp(self, address, request):
        type = request.get_type()
        type_s = request.get_type_s()

        self.info("Received %s message from '%s'" % (type_s, address))

        if not type in (0x01, 0x04): raise netius.NetiusError(
            "Invalid operation type '%d'", type
        )

        type_r = self.get_type(request)
        options = self.get_options(request)
        yiaddr = self.get_yiaddr(request)
        verb = self.get_verb(type_r)
        verb = verb.capitalize()

        options[type_r] = None

        self.info("%s address '%s' ..." % (verb, yiaddr))

        response = request.response(yiaddr, options = options)
        self.send(response, address)

    def on_serve(self):
        netius.DatagramServer.on_serve(self)
        if self.env: self.base_path = self.get_env("BASE_PATH", self.base_path)
        self.info("Starting TFTP server ...")
        self.info("Defining '%s' as the root of the file server ..." % (self.base_path or "."))

if __name__ == "__main__":
    import logging
    server = TFTPServer(level = logging.DEBUG)
    server.serve(env = True)
