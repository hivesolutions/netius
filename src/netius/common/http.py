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

import cStringIO

import netius

REQUEST = 1
""" The http request message indicator, should be
used when identifying the http request messages """

RESPONSE = 2
""" Indicator for the response http message, can be
used to identify chunks of data that represent an
http based response """

LINE_STATE = 1

HEADERS_STATE = 2

MESSAGE_STATE = 3

FINISH_STATE = 4

HTTP_09 = 1

HTTP_10 = 2

HTTP_11 = 3

VERSIONS_MAP = {
    "HTTP/0.9" : HTTP_09,
    "HTTP/1.0" : HTTP_10,
    "HTTP/1.1" : HTTP_11
}

class HTTPParser(netius.Observable):
    """
    Parser object for the http format, should be able to
    parse both request and response messages.

    The parser itself should be event driven an callback
    functions should be called upon partials information
    parsing. But the object itself is not thread safe.
    """

    def __init__(self, type = REQUEST):
        netius.Observable.__init__(self)

        self.reset(type = type)

    def reset(self, type = REQUEST):
        """
        Initializes the state of the parser setting the values
        for the various internal structures to the original value.
        After this operation the parser is ready for a new parse.

        @type type: int
        @param type: The type of http message that is going to be
        parsed using the current parser.
        """

        self.type = type
        self.state = LINE_STATE
        self.buffer = []
        self.headers = {}
        self.message = []
        self.method = None
        self.version = None
        self.code = None
        self.keep_alive = False
        self.line_s = None
        self.headers_s = None
        self.method_s = None
        self.path_s = None
        self.version_s = None
        self.code_s = None
        self.status_s = None
        self.connection_s = None
        self.message_s = None
        self.content_l = -1
        self.message_l = 0

    def get_path(self):
        split = self.path_s.split("?", 1)
        return split[0]

    def get_query(self):
        split = self.path_s.split("?", 1)
        if len(split) == 1: return ""
        else: return split[1]

    def get_message(self):
        if not self.message_s: self.message_s = "".join(self.message)
        return self.message_s

    def get_message_b(self):
        buffer = cStringIO.StringIO()
        for value in self.message: buffer.write(value)
        buffer.seek(0)
        return buffer

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
        if self.state == FINISH_STATE: self.reset(type = self.type)

        # retrieves the size of the data that has been sent for parsing
        # and saves it under the size original variable
        size = len(data)
        size_o = size

        # iterates continuously to try to process all that
        # data that has been sent for processing
        while size > 0:

            if self.state == LINE_STATE:
                count = self._parse_line(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == HEADERS_STATE:
                count = self._parse_headers(data)
                if count == 0: break

                size -= count
                data = data[count:]

                continue

            elif self.state == MESSAGE_STATE:
                count = self._parse_message(data)
                if count == 0: break

                size -= count
                data = data[count:]
                self.state = MESSAGE_STATE

                continue

            elif self.state == FINISH_STATE:
                break

            else:
                raise RuntimeError("invalid state '%d'" % self.state)

        # in case not all of the data has been processed
        # must add it to the buffer so that it may be used
        # latter in the next parsing of the message
        if size > 0: self.buffer.append(data)

        # returns the number of read (processed) bytes of the
        # data that has been sent to the parser
        return size_o - size

    def _parse_line(self, data):
        index = data.find("\r\n")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.line_s = "".join(self.buffer)
        del self.buffer[:]

        values = self.line_s.split(" ", 2)
        if not len(values) == 3:
            raise RuntimeError("invalid status line")

        if self.type == REQUEST:
            self.method_s, self.path_s, self.version_s = values
            self.method = self.method_s.lower()
            self.version = VERSIONS_MAP.get(self.version_s, HTTP_10)
        elif self.type == RESPONSE:
            self.version_s, self.code_s, self.status_s = values
            self.version = VERSIONS_MAP.get(self.version_s, HTTP_10)
            self.status = int(self.code_s)

        # updates the current state of parsing to the message state
        # as that the status line are the headers
        self.state = HEADERS_STATE

        # triggers the on line event so that the listeners are notified
        # about the end of the parsing of the status line and then
        # returns the count of the parsed bytes of the message
        self.trigger("on_line")
        return index + 2

    def _parse_headers(self, data):
        index = data.find("\r\n\r\n")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.headers_s = "".join(self.buffer)
        del self.buffer[:]

        # splits the complete set of lines that compromise
        # the headers and then iterates over each of them
        # to set the key and value in the headers map
        lines = self.headers_s.split("\r\n")
        for line in lines:
            values = line.split(":", 1)
            if not len(values) == 2:
                raise RuntimeError("invalid header line")

            key, value = values
            key = key.strip().lower()
            value = value.strip()
            self.headers[key] = value

        # retrieves the size of the contents from the populated
        # headers, this is not required by the specification and
        # the parser should be usable even without it
        self.content_l = self.headers.get("content-length", None)
        self.content_l = self.content_l and int(self.content_l)

        # verifies if the connection is meant to be kept alive by
        # verifying the current value of the connection header against
        # the expected keep alive string value
        self.connection_s = self.headers.get("connection", None)
        self.connection_s = self.connection_s and self.connection_s.lower()
        self.keep_alive = self.connection_s == "keep-alive"

        # verifies if the current message has finished, for those
        # situations an extra state change will be issued
        has_finished = self.method == "get" or self.content_l == 0

        # updates the current state of parsing to the message state
        # as that the headers are followed by the message
        if has_finished: self.state = FINISH_STATE
        else: self.state = MESSAGE_STATE

        # triggers the on headers event so that the listener object
        # is notified about the parsing of the headers and than returns
        # the parsed amount of information (bytes) to the caller
        self.trigger("on_headers")
        if has_finished: self.trigger("on_data")
        return index + 4

    def _parse_message(self, data):
        data_l = len(data)
        self.message.append(data)
        self.message_l += data_l

        has_finished = not self.content_l == -1 and\
            self.message_l == self.content_l

        if not has_finished: return data_l

        self.state = FINISH_STATE

        self.trigger("on_data")
        return data_l
