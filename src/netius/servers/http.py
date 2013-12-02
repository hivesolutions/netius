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

import time
import zlib
import struct

import netius.common

BASE_HEADERS = {
    "Server" : "%s/%s" % (netius.NAME, netius.VERSION)
}
""" The map containing the complete set of headers
that are meant to be applied to all the responses """

class HTTPConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.HTTPParser(
            self,
            type = netius.common.REQUEST,
            store = True
        )
        self.gzip = None
        self.crc32 = 0
        self.size = 0

        self.parser.bind("on_data", self.on_data)

    def flush(self, callback = None):
        if self.gzip: self._flush_gzip(callback = callback)
        else: self._flush_gzip(callback = callback)

    def send_gzip(self, data, callback = None, level = 6):
        # "calculates" if the current sending of gzip data is
        # the first one by verifying if the gzip object is set
        is_first = self.gzip == None

        # in case this is the first sending a new compress object
        # is created with the requested compress level
        if is_first: self.gzip = zlib.compressobj(level)

        # re-computes the crc 32 value from the provided data
        # string and the previous crc 32 value in case it does
        # exists (otherwise starts from zero)
        self.crc32 = self.crc32 = zlib.crc32(data, self.crc32)

        # increments the size value for the current data that
        # is going to be sent by the length of the data string
        self.size += len(data)

        # compresses the provided data string and removes the
        # initial data contents of the compressed data because
        # they are not part of the gzip specification
        data_c = self.gzip.compress(data)
        data_c = data_c[2:]

        # in case this is the first send operation, need to
        # create and send the header of the gzip contents and
        # then send them through the current connection
        if is_first:
            header = self._header_gzip()
            self.send(header)

        # sends the compressed data to the client endpoint setting
        # the correct callback values as requested
        self.send(data_c, callback = callback)

    def send_response(
        self,
        data = None,
        headers = None,
        version = "HTTP/1.1",
        code = 200,
        code_s = None,
        callback = None
    ):
        headers = headers or {}
        data_l = len(data) if data else 0

        if not "content-length" in headers:
            headers["content-length"] = data_l

        buffer = []
        buffer.append("%s %d %s\r\n" % (version, code, code_s))
        for key, value in headers.iteritems():
            key = netius.common.header_up(key)
            buffer.append("%s: %s\r\n" % (key, value))
        buffer.append("\r\n")
        buffer_data = "".join(buffer)

        self.send(buffer_data)
        data and self.send(data, callback = callback)

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self, self.parser)

    def _flush_base(self, callback = None):
        if not self.callback: return
        self.send("", callback = callback)

    def _flush_gzip(self, callback = None):
        data_c = self.gzip.flush(zlib.Z_FINISH)
        data_c = data_c[:-4]
        self.send(data_c)

        tail = self._tail_gzip()
        self.send(tail, callback = callback)

        self.gzip = None
        self.crc32 = 0
        self.size = 0

    def _header_gzip(self):
        # creates the buffer list that is going to be used in
        # the storage of the various header parts
        header = []

        # writes the magic header and the compression method
        # that is going to be used for the gzip compression
        header.append("\x1f\x8b")
        header.append("\x08")

        # writes the flag values, for this situation there's
        # no file name to be added and so unset flag values
        # are going o be sent (nothing to be declared)
        header.append("\x00")

        # retrieves the current timestamp and then packs it into
        # a long based value and adds it to the current header
        timestamp = long(time.time())
        timestamp = struct.pack("<L", timestamp)
        header.append(timestamp)

        # writes some extra heading values, includes information
        # about the operative system, etc.
        header.append("\x02")
        header.append("\xff")

        # joins the current header value into a single string and
        # then returns it to the caller method to be sent
        return "".join(header)

    def _tail_gzip(self):
        # creates the list that is going to be used as the buffer
        # for the construction of the gzip tail value
        tail = []

        # converts the current crc 32 value into an unsigned value
        # and then packs it as a little endian based long value
        # and then adds it to the tail buffer
        crc32 = self._unsigned(self.crc32)
        crc32 = struct.pack("<L", crc32)
        tail.append(crc32)

        # converts the current response size into an unsigned value
        # and then packs it into a little endian value and adds it
        # to the tail buffer to be part of the tail value
        size = self._unsigned(self.size)
        size = struct.pack("<L", size)
        tail.append(size)

        # joins the tail buffer into a single string and returns it
        # to the caller method as the tail value
        return "".join(tail)

    def _unsigned(self, number):
        """
        Converts the given number to unsigned assuming
        a 32 bit value required for some of the gzip
        based operations.

        @type number: int
        @param number: The number to be converted to unsigned.
        @rtype: int
        @return: The given number converted to unsigned.
        """

        # in case the number is positive or zero
        # (no need to convert) returns the provided
        # number immediately to the caller method
        if number >= 0: return number

        # runs the modulus in the number
        # to convert it to unsigned
        return number + 4294967296

class HTTPServer(netius.StreamServer):
    """
    Base class for serving of the http protocol, should contain
    the basic utilities for handling an http request including
    headers and read of data.
    """

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(self, socket, address, ssl = ssl)

    def on_data_http(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_request(connection, parser)

    def _apply_base(self, headers):
        for key, value in BASE_HEADERS.iteritems():
            if key in headers: continue
            headers[key] = value

    def _apply_parser(self, parser, headers):
        if parser.keep_alive: headers["Connection"] = "keep-alive"
        else: headers["Connection"] = "close"

    def _log_request(self, connection, parser):
        # unpacks the various values that are going to be part of
        # the log message to be printed in the debug
        ip_address = connection.address[0]
        method = parser.method.upper()
        path = parser.get_path()
        version_s = parser.version_s

        # creates the message from the complete set of components
        # that are part of the current message and then prints a
        # debug message with the contents of it
        message = "%s %s %s @ %s" % (method, path, version_s, ip_address)
        self.debug(message)
