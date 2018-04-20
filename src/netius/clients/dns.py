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

import os
import struct

import netius.common

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
    AAAA = 0x1c
)

DNS_CLASSES = dict(
    IN = 0x01
)

DNS_TYPES_R = dict(zip(DNS_TYPES.values(), DNS_TYPES.keys()))
DNS_CLASSES_R = dict(zip(DNS_CLASSES.values(), DNS_CLASSES.keys()))

class DNSRequest(netius.Request):

    def __init__(self, name, type = "a", cls = "in", callback = None):
        netius.Request.__init__(self, callback = callback)
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

        data = b"".join(buffer)

        return data

    def _query(self, name, type = "a", cls = "in"):
        type_i = DNS_TYPES.get(type.upper(), 0x00)
        clsi = DNS_CLASSES.get(cls.upper(), 0x00)

        format = "!HH"

        data = self._label(name)
        data += struct.pack(format, type_i, clsi)

        return data

    def _label(self, value):
        buffer = []
        format = "!B"

        parts = value.split(".")
        for part in parts:
            part = netius.legacy.bytes(part)
            part_l = len(part)
            prefix = struct.pack("!B", part_l)
            part_s = prefix + part
            buffer.append(part_s)

        buffer.append(b"\0")
        data = b"".join(buffer)
        return data

class DNSResponse(netius.Response):

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

    def get_id(self):
        return self.id

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
        index, _size = self.parse_short(data, index)
        type_s = DNS_TYPES_R.get(type, "undefined")
        cls_s = DNS_CLASSES_R.get(cls, "undefined")
        index, payload = self.parse_payload(data, index, type_s)
        return (index, (name, type_s, cls_s, ttl, payload))

    def parse_payload(self, data, index, type_s):
        type_s = type_s.lower()
        method_name = "parse_" + type_s
        method = getattr(self, method_name)
        return method(data, index)

    def parse_a(self, data, index):
        index, address = self.parse_ip4(data, index)
        return (index, address)

    def parse_aaaa(self, data, index):
        index, address = self.parse_ip6(data, index)
        return (index, address)

    def parse_mx(self, data, index):
        index, preference = self.parse_short(data, index)
        index, address = self.parse_label(data, index)
        return (index, (preference, address))

    def parse_cname(self, data, index):
        index, address = self.parse_label(data, index)
        return (index, address)

    def parse_ns(self, data, index):
        pass

    def parse_ar(self, data, index):
        pass

    def parse_label(self, data, index):
        buffer = []

        while True:
            initial = data[index]
            initial_i = netius.legacy.ord(initial)

            if initial_i == 0: index += 1; break
            is_pointer = initial_i & 0xc0

            if is_pointer:
                index, _data = self.parse_pointer(data, index)
                buffer.append(_data)
                data = b".".join(buffer)
                return (index, data)

            _data = data[index + 1:index + initial_i + 1]

            buffer.append(_data)
            index += initial_i + 1

        data = b".".join(buffer)
        return (index, data)

    def parse_pointer(self, data, index):
        slice = data[index:index + 2]

        offset, = struct.unpack("!H", slice)
        offset &= 0x3fff

        _index, label = self.parse_label(data, offset)

        return (index + 2, label)

    def parse_ip4(self, data, index):
        index, long = self.parse_long(data, index)
        address = netius.common.addr_to_ip4(long)
        return (index, address)

    def parse_ip6(self, data, index):
        index, long_long_first = self.parse_long_long(data, index)
        index, long_long_second = self.parse_long_long(data, index)
        address_i = (long_long_first << 64) + long_long_second
        address = netius.common.addr_to_ip6(address_i)
        return (index, address)

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
        long, = struct.unpack("!L", _data)
        return (index + 4, long)

    def parse_long_long(self, data, index):
        _data = data[index:index + 8]
        long_long, = struct.unpack("!Q", _data)
        return (index + 8, long_long)

class DNSProtocol(netius.DatagramProtocol):

    ns_file_l = None

    @classmethod
    def ns_system(cls, type = "ip4"):
        ns = cls.ns_file(type = type)
        if ns: return ns[0]
        ns = cls.ns_google(type = type)
        if ns: return ns[0]
        ns = cls.ns_cloudfare(type = type)
        if ns: return ns[0]
        return None

    @classmethod
    def ns_file(cls, type = "ip4", force = False):
        # verifies if the list value for the file based name server
        # retrieval value is defined and if that's the case and the
        # force flag is not set returns it immediately
        if not cls.ns_file_l == None and not force: return cls.ns_file_l

        # verifies if the resolve file exists and if it does not returns
        # immediately indicating the impossibility to resolve the value
        if not os.path.exists("/etc/resolv.conf"): return None

        # retrieves the reference to the function that is going to validate
        # if the provided name server complies with the proper (address) type
        validator = getattr(netius.common, "is_" + type)

        # opens the resolve file and reads the complete set of contents
        # from it, closing the file afterwards
        file = open("/etc/resolv.conf", "rb")
        try: data = file.read()
        finally: file.close()

        # starts the list that is going to store the various name server
        # values, this is going to be populated with the file contents
        cls.ns_file_l = []

        # splits the contents of the file around their lines and tries
        # to find the name servers defined in it to be added to the list
        for line in data.split(b"\n"):
            line = line.strip()
            if not line.startswith(b"nameserver"): continue
            _header, ns = line.split(b" ", 1)
            ns = ns.strip()
            ns = netius.legacy.str(ns)
            is_valid = validator(ns)
            if not is_valid: continue
            cls.ns_file_l.append(ns)

        # returns the final value of the list of name servers loaded from
        # the file (as expected by the call)
        return cls.ns_file_l

    @classmethod
    def ns_google(cls, type = "ip4"):
        if type == "ip4": return ["8.8.8.8", "8.8.4.4"]
        if type == "ip6": return [
            "2001:4860:4860::8888",
            "2001:4860:4860::8844"
        ]
        return []

    @classmethod
    def ns_cloudfare(cls, type = "ip4"):
        if type == "ip4": return ["1.1.1.1", "1.0.0.1"]
        if type == "ip6": return [
            "2606:4700:4700::1111",
            "2606:4700:4700::1001"
        ]
        return []

    def query(self, name, type = "a", cls = "in", ns = None, callback = None):
        # retrieves the reference to the class associated with the
        # current instance to be used to access class operations
        _cls = self.__class__

        # verifies if a target name server was specified for the query
        # in case it was not uses the default (globally provided) value
        # that may be used for generic queries assuming internet access
        ns = ns or _cls.ns_system()

        # creates a new DNS request object describing the query that was
        # just sent and then generates the request stream code that is
        # going to be used for sending the request through network
        request = DNSRequest(
            name,
            type = type,
            cls = cls,
            callback = callback
        )
        data = request.request()

        # prints some debug information about the DNS query that is going
        # to be performed (provides some development capabilities)
        self.debug("Running DNS query %s '%s in '%s'" % (type, name, ns))

        # adds the current request pending callback handing to the internal
        # management structures so that it becomes callable latter
        self.add_request(request)

        # creates the final address assuming default port in the
        # name server and then send the contents of the DNS request
        address = (ns, 53)
        self.send(data, address)

    def on_data(self, address, data):
        netius.DatagramProtocol.on_data(self, address, data)

        # create the DNS response with the provided data stream and
        # runs the parse operation in it so that the response becomes
        # populated with the proper contents, this operation is risky as
        # it may fail in case the message is malformed
        response = DNSResponse(data)
        response.parse()

        # calls the DNS specific data handler with the proper response
        # object populated with the response from the DNS server
        self.on_data_dns(address, response)

    def on_data_dns(self, address, response):
        # tries to retrieve the request associated with the current
        # response and in case none is found returns immediately as
        # there's nothing remaining to be done
        request = self.get_request(response)
        if not request: return

        # removes the request being handled from the current request
        # structures so that a callback is no longer answered
        self.remove_request(request)

        # in case no callback is not defined for the request returns
        # immediately as there's nothing else remaining to be done,
        # otherwise calls the proper callback with the response
        if not request.callback: return
        request.callback(response)

class DNSClient(netius.ClientAgent):

    protocol = DNSProtocol

    @classmethod
    def query_s(
        cls,
        name,
        type = "a",
        cls_ = "in",
        ns = None,
        callback = None,
        loop = None
    ):
        ns = ns or cls.protocol.ns_system()
        address = (ns, 53)
        protocol = cls.protocol()

        def on_connect(result):
            _transport, protocol = result
            protocol.query(
                name,
                type = type,
                cls = cls_,
                ns = ns,
                callback = callback
            )

        loop = netius.build_datagram(
            lambda: protocol,
            callback = on_connect,
            loop = loop,
            remote_addr = address
        )

        return loop, protocol

if __name__ == "__main__":
    def handler(response):
        # closes the current protocol to correctly close
        # all of the underlying structures
        protocol.close()

        # retrieves the currently associated loop using
        # netius base infra-structure and then runs the
        # stop operation on the next tick end
        netius.compat_loop(loop).stop()

        # in case the provided response is not valid
        # a timeout message is printed to indicate the
        # problem with the resolution
        if not response: print("Timeout in resolution"); return

        # unpacks the complete set of contents from
        # the various answers so that only the address
        # of the answer is available, then prints them
        for answer in response.answers:
            if type in ("a", "aaaa"):
                address = answer[4]
                print("%s" % address)
            if type in ("mx",):
                extra = answer[4]
                priority = extra[0]
                address = extra[1]
                print("%s => %d" % (address, priority))

    # retrieves the values of the configuration variables
    # that are going to be used to perform the DNS query
    name = netius.conf("DNS_NAME", "gmail.com")
    type = netius.conf("DNS_TYPE", "mx")
    ns = netius.conf("DNS_NS", None)

    # runs the static version of a DNS query, note that
    # the daemon flag is unset so that the global client
    # runs in foreground avoiding the exit of the process
    loop, protocol = DNSClient.query_s(
        name,
        type = type,
        ns = ns,
        callback = handler
    )
    loop.run_forever()
    loop.close()
else:
    __path__ = []
