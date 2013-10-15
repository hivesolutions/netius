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

import netius.common

SERVER_NAME = "netius"
""" The name of the server to be used in all of the
identification string about it """

SERVER_VERSION = "0.0.1"
""" The version string to be used for the identification
of the current release of the server """

BASE_HEADERS = dict(
    Server = "%s/%s" % (SERVER_NAME, SERVER_VERSION)
)
""" The map containing the complete set of headers
that are meant to be applied to all the responses """

class HTTPConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.HTTPParser(type = netius.common.REQUEST)

        self.parser.bind("on_data", self.on_data)

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self, self.parser)

class HTTPServer(netius.Server):
    """
    Base class for serving of the http protocol, should contain
    the basic utilities for handling an http request including
    headers and read of data.
    """

    def on_connection_c(self, connection):
        netius.Server.on_connection_c(self, connection)

    def on_data(self, connection, data):
        netius.Server.on_data(self, connection, data)
        connection.parse(data)

    def new_connection(self, socket, address, ssl = False):
        return HTTPConnection(self, socket, address, ssl = ssl)

    def on_data_http(self, connection, parser):
        pass

    def _apply_base(self, headers):
        for key, value in BASE_HEADERS.items():
            if key in headers: continue
            headers[key] = value

    def _apply_parser(self, parser, headers):
        if parser.keep_alive: headers["Connection"] = "keep-alive"
        else: headers["Connection"] = "close"
