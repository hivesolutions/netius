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

import base64

import netius.common

import dns

HELO_STATE = 1

EHLO_STATE = 2

STLS_STATE = 3

UPGRADE_STATE = 4

AUTH_STATE = 5

FROM_STATE = 6

TO_STATE = 7

DATA_STATE = 8

CONTENTS_STATE = 9

QUIT_STATE = 10

FINAL_STATE = 11

class SMTPConnection(netius.Connection):

    def __init__(self, *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.froms = None
        self.tos = None
        self.contents = None
        self.username = None
        self.password = None
        self.expected = None
        self.to_index = 0
        self.state = HELO_STATE
        self.sindex = 0
        self.sequence = ()

        self.parser.bind("on_line", self.on_line)

        self.build()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        self.states = (
            self.helo_t,
            self.ehlo_t,
            self.stls_t,
            self.upgrade_t,
            self.auth_t,
            self.mail_t,
            self.rcpt_t,
            self.data_t,
            self.contents_t,
            self.quit_t,
            self.pass_t
        )
        self.state_l = len(self.states)

    def set_sequence(self, sequence):
        self.sindex = 0
        self.sequence = sequence
        self.state = sequence[0]

    def set_message_seq(self, ehlo = True):
        sequence = (
            EHLO_STATE if ehlo else HELO_STATE,
            AUTH_STATE,
            FROM_STATE,
            TO_STATE,
            DATA_STATE,
            CONTENTS_STATE,
            QUIT_STATE,
            FINAL_STATE
        )
        self.set_sequence(sequence)

    def set_message_stls_seq(self, ehlo = True):
        sequence = (
            EHLO_STATE if ehlo else HELO_STATE,
            STLS_STATE,
            UPGRADE_STATE,
            EHLO_STATE if ehlo else HELO_STATE,
            AUTH_STATE,
            FROM_STATE,
            TO_STATE,
            DATA_STATE,
            CONTENTS_STATE,
            QUIT_STATE,
            FINAL_STATE
        )
        self.set_sequence(sequence)

    def next_sequence(self):
        self.sindex += 1
        self.state = self.sequence[self.sindex]

    def set_smtp(self, froms, tos, contents, username = None, password = None):
        self.froms = froms
        self.tos = tos
        self.contents = contents
        self.username = username
        self.password = password

    def parse(self, data):
        return self.parser.parse(data)

    def send_smtp(self, code, message = "", delay = False, callback = None):
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

        # verifies that the current state valid represents a valid state
        # according to the ones that have "generate" handling methods, otherwise
        # raises a parser error indicating the problem
        if self.state > self.state_l:
            raise netius.ParserError("Invalid state")

        # runs the calling of the next state based method according to the
        # currently defined state, this is the increments in calling
        self.call()

    def call(self):
        # tries to retrieve the method for the current state in iteration
        # and then calls the retrieve method with no arguments (handler method)
        method = self.states[self.state - 1]
        method()

    def skip(self):
        self.next_sequence()
        self.call()

    def helo_t(self):
        self.helo("relay.example.org")
        self.next_sequence()

    def ehlo_t(self):
        self.ehlo("relay.example.org")
        self.next_sequence()

    def stls_t(self):
        self.starttls()
        self.next_sequence()

    def upgrade_t(self):
        self.upgrade(server = False)
        self.next_sequence()

    def auth_t(self):
        is_valid = self.username and self.password
        if not is_valid: self.skip(); return

        self.auth(self.username, self.password)
        self.next_sequence()

    def mail_t(self):
        self.mail(self.froms[0])
        self.next_sequence()

    def rcpt_t(self):
        is_final = self.to_index == len(self.tos) - 1
        self.rcpt(self.tos[self.to_index])
        self.to_index += 1
        if is_final: self.next_sequence()

    def data_t(self):
        self.data()
        self.next_sequence()

    def contents_t(self):
        self.assert_s(CONTENTS_STATE)
        self.send(self.contents)
        self.send("\r\n.\r\n")
        self.set_expected(250)
        self.next_sequence()

    def quit_t(self):
        self.quit()
        self.next_sequence()

    def pass_t(self):
        pass

    def helo(self, host):
        self.assert_s(HELO_STATE)
        message = host
        self.send_smtp("helo", message)
        self.set_expected(250)

    def ehlo(self, host):
        self.assert_s(EHLO_STATE)
        message = host
        self.send_smtp("ehlo", message)
        self.set_expected(250)

    def starttls(self):
        self.assert_s(STLS_STATE)
        self.send_smtp("starttls")
        self.set_expected(220)

    def auth(self, username, password, method = "plain"):
        self.assert_s(AUTH_STATE)
        auth_value = "\0%s\0%s" % (username, password)
        auth_value = base64.b64encode(auth_value)
        message = "%s %s" % (method, auth_value)
        self.send_smtp("auth", message)
        self.set_expected(235)

    def mail(self, value):
        self.assert_s(FROM_STATE)
        message = "FROM:<%s>" % value
        self.send_smtp("mail", message)
        self.set_expected(250)

    def rcpt(self, value):
        self.assert_s(TO_STATE)
        message = "TO:<%s>" % value
        self.send_smtp("rcpt", message)
        self.set_expected(250)

    def data(self):
        self.assert_s(DATA_STATE)
        self.send_smtp("data")
        self.set_expected(354)

    def quit(self):
        self.assert_s(QUIT_STATE)
        self.send_smtp("quit")
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
            "Invalid response code expected '%d' received '%d'" %\
            (expected, code_i)
        )

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

class SMTPClient(netius.StreamClient):

    def __init__(self, auto_close = False, *args, **kwargs):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.auto_close = auto_close

    @classmethod
    def message_s(cls, froms, tos, contents, daemon = True):
        smtp_client = cls.get_client_s(thread = True, daemon = daemon)
        smtp_client.message(froms, tos, contents)

    def message(
        self,
        froms,
        tos,
        contents,
        host = None,
        port = 25,
        username = None,
        password = None,
        stls = False
    ):

        def handler(response = None):
            # in case there's a valid response provided must parse it
            # to try to "recover" the final address that is going to be
            # used in the establishment of the smtp connection
            if response:
                # retrieves the first answer (probably the most accurate)
                # and then unpacks it until the mx address is retrieved
                first = response.answers[0]
                extra = first[4]
                address = extra[1]

            # otherwise the host should have been provided and as such the
            # address value is set with the provided host
            else: address = host

            # sets the proper address (host) and port values that are
            # going to be used to establish the connection, notice that
            # in case the values provided as parameter to the message
            # method are valid they are used instead of the "resolved"
            _host = host or address
            _port = port or 25

            # establishes the connection to the target host and port
            # and using the provided key and certificate files an then
            # sets the smtp information in the current connection
            connection = self.connect(_host, _port)
            if stls: connection.set_message_stls_seq()
            else: connection.set_message_seq()
            connection.set_smtp(
                froms,
                tos,
                contents,
                username = username,
                password = password
            )
            return connection

        # in case the host address has been provided by argument the
        # handler method is called immediately to trigger the processing
        # of the smtp connection using the current host and port
        if host: handler(); return

        # retrieves the first target of the complete list of
        # to targets and then splits the email value so that
        # both the base name and the host are retrieved
        first = tos[0]
        _name, domain = first.split("@", 1)

        # runs the dns query to be able to retrieve the proper
        # mail exchange host for the target email address and then
        # sets the proper callback for sending
        dns.DNSClient.query_s(domain, type = "mx", callback = handler)

    def on_connect(self, connection):
        netius.StreamClient.on_connect(self, connection)

    def on_upgrade(self, connection):
        netius.StreamClient.on_upgrade(self, connection)
        connection.call()

    def on_data(self, connection, data):
        netius.StreamClient.on_data(self, connection, data)
        connection.parse(data)

    def on_connection_d(self, connection):
        netius.StreamClient.on_connection_d(self, connection)
        if not self.auto_close: return
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
    mime["Subject"] = "Hello World"
    mime["From"] = sender
    mime["To"] = receiver
    contents = mime.as_string()

    smtp_client = SMTPClient(auto_close = True)
    smtp_client.message([sender], [receiver], contents)
