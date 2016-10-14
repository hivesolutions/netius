#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import base64
import datetime

import email.parser

import netius.common

from . import dns

HELO_STATE = 1

EHLO_STATE = 2

CAPA_STATE = 3

STLS_STATE = 4

UPGRADE_STATE = 5

AUTH_STATE = 6

USERNAME_STATE = 7

PASSWORD_STATE = 8

FROM_STATE = 9

TO_STATE = 10

DATA_STATE = 11

CONTENTS_STATE = 12

QUIT_STATE = 13

FINAL_STATE = 14

AUTH_METHODS = (
    "plain",
    "login"
)

class SMTPConnection(netius.Connection):

    def __init__(self, host = "smtp.localhost", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.host = host
        self.froms = None
        self.tos = None
        self.contents = None
        self.username = None
        self.password = None
        self.expected = None
        self.to_index = 0
        self.state = HELO_STATE
        self.next = None
        self.sindex = 0
        self.sequence = ()
        self.capabilities = ()
        self.messages = []

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.parser.bind("on_line", self.on_line)
        self.build()

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()
        self.destroy()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        netius.Connection.build(self)
        self.states = (
            self.helo_t,
            self.ehlo_t,
            self.capa_t,
            self.stls_t,
            self.upgrade_t,
            self.auth_t,
            self.username_t,
            self.password_t,
            self.mail_t,
            self.rcpt_t,
            self.data_t,
            self.contents_t,
            self.quit_t,
            self.close_t
        )
        self.state_l = len(self.states)

    def destroy(self):
        """
        Destroys the current structure for the stats meaning that
        it's restored to the original values, this method should only
        be called on situation where no more client usage is required.
        """

        netius.Connection.destroy(self)
        self.states = ()
        self.state_l = 0

    def set_smtp(self, froms, tos, contents, username = None, password = None):
        self.froms = froms
        self.tos = tos
        self.contents = contents
        self.username = username
        self.password = password

    def set_sequence(self, sequence, safe = True):
        if safe and self.sequence == sequence: return
        self.sindex = 0
        self.sequence = sequence
        self.state = sequence[0]

    def set_message_seq(self, ehlo = True):
        sequence = (
            EHLO_STATE if ehlo else HELO_STATE,
            CAPA_STATE,
            AUTH_STATE,
            USERNAME_STATE,
            PASSWORD_STATE,
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
            CAPA_STATE,
            STLS_STATE,
            UPGRADE_STATE,
            EHLO_STATE if ehlo else HELO_STATE,
            CAPA_STATE,
            AUTH_STATE,
            USERNAME_STATE,
            PASSWORD_STATE,
            FROM_STATE,
            TO_STATE,
            DATA_STATE,
            CONTENTS_STATE,
            QUIT_STATE,
            FINAL_STATE
        )
        self.set_sequence(sequence)

    def set_capabilities(self, capabilities, force = True):
        if not force and self.capabilities: return
        capabilities = [value.strip().lower() for value in capabilities]
        self.capabilities = capabilities

    def next_sequence(self):
        self.sindex += 1
        self.sindex = self.sequence.index(self.next) if self.next else self.sindex
        self.state = self.next if self.next else self.sequence[self.sindex]
        self.next = None

    def parse(self, data):
        return self.parser.parse(data)

    def send_smtp(self, code, message = "", delay = True, callback = None):
        base = "%s %s" % (code, message)
        data = base + "\r\n"
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def on_line(self, code, message, is_final = True):
        # creates the base string from the provided code value and the
        # message associated with it, then logs the values into the
        # current debug logger support (for traceability)
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # adds the message part of the line to the buffer that holds the
        # various messages "pending" for the current response, these values
        # may latter be used for the processing of the response
        self.messages.append(message)

        # in case the currently parsed line is not a final one must return
        # immediately to continue the processing of information for the
        # current response, the various message should be accumulated under
        # the message buffer to avoid any problem
        if not is_final: return

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

        # erases the message buffer as it's not longer going to be used in
        # the handling (as it is finished) nothing remaining
        del self.messages[:]

    def call(self):
        # tries to retrieve the method for the current state in iteration
        # and then calls the retrieve method with no arguments (handler method)
        method = self.states[self.state - 1]
        method()

    def skip(self):
        self.next_sequence()
        self.call()

    def helo_t(self):
        self.helo(self.host)
        self.next_sequence()

    def ehlo_t(self):
        self.ehlo(self.host)
        self.next_sequence()

    def capa_t(self):
        capabilities = self.messages[1:]
        self.set_capabilities(capabilities)
        if "starttls" in self.capabilities:
            self.set_message_stls_seq()
        self.next_sequence()
        self.call()

    def stls_t(self):
        self.starttls()
        self.next_sequence()

    def upgrade_t(self):
        def callback(connection):
            connection.upgrade(server = False)
        self.next_sequence()
        callback(self)

    def auth_t(self):
        is_valid = self.username and self.password
        if not is_valid:
            self.next = FROM_STATE
            self.skip()
            return

        method = self.best_auth()
        self.auth(self.username, self.password, method = method)
        self.next_sequence()

    def username_t(self):
        self.login_username(self.username)
        self.next_sequence()

    def password_t(self):
        self.login_password(self.password)
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

    def close_t(self):
        self.close(flush = True)

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
        method_name = "auth_%s" % method
        has_method = hasattr(self, method_name)
        if not has_method: raise netius.NotImplemented("Method not implemented")
        method = getattr(self, method_name)
        method(username, password)

    def auth_plain(self, username, password):
        auth_value = "\0%s\0%s" % (username, password)
        auth_value = netius.legacy.bytes(auth_value)
        auth_value = base64.b64encode(auth_value)
        auth_value = netius.legacy.str(auth_value)
        message = "%s %s" % ("plain", auth_value)
        self.send_smtp("auth", message)
        self.set_expected(235)
        self.next = FROM_STATE

    def auth_login(self, username, password):
        message = "login"
        self.send_smtp("auth", message)
        self.set_expected(334)

    def login_username(self, username):
        username = netius.legacy.bytes(username)
        username = base64.b64encode(username)
        username = netius.legacy.str(username)
        self.send_smtp(username)
        self.set_expected(334)

    def login_password(self, password):
        password = netius.legacy.bytes(password)
        password = base64.b64encode(password)
        password = netius.legacy.str(password)
        self.send_smtp(password)
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
            "Invalid response code expected '%d' received '%d'" %
            (expected, code_i)
        )

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

    def best_auth(self):
        methods = []
        for capability in self.capabilities:
            is_auth = capability.startswith("auth ")
            if not is_auth: continue
            parts = capability.split(" ")
            parts = [part.strip() for part in parts]
            methods.extend(parts[1:])
        usable = [method for method in methods if method in AUTH_METHODS]
        return usable[0] if usable else "plain"

class SMTPClient(netius.StreamClient):

    def __init__(
        self,
        host = None,
        auto_close = False,
        *args,
        **kwargs
    ):
        netius.StreamClient.__init__(self, *args, **kwargs)
        self.host = host if host else "[" + netius.common.host() + "]"
        self.auto_close = auto_close

    @classmethod
    def message_s(
        cls,
        froms,
        tos,
        contents,
        daemon = True,
        host = None,
        callback = None
    ):
        smtp_client = cls.get_client_s(thread = True, daemon = daemon, host = host)
        smtp_client.message(froms, tos, contents, callback = callback)

    def message(
        self,
        froms,
        tos,
        contents,
        host = None,
        port = 25,
        username = None,
        password = None,
        ehlo = True,
        stls = False,
        mark = True,
        callback = None
    ):
        # in case the mark flag is set the contents data is modified
        # and "marked" with the pre-defined header values of the client
        # this should provide some extra information on the agent
        if mark: contents = self.mark(contents)

        # creates the method that is able to generate handler for a
        # certain sequence of to based (email) addresses
        def build_handler(tos, domain = None, tos_map = None):

            def on_close(connection):
                # verifies if the current handler has been build with a
                # domain based clojure and if that's the case removes the
                # reference of it from the map of tos, then verifies if the
                # map is still valid and if that's the case returns and this
                # is not considered the last remaining smtp session for the
                # current send operation (still some open)
                if domain: del tos_map[domain]
                if tos_map: return

                # verifies if the callback method is defined and if that's
                # the case calls the callback indicating the end of the send
                # operation (note that this may represent multiple smtp sessions)
                callback and callback(self)

            def handler(response = None):
                # in case there's a valid response provided must parse it
                # to try to "recover" the final address that is going to be
                # used in the establishment of the smtp connection
                if response and response.answers:
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
                # and using the provided key and certificate files and then
                # sets the smtp information in the current connection, after
                # the connections is completed the smtp session should start
                connection = self.connect(_host, _port)
                if stls: connection.set_message_stls_seq(ehlo = ehlo)
                else: connection.set_message_seq(ehlo = ehlo)
                connection.set_smtp(
                    froms,
                    tos,
                    contents,
                    username = username,
                    password = password
                )
                connection.bind("close", on_close)
                return connection

            # returns the clojure bound handler method, ready
            # to be used under a specific context
            return handler

        # in case the host address has been provided by argument the
        # handler method is called immediately to trigger the processing
        # of the smtp connection using the current host and port
        if host:
            handler = build_handler(tos)
            connection = handler()
            return connection

        # ensures that the proper main loop is started so that the current
        # smtp client does not become orphan as no connection has been
        # established as of this moment (as expected) and the dns client
        # is going to be run as a daemon (avoids process exit)
        self.ensure_loop()

        # creates the map that is going to be used to associate each of
        # the domains with the proper to (email) addresses, this is going
        # to allow aggregated based smtp sessions (performance wise)
        tos_map = dict()
        for to in tos:
            _name, domain = to.split("@", 1)
            _tos = tos_map.get(domain, [])
            _tos.append(to)
            tos_map[domain] = _tos

        # iterates over the complete set of domain and associated
        # to addresses list for each of them to run the mx based
        # query operation and then start the smtp session
        for domain, tos in netius.legacy.iteritems(tos_map):
            # creates a new handler method bound to the to addresses
            # associated with the current domain in iteration
            handler = build_handler(tos, domain = domain, tos_map = tos_map)

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
            ssl = ssl,
            host = self.host
        )

    def mark(self, contents):
        parser = email.parser.Parser()
        message = parser.parsestr(contents)
        self.date(message)
        self.user_agent(message)
        return message.as_string()

    def date(self, message):
        date = message.get("Date", None)
        if date: return
        date_time = datetime.datetime.utcnow()
        message["Date"] = date_time.strftime("%a, %d %b %Y %H:%M:%S +0000")

    def user_agent(self, message):
        user_agent = message.get("User-Agent", None)
        if user_agent: return
        message["User-Agent"] = netius.IDENTIFIER

if __name__ == "__main__":
    import email.mime.text

    sender = "hello@bemisc.com"
    receiver = "hello@bemisc.com"

    mime = email.mime.text.MIMEText("Hello World")
    mime["Subject"] = "Hello World"
    mime["From"] = sender
    mime["To"] = receiver
    contents = mime.as_string()

    client = SMTPClient(auto_close = True)
    client.message([sender], [receiver], contents)
