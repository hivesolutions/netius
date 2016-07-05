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

import netius

from . import parser

HEADER_SIZE = 9

SETTING_SIZE = 6

DATA = 0x00
SETTINGS = 0x04

HEADER_STATE = 1

PAYLOAD_STATE = 2

FINISH_STATE = 3

class HTTP2Parser(parser.Parser):

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
            self._parse_header,
            self._parse_payload
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
        self.state = HEADER_STATE
        self.buffer = []
        self.length = 0
        self.type = 0
        self.flags = 0
        self.stream = 0

    def clear(self, force = False):
        if not force and self.state == HEADER_STATE: return
        self.reset()

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

    def _parse_header(self, data):
        if len(data) + self.buffer_size < HEADER_SIZE: return 0

        size = HEADER_SIZE - self.buffer_size
        data = self.buffer_data + data[:size]

        header = struct.unpack("!BHBBI", data)
        extra, self.length, self.type, self.flags, self.stream = header
        self.length += extra << 16

        self.state = PAYLOAD_STATE
        self.trigger("on_header", header)

        return size

    def _parse_payload(self, data):
        if len(data) + self.buffer_size < self.length: return 0

        size = self.length - self.buffer_size
        data = self.buffer_data + data[:size]

        if self.type == SETTINGS:
            self._parse_settings(data)

        self.state = FINISH_STATE
        self.trigger("on_frame")

        return size

    def _parse_settings(self, data):
        settings = []
        count = self.length // SETTING_SIZE

        for index in netius.legacy.xrange(count):
            base = index * SETTING_SIZE
            part = data[base:base + SETTING_SIZE]
            setting = struct.unpack("!HI", part)
            settings.append(setting)

        self.trigger("on_settings", settings)

    @property
    def buffer_size(self):
        return sum(len(data) for data in self.buffer)

    @property
    def buffer_data(self, empty = True):
        data = b"".join(self.buffer)
        if empty: del self.buffer[:]
        return data
