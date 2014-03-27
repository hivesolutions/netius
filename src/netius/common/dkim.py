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
    lines = re.split("\r?\n", message)
    i = 0
    while i < len(lines):
        if len(lines[i]) == 0:
            # End of headers, return what we have plus the body, excluding the blank line.
            i += 1
            break
        if re.match(r"[\x09\x20]", lines[i][0]):
            headers[-1][1] += lines[i]+"\r\n"
        else:
            m = re.match(r"([\x21-\x7e]+?):", lines[i])
            if m is not None:
                headers.append([m.group(1), lines[i][m.end(0):]+"\r\n"])
            elif lines[i].startswith("From "):
                pass
            else:
                raise MessageFormatError("Unexpected characters in RFC822 header: %s" % lines[i])
        i += 1
    return (headers, "\r\n".join(lines[i:]))

def dkim_sign(message, selector, domain, private_key):
    headers, body = rfc822_parse(message)
