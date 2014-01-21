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

QUIT_STATE = 6

FINAL_STATE = 7

class SMTPConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.froms = None
        self.tos = None
        self.contents = None
        self.expected = None
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
        base = "%s %s" % (code, message)
        data = base + "\r\n"
        self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)

    def on_line(self, code, message):
        # creates the base string from the provided code value and the
        # message associated with it, then logs the values into the
        # current debug logger support (for traceability)
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # verifies if the provided code contains the separator character
        # this should mean that this is a multiple line based response
        # and for those situations no processing occurs immediately waiting
        # instead for the last line (not dashed) to run the processing
        is_multiple = "-" in code
        if is_multiple: return

        # runs the code based assertion so that if there's an expected
        # value set for the current connection it's correctly validated
        self.assert_c(code)

        #@TODO: this state thing must be optimized !!!
        #into a list of state and methods

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
            self.contents_t()
        elif self.state == QUIT_STATE:
            self.quit()

    def contents_t(self):
        self.state = QUIT_STATE
        self.send(self.contents)
        self.send("\r\n.\r\n")
        self.set_expected(250)

    def helo(self, host):
        self.assert_s(HELLO_STATE)
        self.state = FROM_STATE
        message = host
        self.send_smtp("helo", message)
        self.set_expected(250)

    def mail(self, value):
        self.assert_s(FROM_STATE)
        self.state = TO_STATE
        message = "FROM:<%s>" % value
        self.send_smtp("mail", message)
        self.set_expected(250)

    def rcpt(self, value, final = True):
        self.assert_s(TO_STATE)
        if final: self.state = DATA_STATE
        message = "TO:<%s>" % value
        self.send_smtp("rcpt", message)
        self.set_expected(250)

    def data(self):
        self.assert_s(DATA_STATE)
        self.state = CONTENTS_STATE
        message = ""
        self.send_smtp("data", message)
        self.set_expected(354)

    def quit(self):
        self.assert_s(QUIT_STATE)
        self.state = FINAL_STATE
        message = ""
        self.send_smtp("quit", message)
        self.set_expected(221)

    def set_expected(self, expected):
        self.expected = expected

    def assert_c(self, code):
        if not self.expected: return
        expected = self.expected
        code_i = int(code)
        self.expected = None
        valid = expected == code_i
        if valid: return
        raise netius.ParserError(
            "Invalid code expected '%d' got '%d'" %\
            (expected, code_i)
        )

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

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

    sender = "joamag@bemisc.com"
    receiver = "joamag@gmail.com"

    mime = email.mime.text.MIMEText("Hello World")
    mime["Subject"] = "The contents of a message"
    mime["From"] = sender
    mime["To"] = receiver
    contents = mime.as_string()

    smtp_client = SMTPClient()
    smtp_client.message([sender], [receiver], contents)
