#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

from . import observer

class Transport(observer.Observable):
    """
    Decorator class to be used to add the functionality of a
    transport layer using a simplified and standard api.

    Allows adding the functionality to an internal netius
    connection (or equivalent) object.
    """

    def __init__(self, connection):
        self._connection = connection
        self._protocol = None

    def close(self):
        self._connection.close()

    def abort(self):
        self._connection.close()

    def write(self, data):
        self._connection.send(data)

    def sendto(self, data, addr = None):
        self._connection.send(data, address = addr)

    def get_extra_info(self, name, default = None):
        if name == "socket": return self._connection.socket
        else: return default

    def set_protocol(self, protocol):
        self._set_protocol(protocol, mark = False)

    def get_protocol(self):
        return self._protocol

    def is_closing(self):
        return self._connection.is_closed()

    def _on_data(self, connection, data):
        pass

    def _on_close(self, connection):
        pass

    def _set_compat(self, protocol):
        self._set_binds()
        self._set_protocol(protocol)

    def _set_binds(self):
        self._connection.bind("data", self._on_data)
        self._connection.bind("close", self._on_close)

    def _set_protocol(self, protocol, mark = True):
        self._protocol = protocol
        if mark: self._protocol.connection_made(self)

class TransportDatagram(Transport):

    def _on_data(self, connection, data):
        data, address = data
        self._protocol.datagram_received(data, address)

    def _on_close(self, connection):
        pass

class TransportStream(Transport):

    def _on_data(self, connection, data):
        self._protocol.data_received(data)

    def _on_close(self, connection):
        self._protocol.eof_received()
        self._protocol.connection_lost(None)
