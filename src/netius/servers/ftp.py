#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import stat
import datetime

import netius.common

BUFFER_SIZE = 4096
""" The size of the buffer that is going to be used when
sending the file to the client, this should not be neither
to big nor to small (as both situations would create problems) """

CAPABILITIES = (
    "PASV",
    "UTF8"
)
""" The sequence defining the complete set of capabilities
that are available under the current ftp server implementation """

PERMISSIONS = {
    7 : "rwx",
    6 : "rw-",
    5 : "r-x",
    4 : "r--",
    0 : "---"
}
""" Map that defines the association between the octal based
values for the permissions and the associated string values """

TYPES = {
    "A" : "ascii",
    "E" : "ebcdic",
    "I" : "binary",
    "L" : "local"
}
""" The map that associated the various type command arguments
with the more rich data mode transfer types """

class FTPConnection(netius.Connection):

    def __init__(self, base_path = "", host = "ftp.localhost", mode = "ascii", *args, **kwargs):
        netius.Connection.__init__(self, *args, **kwargs)
        self.parser = None
        self.base_path = os.path.abspath(base_path)
        self.host = host
        self.mode = mode
        self.data_server = None
        self.cwd = "/"
        self.username = "anonymous"
        self.password = "anonymous"

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        self.parser = netius.common.FTPParser(self)
        self.parser.bind("on_line", self.on_line)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if self.parser: self.parser.destroy()
        if self.data_server: self.data_server.close_ftp()
        file = hasattr(self, "file") and self.file
        if file: file.close()

    def parse(self, data):
        return self.parser.parse(data)

    def send_ftp(self, code, message = "", lines = (), simple = False, delay = False, callback = None):
        if lines: self.send_ftp_lines(
            code,
            message = message,
            lines = lines,
            simple = simple,
            delay = delay,
            callback = callback
        )
        else: self.send_ftp_base(
            code,
            message,
            delay,
            callback
        )

    def send_ftp_base(self, code, message = "", delay = False, callback = None):
        base = "%d %s" % (code, message)
        data = base + "\r\n"
        self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)

    def send_ftp_lines(self, code, message = "", lines = (), simple = False, delay = False, callback = None):
        lines = list(lines)
        if not simple: lines.insert(0, message)
        body = lines[:-1]
        tail = lines[-1]
        base = "%d-%s" % (code, message) if simple else "%d %s" % (code, message)
        lines_s = [" %s" % line for line in body] if simple else\
            ["%d-%s" % (code, line) for line in body]
        lines_s.append("%d %s" % (code, tail))
        if simple: lines_s.insert(0, base)
        data = "\r\n".join(lines_s) + "\r\n"
        self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)

    def ready(self):
        message = "%s FTP Server %s ready" % (self.host, netius.NAME)
        self.send_ftp(220, message)

    def ok(self):
        message = "ok"
        self.send_ftp(200, message)

    def flush_ftp(self):
        if not self.remaining: return
        method = getattr(self, "flush_" + self.remaining)
        method()

    def flush_list(self):
        self.send_ftp(150, "directory list sending")
        list_data = self._list()
        self.data_server.send_ftp(list_data, callback = self.on_flush_list)

    def flush_retr(self):
        self.send_ftp(150, "file sending")

        relative_path = os.path.join(self.base_path, self.cwd[1:])
        full_path = os.path.join(relative_path, self.file_name)

        self.bytes_p = os.path.getsize(full_path)
        self.file = open(full_path, "rb")

        self._file_send(self)

    def on_flush_list(self, connection):
        self._data_close()
        self.send_ftp(226, "directory send ok")

    def on_flush_retr(self, connection):
        self._data_close()
        self.send_ftp(226, "file send ok")

    def on_line(self, code, message, is_final = True):
        # "joins" the code and the message part of the message into the base
        # string and then uses this value to print some debug information
        base = "%s %s" % (code, message)
        self.owner.debug(base)

        # calls the proper top level owner based line information handler that
        # should ignore any usages as the connection will take care of the proper
        # handling for the current connection
        self.owner.on_line_ftp(self, code, message)

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

    def on_user(self, message):
        self.username = message
        self.ok()

    def on_syst(self, message):
        self.send_ftp(215, message = netius.VERSION)

    def on_feat(self, message):
        self.send_ftp(211, "features", lines = list(CAPABILITIES) + ["end"], simple = True)

    def on_opts(self, message):
        self.ok()

    def on_pwd(self, message):
        self.send_ftp(257, "\"%s\"" % self.cwd)

    def on_type(self, message):
        self.mode = TYPES.get("message", "ascii")
        self.ok()

    def on_pasv(self, message):
        data_server = self._data_open()
        port_h = (data_server.port & 0xff00) >> 8
        port_l = data_server.port & 0x00ff
        address = self.socket.getsockname()[0]
        address = address.replace(".", ",")
        address_s = "%s,%d,%d" % (address, port_h, port_l)
        self.send_ftp(227, "entered passive mode (%s)" % address_s)

    def on_port(self, message):
        self.ok()

    def on_cdup(self, message):
        self.cwd = self.cwd.rsplit("/", 1)[0]
        if not self.cwd: self.cwd = "/"
        self.ok()

    def on_cwd(self, message):
        is_absolute = message.startswith("/")
        if is_absolute: self.cwd = message
        else: self.cwd += message if self.cwd.endswith("/") else "/" + message
        self.ok()

    def on_list(self, message):
        self.remaining = "list"

    def on_retr(self, message):
        self.remaining = "retr"
        self.file_name = message

    def _file_send(self, connection):
        file = self.file
        is_larger = BUFFER_SIZE > self.bytes_p
        buffer_s = self.bytes_p if is_larger else BUFFER_SIZE
        data = file.read(buffer_s)
        data_l = len(data) if data else 0
        self.bytes_p -= data_l
        is_final = not data or self.bytes_p == 0
        callback = self._file_finish if is_final else self._file_send
        self.data_server.send_ftp(
            data,
            delay = True,
            callback = callback
        )

    def _file_finish(self, connection):
        self.file.close()
        self.file = None
        self.bytes_p = None
        self.on_flush_retr(connection)

    def _data_open(self):
        if self.data_server: return
        self.data_server = FTPDataServer(self, self.owner)
        self.data_server.serve(
            host = self.owner.host,
            port = 0,
            load = False,
            start = False
        )
        return self.data_server

    def _data_close(self):
        if not self.data_server: return
        self.data_server.close_ftp()
        self.data_server = None

    def _list(self):
        # gathers the current relative (full) path for the state using
        # the current working directory value and normalizing it
        relative_path = os.path.join(self.base_path, self.cwd[1:])
        relative_path = os.path.abspath(relative_path)
        relative_path = os.path.normpath(relative_path)

        # lists the directory for the current relative path, this
        # should get a list of files contained in it, in case there's
        # an error in such listing an empty string is returned
        try: entries = os.listdir(relative_path)
        except: return ""

        # allocates space for the list that will hold the various lines
        # for the complete set of tiles in the directory
        lines = []

        # iterates over the complete set of entries in the current
        # working directory to create their respective listing line
        for entry in entries:
            file_path = os.path.join(relative_path, entry)
            try: mode = os.stat(file_path)
            except: continue
            permissions = self._to_unix(mode)
            timstamp = mode.st_mtime
            date_time = datetime.datetime.fromtimestamp(timstamp)
            date_s = date_time.strftime("%b %d  %Y")
            line = "%s    1 %-8s %-8s %8lu %s %s" %\
                (permissions, "ftp", "ftp", mode.st_size, date_s, entry)
            lines.append(line)

        # returns the final list string result as the joining of the
        # various lines for each of the files (as expected)
        return "\r\n".join(lines)

    def _to_unix(self, mode):
        is_dir = "d" if stat.S_ISDIR(mode.st_mode) else "-"
        permissions = str(oct(mode.st_mode)[-3:])
        return is_dir + "".join([PERMISSIONS.get(int(item), item) for item in permissions])

class FTPDataServer(netius.StreamServer):

    def __init__(self, connection, container, *args, **kwargs):
        netius.StreamServer.__init__(self, *args, **kwargs)
        self.connection = connection
        self.container = container
        self.accepted = None
        self.container.add_base(self)

    def on_connection_c(self, connection):
        netius.StreamServer.on_connection_c(self, connection)
        if self.accepted: connection.close(); return
        self.accepted = connection
        self.connection.flush_ftp()

    def send_ftp(self, data, delay = False, force = False, callback = None):
        if not self.accepted: raise netius.DataError("No connection accepted")
        return self.accepted.send(data, delay = delay, force = force, callback = callback)

    def close_ftp(self):
        if self.accepted: self.accepted.close(); self.accepted = None
        self.cleanup()

class FTPServer(netius.ContainerServer):

    def __init__(self, base_path = "", auth_s = "dummy", *args, **kwargs):
        netius.ContainerServer.__init__(self, *args, **kwargs)
        self.base_path = base_path
        self.auth_s = auth_s

    def serve(self, host = "ftp.localhost", port = 21, *args, **kwargs):
        netius.ContainerServer.serve(self, port = port, *args, **kwargs)
        self.host = host

    def on_connection_c(self, connection):
        netius.ContainerServer.on_connection_c(self, connection)
        connection.ready()

    def on_data(self, connection, data):
        netius.ContainerServer.on_data(self, connection, data)
        connection.parse(data)

    def on_serve(self):
        netius.ContainerServer.on_serve(self)
        if self.env: self.base_path = self.get_env("BASE_PATH", self.base_path)
        if self.env: self.host = self.get_env("FTP_HOST", self.host)
        if self.env: self.auth_s = self.get_env("FTP_AUTH", self.auth_s)
        self.auth = self.get_auth(self.auth_s)
        self.info("Starting FTP server on '%s' using '%s' ..." % (self.host, self.auth_s))
        self.info("Defining '%s' as the root of the file server ..." % (self.base_path or "."))

    def new_connection(self, socket, address, ssl = False):
        return FTPConnection(
            owner = self,
            socket = socket,
            address = address,
            ssl = ssl,
            base_path = self.base_path,
            host = self.host
        )

    def on_line_ftp(self, connection, code, message):
        pass

if __name__ == "__main__":
    import logging
    server = FTPServer(level = logging.DEBUG)
    server.serve(env = True)
