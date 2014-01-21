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

import netius

class SMTPParser(netius.Observable):

    def __init__(self, owner, store = False):
        netius.Observable.__init__(self)

        self.owner = owner
        self.buffer = []

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

        # retrieves the size of the data that has been sent for parsing
        # and saves it under the size original variable
        size = len(data)
        size_o = size

        # iterates continuously to try to process all that
        # data that has been sent for processing
        while size > 0:
            # retrieves the parsing method for the current
            # state and then runs it retrieving the number
            # of valid parsed bytes in case this value is
            # zero the parsing iteration is broken
            method = self._parse_line
            count = method(data)
            if count == 0: break

            # decrements the size of the data buffer by the
            # size of the parsed bytes and then retrieves the
            # sub part of the data buffer as the new data buffer
            size -= count
            data = data[count:]

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

        # splits the provided line into the code and message parts in case
        # the split is not successful (not enough information) then an extra
        # value is added to the sequence of values for compatibility
        values = self.line_s.split(" ", 1)
        if not len(values) > 1: values.append("")

        # unpacks the set of values that have just been parsed into the code
        # and the message items as expected by the smtp specification
        code, message = values

        # triggers the on line event so that the listeners are notified
        # about the end of the parsing of the smtp line and then
        # returns the count of the parsed bytes of the message
        self.trigger("on_line", code, message)
        return index + 1
