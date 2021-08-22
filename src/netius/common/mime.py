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
import mimetypes

import netius

LINE_REGEX = re.compile(b"\r?\n")
""" The regular expression that is going to be used in the
separation of the various lines of the message for the proper
parsing of it, notice the carriage return and new line support """

SPACE_REGEX = re.compile(b"[\t ]")
""" Regular expression used for the matching of all the characters
considered valid for the spaces in the start of a continuation
line for an header value as part of the rfc822 """

HEADER_NAME_REGEX = re.compile(b"([\x21-\x7e]+?):")
""" The regular expression to be used for the matching of the
name part of the header, this should be used do decide if a line
corresponds to an header line or not """

MIME_TYPES = (
    (".csv", "text/csv"),
    (".ini", "text/plain"),
    (".js", "application/javascript"),
    (".log", "text/plain"),
    (".mka", "audio/x-matroska"),
    (".mkv", "video/x-matroska"),
    (".woff", "application/font-woff")
)
""" The sequence containing tuple associating the extension with
the mime type or content type string """

MIME_REGISTERED = False
""" Flag that controls if the mime registration process has already
been performed, avoiding possible duplicated registration that would
spend unnecessary resources """

class Headers(list):
    """
    Mutable structure that allow the access to header tuples
    using both a list style strategy and a dictionary based
    strategy, providing easy manipulation of the items.

    The order of insertion is preserved so that it may be
    respected if a re-construction of the message is required.
    """

    def __getitem__(self, key):
        is_integer = isinstance(key, int)
        if is_integer: return list.__getitem__(self, key)
        for _key, value in self:
            if not _key == key: continue
            return value
        raise KeyError("not found")

    def __setitem__(self, key, value):
        key = self._normalize(key)
        value = self._normalize(value)
        is_integer = isinstance(key, int)
        if is_integer: return list.__setitem__(self, key, value)
        self.append([key, value])

    def __delitem__(self, key):
        is_integer = isinstance(key, int)
        if is_integer: return list.__delitem__(self, key)
        value = self.__getitem__(key)
        self.remove([key, value])

    def __contains__(self, item):
        is_string = isinstance(item, netius.legacy.ALL_STRINGS)
        if not is_string: return list.__contains__(self, item)
        for key, _value in self:
            if not key == item: continue
            return True
        return False

    def item(self, key):
        for item in self:
            if not item[0] == key: continue
            return item
        raise KeyError("not found")

    def get(self, key, default = None):
        if not key in self: return default
        return self[key]

    def set(self, key, value, append = False):
        key = self._normalize(key)
        value = self._normalize(value)
        if key in self and not append: self.item(key)[1] = value
        else: self[key] = value

    def pop(self, key, default = None):
        if not key in self: return default
        value = self[key]
        del self[key]
        return value

    def join(self, separator = "\r\n"):
        separator = netius.legacy.bytes(separator)
        return separator.join([key + b": " + value for key, value in self])

    def _normalize(self, value):
        value_t = type(value)
        if value_t == netius.legacy.BYTES: return value
        if value_t == netius.legacy.UNICODE: return value.encode("utf-8")
        return netius.legacy.bytes(str(value))

def rfc822_parse(message, strip = True):
    """
    Parse a message in rfc822 format. This format is similar to
    the mime one with only some small changes. The returning value
    for this function a set of dictionary tuples and the body of
    the processed message as a standard encoded string.

    :type message: String
    :param message: The message in rfc822 format, with both carriage
    return and line feed support.
    :type strip: bool
    :param strip: If the initial white spaces in the first header line
    should be removed and the proper abstract structure created with no
    extra space values (no strict representation). This should not be
    used when the strict representation of the headers is required
    (eg: for cryptographic signing purposes).
    :rtype: Tuple
    :return: Returns a tuple of headers and body where headers is
    a list of (name and value) pairs.
    """

    # starts both the line index value and the list that will
    # hold the ordered header values for the message
    index = 0
    headers = Headers()

    # strips the message from any possible starting line characters
    # this sometimes happens for message transmission
    message = message.lstrip()

    # splits the various lines of the message around the various
    # pre-defined separator tokens
    lines = LINE_REGEX.split(message)

    # iterates over all the lines to process the complete set of
    # headers currently defined for the message and determine the
    # start (line) index for the message body
    for line in lines:
        # in case an empty/invalid line has been reached the
        # end of headers have been found (must break the loop)
        if not line: break

        # retrieves the value for the current byte so that it's
        # possible to try to match it against the various regular
        # expression that are part of the parsing loop (line loop)
        byte = netius.legacy.chr(line[0])

        # verifies if this is a continuation line, these lines
        # start with either a space or a tab character, for those
        # situations the contents of the current line must be
        # added to the previously parsed header
        if SPACE_REGEX.match(byte):
            headers[-1][1] += b"\r\n" + line

        # otherwise it's a "normal" header parsing step and the typical
        # header regular expression match strategy is going to be used
        else:
            # tries to run the matching process for message header names
            # against the message line, to be able to "extract" the header
            match = HEADER_NAME_REGEX.match(line)

            # in case there was a valid match for the header tag, processed
            # it by separating the name from the value of the header and
            # creating the proper header tuple adding it to the list of headers
            if match:
                name = match.group(1)
                value = line[match.end(0):]
                if strip: value = value.lstrip()
                headers.append([name, value])

            # otherwise in case the line is a from line formatted
            # using an old fashion strategy tolerates it (compatibility)
            elif line.startswith(b"From "): pass

            # as a fallback raises a parser error as no parsing of header
            # was possible for the message (major problem)
            else: raise netius.ParserError("Unexpected header value")

        # increments the current line index counter, as one more
        # line has been processed by the parser
        index += 1

    # joins the complete set of "remaining" body lines creating the string
    # representing the body, and uses it to create the headers and body
    # tuple that is going to be returned to the caller method
    body_lines = lines[index + 1:]
    body = b"\r\n".join(body_lines)
    return (headers, body)

def rfc822_join(headers, body):
    headers_s = headers.join()
    return headers_s + b"\r\n\r\n" + body

def mime_register():
    global MIME_REGISTERED
    if MIME_REGISTERED: return
    for extension, mime_type in MIME_TYPES:
        mimetypes.add_type(mime_type, extension)
    MIME_REGISTERED = True

mime_register()
