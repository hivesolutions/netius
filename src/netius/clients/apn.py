#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import json
import struct
import binascii

import netius

class APNProtocol(netius.StreamProtocol):
    """
    Protocol class that defines the interface to operate
    an apple push notifications (APN) protocol that is
    able to send push notifications to Apple devices.

    Should be compliant with a simple message oriented
    interface for easy of usage from developers.
    """

    HOST = "gateway.push.apple.com"
    """ The host of the APN service to be used when
    in production mode """

    PORT = 2195
    """ The port of the APN service to be used when
    in sandbox mode """

    SANDBOX_HOST = "gateway.sandbox.push.apple.com"
    """ The host of the APN service to be used when
    in sandbox mode (for testing purposes) """

    SANDBOX_PORT = 2195
    """ The port of the APN service to be used when
    in sandbox mode (for testing purposes) """

    def __init__(self, *args, **kwargs):
        netius.StreamProtocol.__init__(self, *args, **kwargs)
        self.host = None
        self.port = None
        self.token = None
        self.message = None
        self.sound = None
        self.badge = 0
        self.sandbox = True
        self._close = True

    def connection_made(self, transport):
        netius.StreamProtocol.connection_made(self, transport)

        self.send_notification(
            self.token,
            self.message,
            sound = self.sound,
            badge = self.badge,
            close = self._close
        )

    def send_notification(
        self,
        token,
        message,
        sound = "default",
        badge = 0,
        close = False
    ):
        # creates the callback handler that closes the current
        # client infra-structure after sending, this will close
        # the connection using a graceful approach to avoid any
        # of the typical problems with the connection shutdown
        def callback(transport): self.close()

        # converts the current token (in hexadecimal) to a set
        # of binary string elements and uses that value to get
        # a string of data from the string of hexadecimal data
        token = netius.legacy.bytes(token)
        token = binascii.unhexlify(token)

        # creates the message structure using with the
        # message (string) as the alert and then converts
        # it into a JSON format (payload)
        message_s = dict(
           aps = dict(
                alert = message,
                sound = sound,
                badge = badge
            )
        )
        payload = json.dumps(message_s)

        # verifies if the resulting payload object is unicode based
        # and in case it is encodes it into a string representation
        # so that it may be used for the packing of structure
        is_unicode = netius.legacy.is_unicode(payload)
        if is_unicode: payload = payload.encode("utf-8")

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
        self.send(message, callback = callback)

    def set(
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

    def notify(self, token, loop = None, **kwargs):
        # retrieves the intance's parent class object to be
        # used to global class operations
        cls = self.__class__

        # unpacks the various keyword based arguments for the
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
        self.host = cls.SANDBOX_HOST if sandbox else cls.HOST
        self.port = cls.SANDBOX_PORT if sandbox else cls.PORT

        # sets the APN specific information in the current
        # protocol instance to be used once connected
        self.set(
            token,
            message,
            sound = sound,
            badge = badge,
            sandbox = sandbox,
            key_file = key_file,
            cer_file = cer_file,
            _close = _close
        )

        # establishes the connection to the target host and port
        # and using the provided key and certificate files
        loop = netius.connect_stream(
            lambda: self,
            host = self.host,
            port = self.port,
            ssl = True,
            key_file = key_file,
            cer_file = cer_file,
            loop = loop
        )

        # returns both the current associated loop and the current
        # instance to the protocol defined by the current instance
        return loop, self

class APNClient(netius.ClientAgent):

    protocol = APNProtocol

    @classmethod
    def notify_s(cls, token, loop = None, **kwargs):
        protocol = cls.protocol()
        return protocol.notify(token, loop = loop, **kwargs)

if __name__ == "__main__":
    def on_finish(protocol):
        netius.compat_loop(loop).stop()

    token = netius.conf("APN_TOKEN", None)
    key_file = netius.conf("APN_KEY_FILE", None)
    cer_file = netius.conf("APN_CER_FILE", None)

    loop, protocol = APNClient.notify_s(
        token, key_file = key_file, cer_file = cer_file
    )

    protocol.bind("finish", on_finish)

    loop.run_forever()
    loop.close()
else:
    __path__ = []
