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

import json
import struct
import binascii

import netius

HOST = "gateway.push.apple.com"
""" The host of the apn service to be used when
in production mode """

PORT = 2195
""" The port of the apn service to be used when
in sandbox mode """

SANDBOX_HOST = "gateway.sandbox.push.apple.com"
""" The host of the apn service to be used when
in sandbox mode (for testing purposes) """

SANDBOX_PORT = 2195
""" The port of the apn service to be used when
in sandbox mode (for testing purposes) """

class APNConnection(netius.Connection):

    def __init__(self, owner, socket, address, ssl = False):
        netius.Connection.__init__(self, owner, socket, address, ssl = ssl)
        self.token = None
        self.message = None
        self.sound = None
        self.badge = 0
        self.sandbox = True
        self._close = True

    def set_apn(
        self,
        token,
        message,
        sound = "default",
        badge = 0,
        sandbox = True,
        key_file = None,
        cer_file = None,
        _close = True
    ):
        self.token = token
        self.message = message
        self.sound = sound
        self.badge = badge
        self.sandbox = sandbox
        self.key_file = key_file
        self.cer_file = cer_file
        self._close = _close

class APNClient(netius.Client):

    def message(self, token, *args, **kwargs):
        # unpacks the various keyword based arguments fro the
        # provided map of arguments defaulting to a series of
        # pre-defined values in case the arguments have not
        # been correctly provided
        message = kwargs.get("message", "Hello World")
        sound = kwargs.get("sound", "default")
        badge = kwargs.get("badge", 0)
        sandbox = kwargs.get("sandbox", True)
        key_file = kwargs.get("key_file", None)
        cer_file = kwargs.get("cer_file", None)
        _close = kwargs.get("close", True)

        # retrieves the values that are going to be used for
        # both the host and the port, taking into account if
        # the current message is meant to be send using the
        # sandbox environment (for testing purposes)
        host = SANDBOX_HOST if sandbox else HOST
        port = SANDBOX_PORT if sandbox else PORT

        # establishes the connection to the target host and port
        # and using the provided key and certificate files an then
        # sets the apn information in the current connection
        connection = self.connect(
            host,
            port,
            ssl = True,
            key_file = key_file,
            cer_file = cer_file
        )
        connection.set_apn(
            token,
            message,
            sound = sound,
            badge = badge,
            sandbox = sandbox,
            key_file = key_file,
            cer_file = cer_file,
            _close = _close
        )

    def on_connect(self, connection):
        netius.Client.on_connect(self, connection)

        # creates the callback handler that closes the current
        # client infra-structure after sending
        def callback(connection): self.close()

        # unpacks the various elements that are going to be
        # used in the sending of the message
        token = connection.token
        message = connection.message
        sound = connection.sound
        badge = connection.badge
        close = connection._close

        # converts the current token (in hexadecimal) to a
        # string of binary data for the message
        token = binascii.unhexlify(token)

        # creates the message structure using with the
        # message (string) as the alert and then converts
        # it into a json format (payload)
        message_s = {
           "aps" : {
                "alert" : message,
                "sound" : sound,
                "badge" : badge
            }
        }
        payload = json.dumps(message_s)

        # sets the command with the zero value (simplified)
        # then calculates the token and payload lengths
        command = 0
        token_length = len(token)
        payload_length = len(payload)

        # creates the initial template for message creation by
        # using the token and the payload length for it, then
        # applies the various components of the message and packs
        # them according to the generated template
        template = "!BH%dsH%ds" % (token_length, payload_length)
        message = struct.pack(template, command, token_length, token, payload_length, payload)
        callback = callback if close else None
        connection.send(message, callback = callback)

    def new_connection(self, socket, address, ssl = False):
        return APNConnection(self, socket, address, ssl = ssl)
