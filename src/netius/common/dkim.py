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

import re

import netius

LINE_REGEX = re.compile(r"\r?\n")
""" The regular expression that is going to be used in the
separation of the various lines of the message for the proper
parsing of it, notice the carriage return and new line support """

SPACE_REGEX = re.compile(r"[\t ]")

HEADER_NAME_REGEX = re.compile(r"([\x21-\x7e]+?):")

def rfc822_parse(message, exclude = ()):
    """
    Parse a message in rfc822 format. This format is similar to
    the mime one with only some small changes. The returning value
    for this function a set of dictionary tuples and the body of
    the processed message as a standard encoded string.

    @type message: String
    @param message: The message in rfc822 format, with both Carriage
    return and line feed support.
    @rtype: Tuple
    @return Returns a tuple of headers and body where headers is
    a list of (name and value) pairs.
    """

    headers = []
    lines = LINE_REGEX.split(message)

    index = 0

    # iterates over all the lines to process the complete set of
    # headers currently defined for the message and determine the
    # start (line) index for the message body
    for line in lines:
        # in case an empty/invalid line has been reached the
        # end of headers have been found (must break the loop)
        if not line: break

        # verifies if this is a continuation line, these lines
        # start with either a space or a tab character, for those
        # situations the contents of the current line must be
        # added to the previously parsed header
        if SPACE_REGEX.match(line[0]):
            headers[-1][1] += line + "\r\n"

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
                value = line[match.end(0):] + "\r\n"
                headers.append([name, value])

            # otherwise in case the line is a from line formatted
            # using an old fashion strategy tolerates it (compatibility)
            elif line.startswith("From "): pass

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
    body = "\r\n".join(body_lines)
    return (headers, body)

def dkim_sign(message, selector, domain, private_key):
    headers, body = rfc822_parse(message)
