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
import netius.clients

class DHCPConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.parser = netius.common.DHCPParser(self)

class DHCPServer(netius.DatagramServer):

    def __init__(self, rules = {}, name = None, handler = None, *args, **kwargs):
        netius.DatagramServer.__init__(
            self,
            name = name,
            handler = handler,
            *args,
            **kwargs
        )
        self.rules = rules

    def serve(self, port = 67, type = netius.UDP_TYPE, *args, **kwargs):
        netius.DatagramServer.serve(self, port = port, type = type, *args, **kwargs)

    def on_data(self, address, data):
        netius.DatagramServer.on_data(self, address, data)

        print address

    def on_connection_d(self, connection):
        netius.DatagramServer.on_connection_d(self, connection)

        if hasattr(connection, "tunnel_c"): connection.tunnel_c.close()

    def new_connection(self, socket, address, ssl = False):
        return DHCPConnection(self, socket, address, ssl = ssl)

if __name__ == "__main__":
    import logging
    server = DHCPServer(level = logging.INFO)
    server.serve(host = "0.0.0.0", port = 67)
