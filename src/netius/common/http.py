#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import re
import tempfile

import netius

from . import util
from . import parser

FILE_LIMIT = 5242880
""" The limit value (in bytes) from which the back-end
message storage mechanism will start using a file system
stored file instead of an in memory object, this way it's
possible to avoid memory starvation problems, this is a
default value for the parser and may be overriden using
the dedicated parameter value in the constructor """

REQUEST = 1
""" The HTTP request message indicator, should be
used when identifying the HTTP request messages """

RESPONSE = 2
""" Indicator for the response HTTP message, can be
used to identify chunks of data that represent an
HTTP based response """

LINE_STATE = 1
""" The initial state where the status line is meant
to be read as expected by the HTTP specification """

HEADERS_STATE = 2
""" State here the headers are waiting to be read this
state exits when the end of headers sequence is found
and the headers are parsed """

MESSAGE_STATE = 3
""" The message state for the situations where the message
is waiting to be processed (read) this state may persist
for some time if the message is big enough """

FINISH_STATE = 4
""" The final state set when the complete HTTP request or
response has been processed, if a parse operation starts
with this state the parsed is reseted """

PLAIN_ENCODING = 1
""" Plain text encoding that does not transform the
data from its based format, should be used only as
a fallback method because of performance issues """

CHUNKED_ENCODING = 2
""" Chunked based encoding that allows the sending of
the data as a series of length based parts """

GZIP_ENCODING = 3
""" The gzip based encoding used to compress data, this
kind of encoding will always used chunked encoding so
that the content may be send in parts """

DEFLATE_ENCODING = 4
""" The deflate based encoding used to compress data, this
kind of encoding will always used chunked encoding so
that the content may be send in parts """

HTTP_09 = 1
""" The enumeration value for the temporary and beta HTTP
version 0.9 version (very rare) """

HTTP_10 = 2
""" Value for the first version of the HTTP specification,
connection running under this version should be closed right
away as defined in the specification """

HTTP_11 = 3
""" Current version of the HTTP specification should be the
most commonly used nowadays, connection running under this
version of the protocol should keep connections open """

VERSIONS_MAP = {
    "HTTP/0.9" : HTTP_09,
    "HTTP/1.0" : HTTP_10,
    "HTTP/1.1" : HTTP_11
}
""" Maps associating the standard HTTP version string with the
corresponding enumeration based values for each of them """

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

HEADER_NAME_REGEX = re.compile(r"^[\!\#\$\%\&'\*\+\-\.\^\_\`\~0-9a-zA-Z]+$")
""" Regular expression to be used in the validation of the
header naming tokens, so that only the valid names are captured
avoiding possible security issues, should be compliant with RFC 7230 """

class HTTPParser(parser.Parser):
    """
    Parser object for the HTTP format, should be able to
    parse both request and response messages.

    The parser itself should be event driven an callback
    functions should be called upon partials information
    parsing. But the object itself is not thread safe.
    """

    FIELDS = (
        "_pid",
        "type",
        "store",
        "file_limit",
        "state",
        "buffer",
        "headers",
        "message",
        "method",
        "version",
        "code",
        "keep_alive",
        "line_s",
        "headers_s",
        "method_s",
        "path_s",
        "version_s",
        "code_s",
        "status_s",
        "connection_s",
        "message_s",
        "message_f",
        "content_l",
        "message_l",
        "transfer_e",
        "encodings",
        "chunked",
        "chunk_d",
        "chunk_l",
        "chunk_s",
        "chunk_e"
    )

    def __init__(
        self,
        owner,
        type = REQUEST,
        store = False,
        file_limit = FILE_LIMIT
    ):
        parser.Parser.__init__(self, owner)

        self.build()
        self.reset(type = type, store = store, file_limit = file_limit)

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        self.connection = self.owner

        self.states = (
            self._parse_line,
            self._parse_headers,
            self._parse_message
        )
        self.state_l = len(self.states)

    def destroy(self):
        """
        Destroys the current structure for the parser meaning that
        it's restored to the original values, this method should only
        be called on situation where no more parser usage is required.
        """

        parser.Parser.destroy(self)

        self.clear()
        self.close()

        self.connection = None
        self.states = ()
        self.state_l = 0

    def reset(self, type = REQUEST, store = False, file_limit = FILE_LIMIT):
        """
        Initializes the state of the parser setting the values
        for the various internal structures to the original value.
        After this operation the parser is ready for a new parse.

        :type type: int
        :param type: The type of HTTP message that is going to be
        parsed using the current parser.
        :type store: bool
        :param store: If the complete message body should be stored
        in memory as the message gets loaded, this option may create
        some serious performance issues.
        :type file_limit: int
        :param file_limit: The maximum content for the payload message
        from which a in file buffer will be used instead of the one that
        is stored in memory (avoid memory starvation).
        """

        self.close()
        self.type = type
        self.store = store
        self.file_limit = file_limit
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
        self.message_f = None
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
        self.reset(
            type = self.type,
            store = self.store,
            file_limit = self.file_limit
        )

    def close(self):
        if hasattr(self, "message") and self.message: self.message = []
        if hasattr(self, "message_f") and self.message_f: self.message_f.close()

    def get_path(self, normalize = False):
        """
        Retrieves the path associated with the request, this
        value should be interpreted from the HTTP status line.

        In case the normalize flag is set a possible absolute
        URL value should be normalized into an absolute path.
        This may be required under some proxy related scenarios.

        :type normalize: bool
        :param normalize: If the normalization process should be
        applied for absolute URL scenarios.
        :rtype: String
        :return: The path associated with the current request.
        """

        split = self.path_s.split("?", 1)
        path = split[0]
        if not normalize: return path
        if not path.startswith(("http://", "https://")): return path
        return netius.legacy.urlparse(path).path

    def get_query(self):
        """
        Retrieves the (GET) query part of the path, this is considered
        to be the part of the path after the first question mark.

        This query string may be used to parse any possible (GET)
        arguments.

        :rtype: String
        :return: The query part of the path, to be used for parsing
        of (GET) arguments.
        """

        split = self.path_s.split("?", 1)
        if len(split) == 1: return ""
        else: return split[1]

    def get_message(self):
        """
        Gathers the complete set of message contents for the current
        request/response in parsing. The proper gathering strategy will
        depend on the current strategy (eg: in memory vs file strategies).

        The result of this process is cached meaning that further calls
        to this method will return the same result.

        This method should be used carefully as it may create some memory
        performance issues when retrieving large message values.

        :rtype: String
        :return: The message for the current parsing process as a linear
        string value that may be used as a simple buffer.
        """

        if self.message_s: return self.message_s
        if self.message_f: self.message_s = self.get_message_f()
        else: self.message_s = b"".join(self.message)
        return self.message_s

    def get_message_f(self):
        self.message_f.seek(0)
        return self.message_f.read()

    def get_message_b(self, copy = False, size = 40960):
        """
        Retrieves a new buffer associated with the currently
        loaded message, the first time this method is called a
        new in memory object will be created for the storage.

        In case the current parsing operation is using a file like
        object for the handling this object it is returned instead.

        The call of this method is only considered to be safe after
        the complete message has been received and processed, otherwise
        and invalid message file structure may be created.

        Note that the returned object will always be set at the
        beginning of the file, so some care should be taken in usage.

        :type copy: bool
        :param copy: If a copy of the file object should be returned
        or if instead the shallow copy associated with the parser should
        be returned instead, this should be used carefully to avoid any
        memory leak from file descriptors.
        :type size: int
        :param size: Size (in bytes) of the buffer to be used in a possible
        copy operation between buffers.
        :rtype: File
        :return: The file like object that may be used to percolate
        over the various parts of the current message contents.
        """

        # in case there's not message file currently enabled creates one
        # and writes the value of the message into it
        if not self.message_f:
            self.message_f = netius.legacy.BytesIO()
            for value in self.message: self.message_f.write(value)

        # restores the message file to the original/initial position and
        # then in case there's no copy required returns it immediately
        self.message_f.seek(0)
        if not copy: return self.message_f

        # determines if the file limit for a temporary file has been
        # surpassed and if that's the case creates a named temporary
        # file, otherwise created a memory based buffer
        use_file = self.store and self.content_l >= self.file_limit
        if use_file: message_f = tempfile.NamedTemporaryFile(mode = "w+b")
        else: message_f = netius.legacy.BytesIO()

        try:
            # iterates continuously reading the contents from the message
            # file and writing them back to the output (copy) file
            while True:
                data = self.message_f.read(size)
                if not data: break
                message_f.write(data)
        finally:
            # resets both of the message file (output and input) to the
            # original position as expected by the infra-structure
            self.message_f.seek(0)
            message_f.seek(0)

        # returns the final (copy) of the message file to the caller method
        # note that the type of this file may be an in memory or stored value
        return message_f

    def get_headers(self):
        headers = dict(self.headers)
        for key, value in netius.legacy.iteritems(self.headers):
            key_up = util.header_up(key)
            del headers[key]
            headers[key_up] = value
        return headers

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

                # must clear the current parser state, so that it may
                # start the parsing of a new message and then continue
                # the loop trying to find new contents for parsing, this
                # critical for HTTP pipelining support
                self.clear()
                continue

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
        # tries to find the final newline value in the provided
        # data in case there's one it's considered that the the
        # initial line must have been found
        index = data.find(b"\n")
        if index == -1: return 0

        # adds the partial data (until line ending) to the buffer
        # and then joins the buffer as the initial line, this value
        # should not include the final newline characters, after that
        # the buffer is cleared as new data is going to be stored for
        # (remaining part of the request or response)
        self.buffer.append(data[:index])
        self.line_s = b"".join(self.buffer).rstrip()
        self.line_s = netius.legacy.str(self.line_s)
        del self.buffer[:]

        # restores the final end of line sequence to the buffer, this
        # allows "simple requests" to be parsed properly in under the
        # next section of parsing headers (required for compliance)
        self.buffer.append(b"\r\n")

        # splits the line around its various components, verifying than
        # that the number of provided items is the expected one, notice
        # that for responses the parsing is relaxed as the status string
        # can be an empty string (no message to be presented)
        values = self.line_s.split(" ", 2)
        if self.type == RESPONSE and len(values) == 2: values.append("")
        if not len(values) == 3: raise netius.ParserError(
            "Invalid status line '%s'" % self.line_s
        )

        # determines if the current type of parsing is request based
        # and if that's the case unpacks the status line as a request
        if self.type == REQUEST:
            self.method_s, self.path_s, self.version_s = values
            self.method = self.method_s.lower()
            self.version = VERSIONS_MAP.get(self.version_s, HTTP_10)

        # otherwise ensures that the parsing type is response based
        # and unpacks the status line accordingly
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
        buffer_s = b"".join(buffer_t)

        # tries to find the end of headers sequence in case
        # it's not found returns the zero value meaning that
        # the no bytes have been processed (delays parsing)
        index = buffer_s.find(b"\r\n\r\n")
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
        lines = self.headers_s.split(b"\r\n")
        for line in lines:
            # verifies if the line contains any information if
            # that's not the case the current cycle must be
            # skipped as this may be an extra empty line
            if not line: continue

            # tries to split the line around the key to value
            # separator in case there's no valid split (two
            # values were not found) an exception must be raised
            values = line.split(b":", 1)
            if not len(values) == 2:
                raise netius.ParserError("Invalid header line")

            # unpacks both the key and the value and runs some
            # parsing validation to ensure proper HTTP compliance
            key, value = values

            # normalizes the header key and converts it into a string
            # then validates its conformance according to the RFC 7230
            # so that their components have verified compliance
            key = key.lower()
            key = netius.legacy.str(key)
            if not HEADER_NAME_REGEX.match(key):
                raise netius.ParserError("Invalid header key")

            # obtains the value and removes any extra space value from
            # both the beginning and the end of it, then makes sure that
            # no extra "space like" character exist in it
            value = value.strip(b" ")
            value = netius.legacy.str(value, errors = "replace")
            if not value == value.strip():
                raise netius.ParserError("Invalid header value")

            # in case the header already exists this indicates that
            # there are multiple definitions of the header and a sequence
            # must be used in order to store the various headers
            exists = key in self.headers
            if exists:
                sequence = self.headers[key]
                is_list = type(sequence) == list
                if not is_list: sequence = [sequence]
                sequence.append(value)
                value = sequence

            # sets the final header value into the headers map so that
            # it may be used latter for the serialization process
            self.headers[key] = value

        # retrieves the size of the contents from the populated
        # headers, this is not required by the specification and
        # the parser should be usable even without it
        self.content_l = self.headers.get("content-length", -1)
        self.content_l = self.content_l and int(self.content_l)

        # verifies if a back-end file object should be used to store
        # the file contents, this is done by checking the store flag
        # and verifying that the file limit value has been reached
        use_file = self.store and self.content_l >= self.file_limit
        if use_file: self.message_f = tempfile.NamedTemporaryFile(mode = "w+b")

        # retrieves the type of transfer encoding that is going to be
        # used in the processing of this request in case it's of type
        # chunked sets the current chunked flag indicating that the
        # request is meant to be processed as so
        self.transfer_e = self.headers.get("transfer-encoding", None)
        self.chunked = self.transfer_e == "chunked"

        # verifies if the transfer encoding is compliant with the expected
        # kind of transfer encodings, if not fails with a parsing error
        if not self.transfer_e in (None, "identity", "chunked"):
            raise netius.ParserError("Invalid transfer encoding")

        # verifies that if the chunked encoding is requested then the content
        # length value must be unset (as expected)
        if self.chunked and not self.content_l == -1:
            raise netius.ParserError("Chunked encoding with content length set")

        # in case the current response in parsing has the no content
        # code (no payload present) the content length is set to the
        # zero value in case it has not already been populated
        if self.type == RESPONSE and self.code in (204, 304) and\
            self.content_l == -1: self.content_l = 0

        # in case the current request is not chunked and the content length
        # header is not defined the content length is set to zero because
        # for normal requests with payload the content length is required
        # and if it's omitted it means there's no payload present
        if self.type == REQUEST and not self.chunked and\
            self.content_l == -1: self.content_l = 0

        # verifies if the connection is meant to be kept alive by
        # verifying the current value of the connection header against
        # the expected keep alive string value, note that the verification
        # takes into account a possible list value in connection
        self.connection_s = self.headers.get("connection", None)
        if type(self.connection_s) == list: self.connection_s = self.connection_s[0]
        self.connection_s = self.connection_s and self.connection_s.lower()
        self.keep_alive = self.connection_s == "keep-alive"
        self.keep_alive |= self.connection_s == None and self.version >= HTTP_11

        # verifies if the current message has finished, for those
        # situations an extra (finish) state change will be issued
        has_finished = self.content_l == 0

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
        # stores the data in the proper buffer and increments
        # the message length counter with the size of the data
        data_l = len(data)
        if self.store: self._store_data(data)
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
        # that happens when only the last two characters remain
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

            # in case the message is not meant to be stored or in
            # case the file storage mode is active (spares memory),
            # deletes the contents of the message buffer as they're
            # not going to be used to access request's data as a whole
            if not self.store or self.message_f: del self.message[:]

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
            index = data.find(b"\n")
            if index == -1: return 0

            # some of the current data to the buffer and then re-joins
            # it as the header value, then removes the complete set of
            # contents from the buffer so that it may be re-used
            self.buffer.append(data[:index])
            header = b"".join(self.buffer)[:-1]
            del self.buffer[:]

            # sets the new data buffer as the partial buffer of the data
            # except the extra newline character (not required)
            data = data[index + 1:]

            # splits the header value so that additional chunk information
            # is removed and then parsed the value as the original chunk
            # size (dimension) adding the two extra bytes to the length
            header_s = header.split(b";", 1)
            size = header_s[0]
            self.chunk_d = int(size.strip(), base = 16)
            self.chunk_l = self.chunk_d + 2
            self.chunk_s = len(self.message)

            # increments the counter of the parsed number of bytes from the
            # provided data by the index of the newline character position
            # plus one byte respecting to the newline character
            count += index + 1

        # retrieves the partial data that is valid according to the
        # calculated chunk length and then calculates the size of
        # "that" partial data string value
        data = data[:self.chunk_l - 2]
        data_s = len(data)

        # adds the partial data to the message list and runs the store operation
        # just in case the storage of the data in file is required, then decrements
        # the (remaining) chunk length by the size of the read data, note that
        # the message buffer is used even if the store flag is not set, so that
        # it's possible to refer the chunk as a tuple of start and end indexes when
        # triggering the chunk parsed (on chunk) event (performance gains)
        if data: self.message.append(data)
        if data and self.store: self._store_data(data, memory = False)
        self.chunk_l -= data_s

        # in case there's data parsed the partial data event
        # is triggered to notify handlers about the new data
        if data: self.trigger("on_partial", data)

        # increments the byte counter value by the size of the data
        # and then returns the same counter to the caller method
        count += data_s
        return count

    def _store_data(self, data, memory = True):
        if not self.store: raise netius.ParserError("Store is not possible")
        if self.message_f: self.message_f.write(data)
        elif memory: self.message.append(data)

    def _parse_query(self, query):
        # runs the "default" parsing of the query string from the system
        # and then decodes the complete set of parameters properly
        params = netius.legacy.parse_qs(query, keep_blank_values = True)
        return self._decode_params(params)

    def _decode_params(self, params):
        _params = dict()

        for key, value in netius.legacy.iteritems(params):
            items = []
            for item in value:
                is_bytes = netius.legacy.is_bytes(item)
                if is_bytes: item = item.decode("utf-8")
                items.append(item)
            is_bytes = netius.legacy.is_bytes(key)
            if is_bytes: key = key.decode("utf-8")
            _params[key] = items

        return _params

class HTTPResponse(object):

    def __init__(self, data = None, code = 200, status = None, headers = None):
        self.data = data
        self.code = code
        self.status = status
        self.headers = headers

    def read(self):
        return self.data

    def readline(self):
        return self.read()

    def close(self):
        pass

    def getcode(self):
        return self.code

    def info(self):
        return self.headers
