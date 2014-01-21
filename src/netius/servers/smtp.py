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

INTIAL_STATE = 1

HELLO_STATE = 2

HEADER_STATE = 3

DATA_STATE = 4

TERMINATION_SIZE = 5
""" The size of the termination sequence of the smtp message
this is going to be used in some parsing calculus """

class SMTPConnection(netius.Connection):

    def __init__(self, host = "smtp.localhost", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = netius.common.SMTPParser(self)
        self.host = host
        self.chost = None
        self.from_l = []
        self.to_l = []
        self.previous = ""
        self.state = INTIAL_STATE

        self.parser.bind("on_line", self.on_line)

    def parse(self, data):
        if self.state == DATA_STATE: self.on_raw_data(data)
        else: return self.parser.parse(data)

    def send_smtp(self, code, message = "", delay = False, callback = None):
        base = "%d %s" % (code, message)
        data = base + "\r\n"
        self.send(data, delay = delay, callback = callback)

    def ready(self):
        self.assert_s(INTIAL_STATE)
        self.state = HELLO_STATE
        message = "%s ESMTP %s" % (self.host, netius.NAME)
        self.send_smtp(220, message)

    def hello(self, host):
        self.assert_s(HELLO_STATE)
        self.state = HEADER_STATE
        self.chost = host
        message = "Hello %s, I am glad to meet you" % host
        self.send_smtp(250, message)

    def end_data(self):
        self.assert_s(HEADER_STATE)
        self.owner.on_header_smtp(self.from_l, self.to_l)
        self.state = DATA_STATE
        message = "End data with <CR><LF>.<CR><LF>"
        self.send_smtp(354, message)

    def queued(self, index = -1):
        self.assert_s(DATA_STATE)
        self.owner.on_message_smtp()
        self.state = HEADER_STATE
        message = "Ok: queued as %d" % index
        self.send_smtp(250, message)

    def bye(self):
        message = "Bye"
        self.send_smtp(221, message)

    def ok(self):
        message = "Ok"
        self.send_smtp(250, message)

    def not_implemented(self):
        message = "Not implemented"
        self.send_smtp(550, message)

    def on_raw_data(self, data):
        # calls the proper callback handler for data in the owner indicating
        # that the current data has just been received and must be properly
        # handled to the proper redirector middleware
        self.owner.on_data_smtp(data)

        # calculates the length of the data that has just been received and then
        # measures the size of the possible remaining bytes of the buffer from the
        # previously received ones and appends them to the buffer ten trying to
        # find the termination string in the final concatenated string
        data_l = len(data)
        remaining = TERMINATION_SIZE - data_l if TERMINATION_SIZE > data_l else 0
        previous_v = self.previous[remaining * -1:] if remaining > 0 else ""
        buffer = previous_v + data[TERMINATION_SIZE * -1:]
        is_final = not buffer.find("\r\n.\r\n") == -1

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

    def on_line(self, code, message):
        # "joins" the code and the message part of the message into the base
        # string and then uses this value to print some debug information
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # calls the proper top level owner based line information handler that
        # should ignore any usages as the connection will take care of the proper
        # handling for the current connection
        self.owner.on_line_smtp(code, message)

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
        self.not_implemented()

    def on_mail(self, message):
        self.from_l.append(message)
        self.ok()

    def on_rcpt(self, message):
        self.to_l.append(message)
        self.ok()

    def on_data(self, message):
        self.end_data()

    def on_quit(self, message):
        self.bye()

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

class SMTPServer(netius.StreamServer):

    def __init__(self, *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)

    def serve(self, port = 25, *args, **kwargs):
        netius.StreamServer.serve(self, port = port, *args, **kwargs)

    def on_connection_c(self, connection):
        netius.StreamServer.on_connection_c(self, connection)
        connection.ready()

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.StreamServer.on_serve(self)
        self.info("Starting SMTP server ...")

    def new_connection(self, socket, address, ssl = False):
        return SMTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl
        )

    def on_line_smtp(self, code, message):
        pass

    def on_header_smtp(self, from_l, to_l):
        pass

    def on_data_smtp(self, data):
        pass

    def on_message_smtp(self):
        pass

if __name__ == "__main__":
    import logging
    server = SMTPServer(level = logging.DEBUG)
    server.serve(env = True)
