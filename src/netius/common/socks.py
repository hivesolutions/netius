#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import struct

import netius

from . import util
from . import parser

IPV4 = 0x01

IPV6 = 0x04

DOMAIN = 0x03

VERSION_STATE = 1

HEADER_STATE = 2

USER_ID_STATE = 3

DOMAIN_STATE = 4

AUTH_COUNT_STATE = 5

AUTH_METHODS_STATE = 6

HEADER_EXTRA_STATE = 7

SIZE_STATE = 8

ADDRESS_STATE = 9

PORT_STATE = 10

FINISH_STATE = 11

class SOCKSParser(parser.Parser):

    def __init__(self, owner):
        parser.Parser.__init__(self, owner)

        self.build()
        self.reset()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        self.states = (
            self._parse_version,
            self._parse_header,
            self._parse_user_id,
            self._parse_domain,
            self._parse_auth_count,
            self._parse_auth_methods,
            self._parse_header_extra,
            self._parse_size,
            self._parse_address,
            self._parse_port
        )
        self.state_l = len(self.states)

    def destroy(self):
        """
        Destroys the current structure for the parser meaning that
        it's restored to the original values, this method should only
        be called on situation where no more parser usage is required.
        """

        parser.Parser.destroy(self)

        self.states = ()
        self.state_l = 0

    def reset(self):
        self.state = VERSION_STATE
        self.buffer = []
        self.version = None
        self.command = None
        self.port = None
        self.address = None
        self.address_s = None
        self.user_id = None
        self.domain = None
        self.type = None
        self.size = 0
        self.is_extended = False
        self.auth_count = 0
        self.auth_methods = None

    def clear(self, force = False):
        if not force and self.state == VERSION_STATE: return
        self.reset(self.type, self.store)

    def parse(self, data):
        """
        Parses the provided data chunk, changing the current
        state of the parser accordingly and returning the
        number of processed bytes from it.

        :type data: String
        :param data: The string containing the data to be parsed
        in the current parse operation.
        :rtype: int
        :return: The amount of bytes of the data string that have
        been "parsed" in the current parse operation.
        """

        parser.Parser.parse(self, data)

        # in case the current state of the parser is finished, must
        # reset the state to the start position as the parser is
        # re-starting (probably a new data sequence)
        if self.state == FINISH_STATE: self.clear()

        # retrieves the size of the data that has been sent for parsing
        # and saves it under the size original variable
        size = len(data)
        size_o = size

        # iterates continuously to try to process all that
        # data that has been sent for processing
        while size > 0:

            if self.state <= self.state_l:
                method = self.states[self.state - 1]
                count = method(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == FINISH_STATE:
                break

            else:
                raise netius.ParserError("Invalid state '%d'" % self.state)

        # in case not all of the data has been processed
        # must add it to the buffer so that it may be used
        # latter in the next parsing of the message
        if size > 0: self.buffer.append(data)

        # returns the number of read (processed) bytes of the
        # data that has been sent to the parser
        return size_o - size

    def get_host(self):
        return self.domain or self.address_s

    def get_address(self):
        if self.type == None: return None

        if self.type == IPV4: address = struct.pack("!I", self.address)
        elif self.type == IPV6: address = struct.pack("!QQ", self.address)
        else: address = struct.pack("!B", self.size) + self.address

        return address

    def _parse_version(self, data):
        if len(data) < 1:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:1]
        self.version, = struct.unpack("!B", request)

        if self.version == 4: self.state = HEADER_STATE
        elif self.version == 5: self.state = AUTH_COUNT_STATE
        else: raise netius.ParserError("Invalid version '%d'" % self.version)

        return 1

    def _parse_header(self, data):
        if len(data) < 7:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:7]
        self.command, self.port, self.address = struct.unpack("!BHI", request)
        self.address_s = util.addr_to_ip4(self.address)

        self.is_extended = self.address_s.startswith("0.0.0.")

        self.state = USER_ID_STATE

        return 7

    def _parse_user_id(self, data):
        index = data.find(b"\0")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.user_id = b"".join(self.buffer)
        self.user_id = netius.legacy.str(self.user_id)
        del self.buffer[:]

        if self.is_extended: self.state = DOMAIN_STATE
        else: self.state = FINISH_STATE

        if not self.is_extended: self.trigger("on_data")
        return index + 1

    def _parse_domain(self, data):
        index = data.find(b"\0")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.domain = b"".join(self.buffer)
        self.domain = netius.legacy.str(self.domain)
        del self.buffer[:]

        self.state = FINISH_STATE

        self.trigger("on_data")
        return index + 1

    def _parse_auth_count(self, data):
        if len(data) < 1:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:1]
        self.auth_count, = struct.unpack("!B", request)

        self.state = AUTH_METHODS_STATE

        return 1

    def _parse_auth_methods(self, data):
        is_ready = len(data) + len(self.buffer) >= self.auth_count
        if not is_ready: return 0

        remaining = self.auth_count - len(self.buffer)
        self.buffer.append(data[:remaining])
        data = b"".join(self.buffer)

        format = "!%dB" % self.auth_count
        self.auth_methods = struct.unpack(format, data)
        del self.buffer[:]

        self.state = HEADER_EXTRA_STATE

        self.trigger("on_auth")
        return remaining

    def _parse_header_extra(self, data):
        if len(data) < 4:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:4]
        self.version, self.command, _reserved, self.type =\
            struct.unpack("!BBBB", request)

        if self.type == IPV4: self.size = 4
        elif self.type == IPV6: self.size = 16

        if self.type == DOMAIN: self.state = SIZE_STATE
        else: self.state = ADDRESS_STATE

        return 4

    def _parse_size(self, data):
        if len(data) < 1:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:1]
        self.size, = struct.unpack("!B", request)

        self.state = ADDRESS_STATE

        return 1

    def _parse_address(self, data):
        is_ready = len(data) + len(self.buffer) >= self.size
        if not is_ready: return 0

        remaining = self.size - len(self.buffer)
        self.buffer.append(data[:remaining])
        data = b"".join(self.buffer)

        if self.type == IPV4:
            self.address, = struct.unpack("!I", data)
            self.address_s = util.addr_to_ip4(self.address)
        elif self.type == IPV6:
            self.address = struct.unpack("!QQ", data)
            self.address_s = self.address
        else:
            self.address = netius.legacy.str(data)
            self.address_s = netius.legacy.str(data)

        self.state = PORT_STATE

        return remaining

    def _parse_port(self, data):
        if len(data) < 2:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:2]
        self.port, = struct.unpack("!H", request)

        self.state = FINISH_STATE

        self.trigger("on_data")
        return 2
