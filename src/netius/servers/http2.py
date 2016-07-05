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

import netius.common

from . import http

class HTTP2Connection(http.HTTPConnection):

    def __init__(self, *args, **kwargs):
        http.HTTPConnection.__init__(self, *args, **kwargs)
        self.preface = False #@todo this must be done via states and not like this (just like SMTP)

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.HTTP2Parser(self)
        self.parser.bind("on_frame", self.on_frame)
        self.parser.bind("on_settings", self.on_settings)

    def parse(self, data):
        if not self.preface:
            self.owner.on_preface_http2(self, self.parser)
            self.preface = True
            return
        return self.parser.parse(data)

    def send_frame(self, type = 0x01, flags = 0x00, stream = 0x00, payload = b""):
        size = len(payload)
        header = struct.pack("!BHBBI", 0x00, size, type, flags, stream)
        message = header + payload
        self.send(message)

    def on_frame(self):
        self.owner.on_frame_http2(self, self.parser)

    def on_settings(self, settings):
        self.owner.on_settings_http2(self, self.parser, settings)

class HTTP2Server(http.HTTPServer):

    def get_protocols(self):
        return ["h2", "http/1.1", "http/1.0"]

    def new_connection(self, socket, address, ssl = False):
        return HTTP2Connection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            encoding = self.encoding
        )

    def on_preface_http2(self, connection, parser):
        connection.send_frame(type = netius.common.SETTINGS)

    def on_frame_http2(self, connection, parser):
        is_debug = self.is_debug()
        is_debug and self._log_frame(connection, parser)

    def on_settings_http2(self, connection, parser, settings):
        print(settings)

    def _log_frame(self, connection, parser):
        self.debug("Received frame 0x%02x with length %d" % (parser.type, parser.length))
