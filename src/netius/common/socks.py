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

import netius.common

REQUEST_STATE = 1

USER_ID_STATE = 2

DOMAIN_STATE = 3

FINISH_STATE = 4

class SOCKSParser(netius.Observable):

    def __init__(self, owner):
        netius.Observable.__init__(self)

        self.owner = owner
        self.reset()

    def reset(self):
        self.state = REQUEST_STATE
        self.buffer = []
        self.version = None
        self.command = None
        self.port = None
        self.address = None
        self.address_s = None
        self.user_id = None
        self.domain = None
        self.is_extended = False

    def clear(self, force = False):
        if not force and self.state == REQUEST_STATE: return
        self.reset(self.type, self.store)

    def parse(self, data):
        """
        Parses the provided data chunk, changing the current
        state of the parser accordingly and returning the
        number of processed bytes from it.

        @type data: String
        @param data: The string containing the data to be parsed
        in the current parse operation.
        @rtype: int
        @return: The amount of bytes of the data string that have
        been "parsed" in the current parse operation.
        """

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

            if self.state == REQUEST_STATE:
                count = self._parse_request(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == USER_ID_STATE:
                count = self._parse_user_id(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == DOMAIN_STATE:
                count = self._parse_domain(data)
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

    def _parse_request(self, data):
        print repr(data)
        if len(data) < 8:
            raise netius.ParserError("Invalid request (too short)")

        request = data[:8]
        self.version, self.command, self.port, self.address =\
            struct.unpack("!BBHI", request)
        self.address_s = netius.common.number_to_ip4(self.address)

        self.is_extended = self.address_s.startswith("0.0.0.")

        self.state = USER_ID_STATE

        return 8

    def _parse_user_id(self, data):
        index = data.find("\0")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.user_id = "".join(self.buffer)
        del self.buffer[:]

        if self.is_extended: self.state = DOMAIN_STATE
        else: self.state = FINISH_STATE

        if not self.is_extended: self.trigger("on_data")
        return index + 1

    def _parse_domain(self, data):
        index = data.find("\0")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.domain = "".join(self.buffer)
        del self.buffer[:]

        self.state = FINISH_STATE

        self.trigger("on_data")
        return index + 1
