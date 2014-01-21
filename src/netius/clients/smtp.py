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

HELLO_STATE = 1

FROM_STATE = 2

TO_STATE = 3

DATA_STATE = 4

CONTENTS_STATE = 5

class SMTPConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.froms = None
        self.tos = None
        self.contents = None
        self.to_index = 0
        self.state = HELLO_STATE

        self.parser.bind("on_line", self.on_line)

    def set_smtp(self, froms, tos, contents):
        self.froms = froms
        self.tos = tos
        self.contents = contents

    def parse(self, data):
        return self.parser.parse(data)

    def send_smtp(self, code, message, delay = False, callback = None):
        data = "%s %s\r\n" % (code, message)
        print data
        self.send(data, delay = delay, callback = callback)

    def on_line(self, code, message):

        print "%s - %s" % (code, message)

        #@TODO: this state thing must be optimized !!!
        # into a list of state and methods
        if self.state == HELLO_STATE:
            self.helo("relay.example.org")
        elif self.state == FROM_STATE:
            self.mail(self.froms[0])
        elif self.state == TO_STATE:
            is_final = self.to_index == len(self.tos) - 1
            self.rcpt(self.tos[self.to_index], final = is_final)
            self.to_index += 1
        elif self.state == DATA_STATE:
            self.data()
        elif self.state == CONTENTS_STATE:
            self.send(self.contents)
            self.send("\r\n.\r\n")

    def helo(self, host):
        if not self.state == HELLO_STATE:
            raise netius.ParserError("Invalid state")
        self.state = FROM_STATE
        message = host
        self.send_smtp("HELO", message)

    def mail(self, value):
        if not self.state == FROM_STATE:
            raise netius.ParserError("Invalid state")
        self.state = TO_STATE
        message = "FROM:<%s>" % value
        self.send_smtp("MAIL", message)

    def rcpt(self, value, final = True):
        if not self.state == TO_STATE:
            raise netius.ParserError("Invalid state")
        if final: self.state = DATA_STATE
        message = "TO:<%s>" % value
        self.send_smtp("RCPT", message)

    def data(self):
        if not self.state == DATA_STATE:
            raise netius.ParserError("Invalid state")
        self.state = CONTENTS_STATE
        message = ""
        self.send_smtp("DATA", message)

class SMTPClient(netius.Client):

    def message(self, froms, tos, contents, *args, **kwargs):
        host = "gmail-smtp-in.l.google.com"
        port = 25

        # establishes the connection to the target host and port
        # and using the provided key and certificate files an then
        # sets the smtp information in the current connection
        connection = self.connect(host, port)
        connection.set_smtp(froms, tos, contents)
        return connection

    def on_connect(self, connection):
        netius.Client.on_connect(self, connection)

    def on_data(self, connection, data):
        netius.Client.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.Client.on_connection_d(self, connection)
        if self.connections: return
        self.close()

    def new_connection(self, socket, address, ssl = False):
        return SMTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

if __name__ == "__main__":
    import email.mime.text

    mime = email.mime.text.MIMEText("Hello World")
    mime["Subject"] = "The contents of a message"
    mime["From"] = "joamag@localhost.com"
    mime["To"] = "joamag@gmail.com.com"
    contents = mime.as_string()

    smtp_client = SMTPClient()
    smtp_client.message(["joamag@localhost.com"], ["joamag@gmail.com"], contents)
