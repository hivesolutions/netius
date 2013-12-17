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

CODE_STRINGS = {
    100 : "Continue",
    101 : "Switching Protocols",
    200 : "OK",
    201 : "Created",
    202 : "Accepted",
    203 : "Non-Authoritative Information",
    204 : "No Content",
    205 : "Reset Content",
    206 : "Partial Content",
    207 : "Multi-Status",
    301 : "Moved permanently",
    302 : "Found",
    303 : "See Other",
    304 : "Not Modified",
    305 : "Use Proxy",
    306 : "(Unused)",
    307 : "Temporary Redirect",
    400 : "Bad Request",
    401 : "Unauthorized",
    402 : "Payment Required",
    403 : "Forbidden",
    404 : "Not Found",
    405 : "Method Not Allowed",
    406 : "Not Acceptable",
    407 : "Proxy Authentication Required",
    408 : "Request Timeout",
    409 : "Conflict",
    410 : "Gone",
    411 : "Length Required",
    412 : "Precondition Failed",
    413 : "Request Entity Too Large",
    414 : "Request-URI Too Long",
    415 : "Unsupported Media Type",
    416 : "Requested Range Not Satisfiable",
    417 : "Expectation Failed",
    500 : "Internal Server Error",
    501 : "Not Implemented",
    502 : "Bad Gateway",
    503 : "Service Unavailable",
    504 : "Gateway Timeout",
    505 : "HTTP Version Not Supported"
}
""" Dictionary associating the error code as integers
with the official descriptive message for it """

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
        self.encodings = None
        self.chunked = False
        self.chunk_d = 0
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

    def get_encodings(self):
        if not self.encodings == None: return self.encodings
        accept_encoding_s = self.headers.get("accept-encoding", "")
        self.encodings = [value.strip() for value in accept_encoding_s.split(",")]
        return self.encodings

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
            # iterates while the current state is valid for
            # parsing as there are only parsing methods for
            # the range of valid states
            if self.state <= self.state_l:

                # retrieves the parsing method for the current
                # state and then runs it retrieving the number
                # of valid parsed bytes in case this value is
                # zero the parsing iteration is broken
                method = self.states[self.state - 1]
                count = method(data)
                if count == 0: break

                # decrements the size of the data buffer by the
                # size of the parsed bytes and then retrieves the
                # sub part of the data buffer as the new data buffer
                size -= count
                data = data[count:]

                # continues the loop as there should be still some
                # data remaining to be parsed in the current buffer
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
        index = data.find("\n")
        if index == -1: return 0

        self.buffer.append(data[:index])
        self.line_s = "".join(self.buffer)[:-1]
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
            self.code = int(self.code_s)
            self.status = self.status_s

        # updates the current state of parsing to the header state
        # so that the headers are the next item to be processed
        self.state = HEADERS_STATE

        # triggers the on line event so that the listeners are notified
        # about the end of the parsing of the status line and then
        # returns the count of the parsed bytes of the message
        self.trigger("on_line")
        return index + 1

    def _parse_headers(self, data):
        # creates a temporary buffer with the contents of
        # the current buffer plus the current data and then
        # joins it to retrieve the current complete buffer
        # string to be used in the finding of the end of
        # header sequence (required for complete parsing)
        buffer_t = self.buffer + [data]
        buffer_s = "".join(buffer_t)

        # tries to find the end of headers sequence in case
        # it's not found returns the zero value meaning that
        # the no bytes have been processed (delays parsing)
        index = buffer_s.find("\r\n\r\n")
        if index == -1: return 0

        # retrieves the partial headers string from the buffer
        # string and then deletes the current buffer so that
        # it may be reused for other partial parsings
        self.headers_s = buffer_s[:index]
        del self.buffer[:]

        # calculates the base length as the difference between
        # the buffer string and the length of the currently
        # provided data value and then uses this value to calculate
        # the base index for the process data count value
        base_length = len(buffer_s) - len(data)
        base_index = index - base_length

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
        return base_index + 4

    def _parse_message(self, data):
        if self.chunked: return self._parse_chunked(data)
        else: return self._parse_normal(data)

    def _parse_normal(self, data):
        # retrieves the size of the data that has just been
        # received and then in case the store flag is set
        # adds the data to the message buffer and increments
        # the message length counter with the size of the data
        data_l = len(data)
        if self.store: self.message.append(data)
        self.message_l += data_l

        # verifies if the complete message has already been
        # received, that occurs if the content length is
        # defined and the value is the is the same as the
        # currently defined message length
        has_finished = not self.content_l == -1 and\
            self.message_l == self.content_l

        # triggers the partial data received event and then
        # in case the complete message has not been received
        # returns immediately the length of processed data
        self.trigger("on_partial", data)
        if not has_finished: return data_l

        # updates the current state to the finish state and then
        # triggers the on data event (indicating the end of the
        # parsing of the message)
        self.state = FINISH_STATE
        self.trigger("on_data")

        # returns the length of the processed data as the amount
        # of processed bytes by the current method
        return data_l

    def _parse_chunked(self, data):
        # starts the parsed byte counter with the initial zero
        # value this will be increment as bytes are parsed
        count = 0

        # verifies if the end of chunk state has been reached
        # that happen when only the last two character remain
        # to be parsed from the chunk
        is_end = self.chunk_l < 3 and self.chunk_l > 0
        if is_end:
            # calculates the size of the data that is going
            # to be parsed as that's required to check if
            # the end chunk state has been reached
            data_l = len(data)

            # in case the required amount of data has not
            # been received returns the parsed bytes amount
            # (count) immediately to the caller
            if data_l < self.chunk_l:
                self.chunk_l -= data_l
                count += data_l
                return count

            # adds the parsed number of bytes to the count value,
            # resets the pending length of the chunk to the initial
            # zero value and then returns that value to the caller
            count += self.chunk_l
            self.chunk_l = 0

            # in case the current chunk dimension (size) is
            # zero this is the last chunk and so the state
            # must be set to the finish and the on data event
            # must be triggered to indicate the end of message
            if self.chunk_d == 0:
                self.state = FINISH_STATE
                self.trigger("on_data")

            # otherwise this is the end of a "normal" chunk and
            # and so the end of chunk index must be calculated
            # and the chunk event must be triggered
            else:
                self.chunk_e = len(self.message)
                self.trigger("on_chunk", (self.chunk_s, self.chunk_e))

            # in case the message is not meant to be stored deletes
            # the contents of the message buffer
            if not self.store: del self.message[:]

            # returns the number of bytes that have been parsed by
            # the current end of chunk operation to the caller method
            return count

        # check if the start of the chunk state is the current one
        # does that by verifying that the current value for the chunk
        # length is zero (initial situation)
        is_start = self.chunk_l == 0
        if is_start:
            # tries to find the separator of the initial value for
            # the chunk in case it's not found returns immediately
            index = data.find("\n")
            if index == -1: return 0

            # some of the current data to the buffer and then re-joins
            # it as the header value, then removes the complete set of
            # contents from the buffer so that it may be re-used
            self.buffer.append(data[:index])
            header = "".join(self.buffer)[:-1]
            del self.buffer[:]

            # sets the new data buffer as the partial buffer of the data
            # except the extra newline character (not required)
            data = data[index + 1:]

            # splits the header value so that additional chunk information
            # is removed and then parsed the value as the original chunk
            # size (dimension) adding the two extra bytes to the length
            header_s = header.split(";", 1)
            size = header_s[0]
            self.chunk_d = int(size.strip(), base = 16)
            self.chunk_l = self.chunk_d + 2
            self.chunk_s = len(self.message)

            # increments the counter of the parsed number of bytes from the
            # provided data by the index of the newline character position
            # plus one byte respecting to the newline character
            count += index + 1

        # retrieve the partial data that is valid according to the
        # calculated chunk length and then calculates the size of
        # "that" partial data string value
        data = data[:self.chunk_l - 2]
        data_s = len(data)

        # adds the partial data to the message list and then decrement
        # the (remaining) chunk length by the size of the read data
        if data: self.message.append(data)
        self.chunk_l -= data_s

        # in case there's data parsed the partial data event
        # is triggered to notify handlers about the new data
        if data: self.trigger("on_partial", data)

        # increments the byte counter value by the size of the data
        # and then returns the same counter to the caller method
        count += data_s
        return count
