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

import time
import base64
import datetime

import netius.common

INTIAL_STATE = 1
""" The initial state for the smtp communication
meaning that no message have been exchanged between
the server and the client parties """

HELO_STATE = 2
""" State where the initial negotiation/identification
processes takes place, it's under this stage that the
start tls may take place to upgrade the connection """

HEADER_STATE = 3
""" Secondary state where the header information for
the message to be sent is defined """

DATA_STATE = 4
""" Final stage of the smtp session where the message
contents are sent over the connection """

USERNAME_STATE = 5
""" The username state where the server is waiting for
a base64 username string to be sent and stored, this
state is only used for the login base authentication """

PASSWORD_STATE = 6
""" The password state where the server is waiting for
a base64 password string to be sent and stored, after
this step proper authentication is possible under the
login type of authentication """

TERMINATION_SIZE = 5
""" The size of the termination sequence of the smtp message
this is going to be used in some parsing calculus, this value
should be exposed so that it may be re-used by other modules """

CAPABILITIES = (
    "AUTH PLAIN LOGIN",
    "STARTTLS"
)
""" The sequence defining the various capabilities that are
available under the current smtp server implementation, the
description of these capabilities should conform with the rfp """

class SMTPConnection(netius.Connection):

    def __init__(self, host = "smtp.localhost", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.host = host
        self.chost = None
        self.identifier = None
        self.time = time.time()
        self.keys = []
        self.from_l = []
        self.to_l = []
        self.previous = bytes()
        self.state = INTIAL_STATE

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.parser.bind("on_line", self.on_line)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()

    def parse(self, data):
        if self.state == DATA_STATE: self.on_raw_data(data)
        elif self.state == USERNAME_STATE: self.on_username(data)
        elif self.state == PASSWORD_STATE: self.on_password(data)
        else: return self.parser.parse(data)

    def send_smtp(self, code, message = "", lines = (), delay = True, callback = None):
        if lines: return self.send_smtp_lines(
            code,
            message = message,
            lines = lines,
            delay = delay,
            callback = callback
        )
        else: return self.send_smtp_base(
            code,
            message,
            delay,
            callback
        )

    def send_smtp_base(self, code, message = "", delay = True, callback = None):
        base = "%d %s" % (code, message)
        data = base + "\r\n"
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def send_smtp_lines(self, code, message = "", lines = (), delay = True, callback = None):
        lines = list(lines)
        lines.insert(0, message)
        body = lines[:-1]
        tail = lines[-1]
        base = "%d %s" % (code, message)
        lines_s = ["%d-%s" % (code, line) for line in body]
        lines_s.append("%d %s" % (code, tail))
        data = "\r\n".join(lines_s) + "\r\n"
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def ready(self):
        self.assert_s(INTIAL_STATE)
        message = "%s ESMTP %s" % (self.host, netius.NAME)
        self.send_smtp(220, message)
        self.state = HELO_STATE

    def helo(self, host):
        self.assert_s(HELO_STATE)
        self.chost = host
        message = "helo %s" % host
        self.send_smtp(250, message)
        self.state = HEADER_STATE

    def ehlo(self, host):
        self.assert_s(HELO_STATE)
        self.chost = host
        message = "ehlo %s" % host
        self.send_smtp(250, message, lines = CAPABILITIES)
        self.state = HEADER_STATE

    def starttls(self):
        def callback(connection):
            connection.upgrade(server = True)
        message = "go ahead"
        self.send_smtp(220, message, callback = callback)
        self.state = HELO_STATE

    def auth(self, method, data):
        method_name = "auth_%s" % method
        has_method = hasattr(self, method_name)
        if not has_method: raise netius.NotImplemented("Method not implemented")
        method = getattr(self, method_name)
        method(data)

    def auth_plain(self, data):
        data_s = base64.b64decode(data)
        data_s = netius.legacy.str(data_s)
        _identifier, username, password = data_s.split("\0")
        self.owner.on_auth_smtp(self, username, password)
        message = "authentication successful"
        self.send_smtp(235, message)
        self.state = HEADER_STATE

    def auth_login(self, data):
        message = "VXNlcm5hbWU6"
        self.send_smtp(334 , message)
        self.state = USERNAME_STATE

    def data(self):
        self.assert_s(HEADER_STATE)
        self.owner.on_header_smtp(self, self.from_l, self.to_l)
        message = "go ahead"
        self.send_smtp(354, message)
        self.previous = bytes()
        self.state = DATA_STATE

    def queued(self, index = -1):
        self.assert_s(DATA_STATE)
        self.owner.on_message_smtp(self)
        identifier = self.identifier or index
        message = "ok queued as %s" % identifier
        self.send_smtp(250, message)
        self.state = HEADER_STATE

    def bye(self):
        message = "bye"
        self.send_smtp(221, message)

    def ok(self):
        message = "ok"
        self.send_smtp(250, message)

    def not_implemented(self):
        message = "not implemented"
        self.send_smtp(550, message)

    def on_username(self, data):
        data_s = base64.b64decode(data)
        data_s = netius.legacy.str(data_s)
        self._username = data_s
        message = "UGFzc3dvcmQ6"
        self.send_smtp(334 , message)
        self.state = PASSWORD_STATE

    def on_password(self, data):
        data_s = base64.b64decode(data)
        data_s = netius.legacy.str(data_s)
        self._password = data_s
        self.owner.on_auth_smtp(self, self._username, self._password)
        delattr(self, "_username")
        delattr(self, "_password")
        message = "authentication successful"
        self.send_smtp(235, message)
        self.state = HEADER_STATE

    def on_raw_data(self, data):
        # calls the proper callback handler for data in the owner indicating
        # that the current data has just been received and must be properly
        # handled to the proper redirector middleware
        self.owner.on_data_smtp(self, data)

        # calculates the length of the data that has just been received and then
        # measures the size of the possible remaining bytes of the buffer from the
        # previously received ones and appends them to the buffer ten trying to
        # find the termination string in the final concatenated string
        data_l = len(data)
        remaining = TERMINATION_SIZE - data_l if TERMINATION_SIZE > data_l else 0
        previous_v = self.previous[remaining * -1:] if remaining > 0 else b""
        buffer = previous_v + data[TERMINATION_SIZE * -1:]
        is_final = not buffer.find(b"\r\n.\r\n") == -1

        # updates the previous value string with the current buffer used for finding
        # the termination string, this value may be used in the next iteration
        self.previous = buffer

        # verifies if this is the final part of the message as
        # pre-defined before the data configuration, if that's not
        # the case must return the control flow immediately
        if not is_final: return

        # runs the queued command indicating that the message has
        # been queued for sending and that the connection may now
        # be closed if there's nothing remaining to be done
        self.queued()

    def on_line(self, code, message, is_final = True):
        # "joins" the code and the message part of the message into the base
        # string and then uses this value to print some debug information
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # calls the proper top level owner based line information handler that
        # should ignore any usages as the connection will take care of the proper
        # handling for the current connection
        self.owner.on_line_smtp(self, code, message)

        # converts the provided code into a lower case value and then uses it
        # to create the problem name for the handler method to be used
        code_l = code.lower()
        method_n = "on_" + code_l

        # verifies if the method for the current code exists in case it
        # does not raises an exception indicating the problem with the
        # code that has just been received (probably erroneous)
        extists = hasattr(self, method_n)
        if not extists: raise netius.ParserError("Invalid code '%s'" % code)

        # retrieves the reference to the method that is going to be called
        # for the handling of the current line from the current instance and
        # then calls it with the provided message
        method = getattr(self, method_n)
        method(message)

    def on_helo(self, message):
        host = message
        self.hello(host)

    def on_ehlo(self, message):
        host = message
        self.ehlo(host)

    def on_starttls(self, message):
        self.starttls()

    def on_auth(self, message):
        message_s = message.split(" ", 1)
        is_tuple = len(message_s) == 2
        if is_tuple: method, data = message_s
        else: method = message; data = ""
        method = method.lower()
        self.auth(method, data)

    def on_mail(self, message):
        self.from_l.append(message)
        self.ok()

    def on_rcpt(self, message):
        self.to_l.append(message)
        self.ok()

    def on_data(self, message):
        self.data()

    def on_quit(self, message):
        self.bye()
        self.close(flush = True)

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

    def to_s(self):
        return ", ".join(["<%s>" % email[3:].strip()[1:-1] for email in self.to_l])

    def received_s(self, for_s = False):
        to_s = self.to_s()
        date_time = datetime.datetime.utcfromtimestamp(self.time)
        date_s = date_time.strftime("%a, %d %b %Y %H:%M:%S +0000")
        return "from %s " % self.chost +\
            "by %s (netius) with ESMTP id %s" % (self.host, self.identifier) +\
            (" for %s" % to_s if for_s else "") +\
            "; %s" % date_s

class SMTPServer(netius.StreamServer):

    def __init__(self, adapter_s = "memory", auth_s = "dummy", locals = ("localhost",), *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.adapter_s = adapter_s
        self.auth_s = auth_s
        self.locals = locals

    def serve(self, host = "smtp.localhost", port = 25, *args, **kwargs):
        netius.StreamServer.serve(self, port = port, *args, **kwargs)
        self.host = host

    def on_connection_c(self, connection):
        netius.StreamServer.on_connection_c(self, connection)
        connection.ready()

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.StreamServer.on_serve(self)
        if self.env: self.host = self.get_env("SMTP_HOST", self.host)
        if self.env: self.adapter_s = self.get_env("SMTP_ADAPTER", self.adapter_s)
        if self.env: self.auth_s = self.get_env("SMTP_AUTH", self.auth_s)
        self.adapter = self.get_adapter(self.adapter_s)
        self.auth = self.get_auth(self.auth_s)
        self.info(
            "Starting SMTP server on '%s' using '%s' and '%s' ..." %
            (self.host, self.adapter_s, self.auth_s)
        )

    def new_connection(self, socket, address, ssl = False):
        return SMTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            host = self.host
        )

    def on_line_smtp(self, connection, code, message):
        pass

    def on_auth_smtp(self, connection, username, password):
        self.auth.auth_assert(username, password)
        connection.username = username

    def on_header_smtp(self, connection, from_l, to_l):
        # creates the list that will hold the various keys
        # to the adapter items that are going to be created
        # for the delivery of the message to the target then
        # retrieves the complete list of users associated with
        # the to (target) list of values
        keys = []
        locals = self._locals(to_l)
        users = self._users(locals)

        # iterates over the complete set of users to reserve
        # new keys for the various items to be delivered
        for user in users:
            key = self.adapter.reserve(owner = user)
            keys.append(key)

        # sets the list of reserved keys in the connection
        # and then generates a new identifier for the current
        # message that is going to be delivered/queued
        connection.keys = keys
        connection.identifier = self._generate(hashed = False)

    def on_data_smtp(self, connection, data):
        for key in connection.keys:
            self.adapter.append(key, data)

    def on_message_smtp(self, connection):
        for key in connection.keys:
            self.adapter.truncate(key, TERMINATION_SIZE)

    def _locals(self, sequence, prefix = "to"):
        emails = self._emails(sequence, prefix = prefix)
        emails = [email for email in emails if self._is_local(email)]
        return emails

    def _remotes(self, sequence, prefix = "to"):
        emails = self._emails(sequence, prefix = prefix)
        emails = [email for email in emails if not self._is_local(email)]
        return emails

    def _emails(self, sequence, prefix = "to"):
        prefix_l = len(prefix)
        base = prefix_l + 1
        emails = [item[base:].strip()[1:-1] for item in sequence]
        return emails

    def _users(self, emails):
        users = [email.split("@", 1)[0] for email in emails]
        return users

    def _is_local(self, email):
        domain = email.split("@", 1)[1]
        return domain in self.locals

if __name__ == "__main__":
    import logging
    server = SMTPServer(level = logging.DEBUG)
    server.serve(env = True)
