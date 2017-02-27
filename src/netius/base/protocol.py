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

class Protocol(observer.Observable):

    def __init__(self):
        self._transport = None

    def connection_made(self, transport):
        self._transport = transport

    def connection_lost(self, exception):
        self._transport = None

    def pause_writing(self):
        pass

    def resume_writing(self):
        pass

class DatagramProtocol(Protocol):

    def on_data(self, data, address):
        pass

    def on_eof(self, address):
        pass

    def send(self, data, address):
        return self.send_to(data, address)

    def send_to(self, data, address):
        return self._transport.sendto(data, address)

class StreamProtocol(Protocol):

    def on_data(self, data):
        pass

    def on_eof(self):
        pass

    def send(self, data):
        return self._transport.send(data)
