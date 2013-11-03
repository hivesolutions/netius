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
""" The initial state where the status line is meant
to be read as expected by the http specification """

HEADERS_STATE = 2
""" State here the headers are waiting to be read this
state exits when the end of headers sequence is found
and the headers are parsed """

MESSAGE_STATE = 3
""" The message state for the situations where the message
is waiting to be processed (read) this state may persist
for some time if the message is big enough """

FINISH_STATE = 4
""" The final state set when the complete http request or
response has been processed, if a parse operation starts
with this state the parsed is reseted """

HTTP_09 = 1
""" The enumeration value for the temporary and beta http
version 0.9 version (very rare) """

HTTP_10 = 2
""" Value for the first version of the http specification,
connection running under this version should be closed right
away as defined in the specification """

HTTP_11 = 3
""" Current version of the http specification should be the
most commonly used nowadays, connection running under this
version of the protocol should keep connections open """

VERSIONS_MAP = {
    "HTTP/0.9" : HTTP_09,
    "HTTP/1.0" : HTTP_10,
    "HTTP/1.1" : HTTP_11
}
""" Maps associating the standard http version string with the
corresponding enumeration based values for each of them """

EMPTY_METHODS = ("get", "connect")
""" Set of http methods that are considered to have no payload
and so no content length is required for any of these methods """

class HTTPParser(netius.Observable):
    """
    Parser object for the http format, should be able to
    parse both request and response messages.

    The parser itself should be event driven an callback
    functions should be called upon partials information
    parsing. But the object itself is not thread safe.
    """

    def __init__(self, owner, type = REQUEST, store = False):
        netius.Observable.__init__(self)

        self.owner = owner
        self.build()
        self.reset(type = type, store = store)

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        self.states = (
            self._parse_line,
            self._parse_headers,
            self._parse_message
        )
        self.state_l = len(self.states)

    def reset(self, type = REQUEST, store = False):
        """
        Initializes the state of the parser setting the values
        for the various internal structures to the original value.
        After this operation the parser is ready for a new parse.

        @type type: int
        @param type: The type of http message that is going to be
        parsed using the current parser.
        @type store: bool
        @param store: If the complete message body should be stored
        in memory as the message gets loaded, this option may create
        some serious performance issues.
        """

        self.type = type
        self.store = store
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
        self.transfer_e = None
        self.chunked = False
        self.chunk_l = 0
        self.chunk_s = 0
        self.chunk_e = 0

    def clear(self, force = False):
        if not force and self.state == LINE_STATE: return
        self.reset(self.type, self.store)

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

    def _parse_line(self, data):
        index = data.find("\r\n")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.line_s = "".join(self.buffer)
        del self.buffer[:]

        values = self.line_s.split(" ", 2)
        if not len(values) == 3:
            raise netius.ParserError("Invalid status line '%s'" % self.line_s)

        if self.type == REQUEST:
            self.method_s, self.path_s, self.version_s = values
            self.method = self.method_s.lower()
            self.version = VERSIONS_MAP.get(self.version_s, HTTP_10)
        elif self.type == RESPONSE:
            self.version_s, self.code_s, self.status_s = values
            self.version = VERSIONS_MAP.get(self.version_s, HTTP_10)
            self.status = int(self.code_s)

        # updates the current state of parsing to the header state
        # so that the headers are the next item to be processed
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
                raise netius.ParserError("Invalid header line")

            key, value = values
            key = key.strip().lower()
            value = value.strip()
            self.headers[key] = value

        # retrieves the size of the contents from the populated
        # headers, this is not required by the specification and
        # the parser should be usable even without it
        self.content_l = self.headers.get("content-length", -1)
        self.content_l = self.content_l and int(self.content_l)

        # retrieves the type of transfer encoding that is going to be
        # used in the processing of this request in case it's of type
        # chunked sets the current chunked flag indicating that the
        # request is meant to be processed as so
        self.transfer_e = self.headers.get("transfer-encoding", None)
        self.chunked = self.transfer_e == "chunked"

        # verifies if the connection is meant to be kept alive by
        # verifying the current value of the connection header against
        # the expected keep alive string value
        self.connection_s = self.headers.get("connection", None)
        self.connection_s = self.connection_s and self.connection_s.lower()
        self.keep_alive = self.connection_s == "keep-alive"

        # verifies if the current message has finished, for those
        # situations an extra state change will be issued
        has_finished = self.method in EMPTY_METHODS or self.content_l == 0

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
        if self.chunked: return self._parse_chunked(data)
        else: return self._parse_normal(data)

    def _parse_normal(self, data):
        data_l = len(data)
        if self.store: self.message.append(data)
        self.message_l += data_l

        has_finished = not self.content_l == -1 and\
            self.message_l == self.content_l

        self.trigger("on_partial", data)

        if not has_finished: return data_l

        self.state = FINISH_STATE

        self.trigger("on_data")
        return data_l

    def _parse_chunked(self, data):
        count = 0

        is_end = self.chunk_l == 2
        if is_end:
            self.chunk_e = len(self.message)
            self.trigger("on_chunk", (self.chunk_s, self.chunk_e))
            if not self.store: del self.message[:]
            self.chunk_l = 0
            count += 2
            return count

        is_start = self.chunk_l == 0
        if is_start:
            try: header, data = data.split("\r\n", 1)
            except: return count
            header_s = header.split(";", 1)
            size = header_s[0]
            self.chunk_l = int(size.strip(), base = 16) + 2
            self.chunk_s = len(self.message)

            count += len(header) + 2

        is_final = is_start and self.chunk_l == 2
        if is_final:
            self.state = FINISH_STATE
            self.trigger("on_data")
            index = data.find("\r\n")
            if index == -1: return count
            self.chunk_l = 0
            return count + 2

        data = data[:self.chunk_l - 2]
        data_s = len(data)

        self.message.append(data)
        self.chunk_l -= data_s

        self.trigger("on_partial", data)

        count += data_s

        return count
