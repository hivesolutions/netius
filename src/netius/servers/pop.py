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

import netius.common

INTIAL_STATE = 1

HELO_STATE = 2

AUTH_STATE = 3

SESSION_STATE = 4

CHUNK_SIZE = 16384
""" The size of the chunk to be used for the partial sending
of the message to the client, this value will affect the
memory used by the server and its network performance """

CAPABILITIES = (
    "TOP",
    "USER",
    "STLS"
)
""" The capabilities that are going to be exposed to the client
as the ones handled by the server, should only expose the ones
that are properly handled by the server """

AUTH_METHODS = (
    "PLAIN",
)
""" Authentication methods that are available to be "used" by
the client, should be mapped into the proper auth handlers """

class POPConnection(netius.Connection):

    def __init__(self, host = "pop.localhost", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.host = host
        self.username = None
        self.token_buf = []
        self.count = 0
        self.byte_c = 0
        self.size = 0
        self.file = None
        self.sizes = ()
        self.keys = ()
        self.state = INTIAL_STATE

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open(): return
        self.parser = netius.common.POPParser(self)
        self.parser.bind("on_line", self.on_line)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed(): return
        if self.file: self.file.close(); self.file = None
        if self.parser: self.parser.destroy()

    def parse(self, data):
        if self.state == AUTH_STATE: self.on_user(data)
        else: return self.parser.parse(data)

    def send_pop(self, message = "", lines = (), status = "OK", delay = True, callback = None):
        status_s = "+" + status if status == "OK" else "-" + status
        base = "%s %s" % (status_s, message)
        data = base + "\r\n"
        if lines: data += "\r\n".join(lines) + "\r\n.\r\n"
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def ready(self):
        self.assert_s(INTIAL_STATE)
        message = "POP3 server ready <%s@%s>" % (netius.NAME, self.host)
        self.send_pop(message)
        self.state = HELO_STATE

    def starttls(self):
        def callback(connection):
            connection.upgrade(server = True)
        message = "go ahead"
        self.send_pop(message, callback = callback)
        self.state = HELO_STATE

    def capa(self):
        self.assert_s(HELO_STATE)
        message = "list follows"
        self.send_pop(message, lines = CAPABILITIES)
        self.state = HELO_STATE

    def auth(self):
        self.assert_s(HELO_STATE)
        message = "list follows"
        self.send_pop(message, lines = AUTH_METHODS)
        self.state = HELO_STATE

    def accept(self):
        self.assert_s(HELO_STATE)
        self.ok()
        self.token_buf = []
        self.state = AUTH_STATE

    def stat(self):
        self.owner.on_stat_pop(self)
        message = "%d %d" % (self.count, self.byte_c)
        self.send_pop(message)

    def list(self):
        self.owner.on_list_pop(self)
        message = "%d messages (%d octets)" % (self.count, self.byte_c)
        lines = []
        for index in range(self.count):
            size = self.sizes[index]
            line = "%d %d" % (index, size)
            lines.append(line)
        self.send_pop(message, lines = lines)

    def uidl(self):
        self.owner.on_uidl_pop(self)
        message = "%d messages (%d octets)" % (self.count, self.byte_c)
        lines = []
        for index in range(self.count):
            key = self.keys[index]
            line = "%d %s" % (index, key)
            lines.append(line)
        self.send_pop(message, lines = lines)

    def retr(self, index):
        def callback(connection):
            if not connection.file: return
            file = connection.file
            contents = file.read(CHUNK_SIZE)
            if contents: self.send(contents, callback = callback)
            else: self.send("\r\n.\r\n"); file.close(); connection.file = None
        self.owner.on_retr_pop(self, index)
        message = "%d octets" % self.size
        self.send_pop(message, callback = callback)
        callback(self)

    def dele(self, index):
        self.owner.on_dele_pop(self, index)
        message = "removed"
        self.send_pop(message)

    def bye(self):
        message = "bye"
        self.send_pop(message)

    def ok(self):
        message = "accepted"
        self.send_pop(message)

    def not_implemented(self):
        message = "not implemented"
        self.send_pop(message, status = "ERR")

    def on_line(self, code, message):
        # "joins" the code and the message part of the message into the base
        # string and then uses this value to print some debug information
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # calls the proper top level owner based line information handler that
        # should ignore any usages as the connection will take care of the proper
        # handling for the current connection
        self.owner.on_line_pop(self, code, message)

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

    def on_stls(self, message):
        self.starttls()

    def on_capa(self, message):
        self.capa()

    def on_auth(self, message):
        if message: self.accept()
        else: self.auth()

    def on_stat(self, message):
        self.stat()

    def on_list(self, message):
        self.list()

    def on_uidl(self, message):
        self.uidl()

    def on_retr(self, message):
        index = int(message)
        self.retr(index)

    def on_dele(self, message):
        index = int(message)
        self.dele(index)

    def on_quit(self, message):
        self.bye()
        self.close(flush = True)

    def on_user(self, token):
        # adds the partial token value to the token buffer and
        # then verifies if it contains the token if that's the
        # case continues the parsing otherwise returns immediately
        self.token_buf.append(token)
        index = token.find(b"\n")
        if index == -1: return

        # removes the extra characters from the token so that no
        # extra value is considered to be part of the token
        token = token.rstrip()

        # logs the received token as this handler is not a callback
        # from the typical on message method
        self.owner.debug(token)

        # joins the the token buffer recreating the token string
        # and then decodes into as a base 64 string and splits it
        # around its own components so that the proper auth callback
        # may be called to validate the authentication
        token = b"".join(self.token_buf)
        token_s = base64.b64decode(token)
        token_s = netius.legacy.str(token_s)
        _identifier, username, password = token_s.split("\0")

        # calls the callback to the authentication and in case everything
        # goes ok the ok value is called and the state of the current
        # connection is changed to session (authentication is valid)
        self.owner.on_auth_pop(self, username, password)
        self.ok()
        self.state = SESSION_STATE

    def assert_s(self, expected):
        if self.state == expected: return
        raise netius.ParserError("Invalid state")

class POPServer(netius.StreamServer):

    def __init__(self, adapter_s = "memory", auth_s = "dummy", *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.adapter_s = adapter_s
        self.auth_s = auth_s

    def serve(self, host = "pop.localhost", port = 110, *args, **kwargs):
        netius.StreamServer.serve(self, port = port, *args, **kwargs)
        self.host = host

    def on_connection_c(self, connection):
        netius.StreamServer.on_connection_c(self, connection)
        connection.ready()

    def on_connection_d(self, connection):
        netius.StreamServer.on_connection_d(self, connection)
        if connection.file: connection.file.close(); connection.file = None

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.StreamServer.on_serve(self)
        if self.env: self.host = self.get_env("POP_HOST", self.host)
        if self.env: self.adapter_s = self.get_env("POP_ADAPTER", self.adapter_s)
        if self.env: self.auth_s = self.get_env("POP_AUTH", self.auth_s)
        self.adapter = self.get_adapter(self.adapter_s)
        self.auth = self.get_auth(self.auth_s)
        self.info(
            "Starting POP server on '%s' using '%s' and '%s' ..." %
            (self.host, self.adapter_s, self.auth_s)
        )

    def new_connection(self, socket, address, ssl = False):
        return POPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            host = self.host
        )

    def on_line_pop(self, connection, code, message):
        pass

    def on_auth_pop(self, connection, username, password):
        self.auth.auth_assert(username, password)
        connection.username = username

    def on_stat_pop(self, connection):
        username = connection.username
        count = self.adapter.count(owner = username)
        total = self.adapter.total(owner = username)
        connection.count = count
        connection.byte_c = total

    def on_list_pop(self, connection):
        username = connection.username
        sizes = self.adapter.sizes(owner = username)
        connection.sizes = sizes

    def on_uidl_pop(self, connection):
        username = connection.username
        connection.keys = self.adapter.list(owner = username)

    def on_retr_pop(self, connection, index):
        key = connection.keys[index]
        connection.size = self.adapter.size(key)
        connection.file = self.adapter.get_file(key)

    def on_dele_pop(self, connection, index):
        username = connection.username
        key = connection.keys[index]
        self.adapter.delete(key, owner = username)

if __name__ == "__main__":
    import logging
    server = POPServer(level = logging.DEBUG)
    server.serve(env = True)
