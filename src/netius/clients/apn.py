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

HOST = "gateway.push.apple.com"
""" The host of the apn service to be used when
in production mode """

PORT = 2195
""" The port of the apn service to be used when
in sandbox mode """

SANDBOX_HOST = "gateway.sandbox.push.apple.com"
""" The host of the apn service to be used when
in sandbox mode """

SANDBOX_PORT = 2195
""" The port of the apn service to be used when
in sandbox mode """

TOKEN = "asdads"

class APNConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.token = None
        self.message = None
        self.sound = None
        self.badge = 0
        self.sandbox = True
        self.wait = False

    def set_apn(
        self,
        token,
        message,
        sound = "default",
        badge = 0,
        sandbox = True,
        wait = False
    ):
        self.token = token
        self.message = message
        self.sound = sound
        self.badge = badge
        self.sandbox = sandbox
        self.wait = wait

    def parse(self, data):
        return self.parser.parse(data)

    def on_data(self):
        self.owner.on_data_http(self.parser)

class APNClient(netius.Client):

    def send_message(self, token = TOKEN, *args, **kwargs):
        message = kwargs.get("message", "Hello World")
        sound = kwargs.get("sound", "default")
        badge = kwargs.get("badge", 0)
        sandbox = kwargs.get("sandbox", True)
        wait = kwargs.get("wait", False)

        # retrieves the values that are going to be used for
        # both the host and the port, taking into account if
        # the current message is meant to be send using the
        # sandbox environment (for testing purposes)
        host = SANDBOX_HOST if sandbox else HOST
        port = SANDBOX_PORT if sandbox else PORT


        #### VER ISTO MUITO IMPORTANTE key_file = None, cer_file = None

        ### tenho de ver bem o house keeping depois do fecho do loop
        # tenho de fechar todas as conexoes !!!!


        connection = self.connect(host, port, ssl = True)
        connection.set_apn(
            token,
            message,
            sound = sound,
            badge = badge,
            sandbox = sandbox,
            wait = wait
        )

    def on_connect(self, connection):
        netius.Client.on_connect(self, connection)

        method = connection.method
        path = connection.path
        version = connection.version

        connection.send("%s %s %s\r\n\r\n" % (method, path, version))

    def new_connection(self, socket, address, ssl = False):
        return APNConnection(self, socket, address, ssl = ssl)
