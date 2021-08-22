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

import os
import stat
import datetime

import netius.common

BUFFER_SIZE = 16384
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
        self.remaining = None
        self.cwd = "/"
        self.username = "anonymous"
        self.password = "anonymous"

    def open(self, *args, **kwargs):
        netius.Connection.open(self, *args, **kwargs)
        if not self.is_open(): return
        self.parser = netius.common.FTPParser(self)
        self.parser.bind("on_line", self.on_line)

    def close(self, *args, **kwargs):
        netius.Connection.close(self, *args, **kwargs)
        if not self.is_closed(): return
        if self.parser: self.parser.destroy()
        if self.data_server: self.data_server.close_ftp()
        file = hasattr(self, "file") and self.file
        if file: file.close()

    def parse(self, data):
        return self.parser.parse(data)

    def send_ftp(self, code, message = "", lines = (), simple = False, delay = True, callback = None):
        if lines: return self.send_ftp_lines(
            code,
            message = message,
            lines = lines,
            simple = simple,
            delay = delay,
            callback = callback
        )
        else: return self.send_ftp_base(
            code,
            message,
            delay,
            callback
        )

    def send_ftp_base(self, code, message = "", delay = True, callback = None):
        base = "%d %s" % (code, message)
        data = base + "\r\n"
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def send_ftp_lines(self, code, message = "", lines = (), simple = False, delay = True, callback = None):
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
        count = self.send(data, delay = delay, callback = callback)
        self.owner.debug(base)
        return count

    def ready(self):
        message = "%s FTP Server %s ready" % (self.host, netius.NAME)
        self.send_ftp(220, message)

    def ok(self):
        message = "ok"
        self.send_ftp(200, message)

    def not_ok(self):
        message = "not ok"
        self.send_ftp(500, message)

    def flush_ftp(self):
        if not self.remaining: return
        method = getattr(self, "flush_" + self.remaining)
        try: method()
        finally: self.remaining = None

    def data_ftp(self, data):
        self.file.write(data)

    def closed_ftp(self):
        has_file = hasattr(self, "file") and not self.file == None
        if not has_file: return
        self.file.close()
        self.file = None
        self.send_ftp(226, "file receive ok")

    def flush_list(self):
        self.send_ftp(150, "directory list sending")
        list_data = self._list()
        self.data_server.send_ftp(list_data, callback = self.on_flush_list)

    def flush_retr(self):
        self.send_ftp(150, "file sending")
        full_path = self._get_path(self.file_name)
        self.bytes_p = os.path.getsize(full_path)
        self.file = open(full_path, "rb")
        self._file_send(self)

    def flush_stor(self):
        self.send_ftp(150, "file receiving")

        full_path = self._get_path(self.file_name)
        self.file = open(full_path, "wb")

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
        self.send_ftp(215, message = "UNIX Type: L8 (%s)" % netius.VERSION)

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

    def on_dele(self, message):
        full_path = self._get_path(extra = message)
        try: os.remove(full_path)
        except Exception: self.not_ok()
        else: self.ok()

    def on_mkd(self, message):
        full_path = self._get_path(extra = message)
        try: os.makedirs(full_path)
        except Exception: self.not_ok()
        else: self.ok()

    def on_rmd(self, message):
        full_path = self._get_path(extra = message)
        try: os.rmdir(full_path)
        except Exception: self.not_ok()
        else: self.ok()

    def on_rnfr(self, message):
        self.source_path = self._get_path(extra = message)
        self.ok()

    def on_rnto(self, message):
        self.target_path = self._get_path(extra = message)
        try: os.rename(self.source_path, self.target_path)
        except Exception: self.not_ok()
        else: self.ok()
        finally: self.source_path = self.target_path = None

    def on_cdup(self, message):
        self.cwd = self.cwd.rsplit("/", 1)[0]
        if not self.cwd: self.cwd = "/"
        self.ok()

    def on_cwd(self, message):
        is_absolute = message.startswith("/")
        if is_absolute: cwd = message
        else: cwd = self.cwd + (message if self.cwd.endswith("/") else "/" + message)

        full_path = self._get_path(extra = message)
        is_dir = os.path.isdir(full_path)
        if not is_dir: self.send_ftp(550, "failed to change directory"); return

        self.cwd = cwd
        self.ok()

    def on_size(self, message):
        full_path = self._get_path(extra = message)
        if os.path.isdir(full_path): size = 0
        else: size = os.path.getsize(full_path)
        self.send_ftp(213, "%d" % size)

    def on_mdtm(self, message):
        full_path = self._get_path(extra = message)
        if os.path.isdir(full_path): modified = 0
        else: modified = os.path.getmtime(full_path)
        modified_d = datetime.datetime.utcfromtimestamp(modified)
        modified_s = modified_d.strftime("%Y%m%d%H%M%S")
        self.send_ftp(213, modified_s)

    def on_noop(self, message):
        self.ok()

    def on_quit(self, message):
        self.send_ftp(221, "exiting connection")

    def on_list(self, message):
        self.remaining = "list"
        self.data_server.flush_ftp()

    def on_retr(self, message):
        self.remaining = "retr"
        self.file_name = message
        self.data_server.flush_ftp()

    def on_stor(self, message):
        self.remaining = "stor"
        self.file_name = message
        self.data_server.flush_ftp()

    def _file_send(self, connection):
        file = self.file
        is_larger = BUFFER_SIZE > self.bytes_p
        buffer_s = self.bytes_p if is_larger else BUFFER_SIZE
        data = file.read(buffer_s)
        data_l = len(data) if data else 0
        self.bytes_p -= data_l
        is_final = not data or self.bytes_p == 0
        callback = self._file_finish if is_final else self._file_send
        self.data_server.send_ftp(data, callback = callback)

    def _file_finish(self, connection):
        self.file.close()
        self.file = None
        self.bytes_p = None
        self.on_flush_retr(connection)

    def _data_open(self):
        if self.data_server: self._data_close()
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
        # retrieves the current value for the relative path, this
        # should take into account the current working directory
        relative_path = self._get_path()

        # lists the directory for the current relative path, this
        # should get a list of files contained in it, in case there's
        # an error in such listing an empty string is returned
        try: entries = os.listdir(relative_path)
        except Exception: return ""

        # allocates space for the list that will hold the various lines
        # for the complete set of tiles in the directory
        lines = []

        # iterates over the complete set of entries in the current
        # working directory to create their respective listing line
        for entry in entries:
            file_path = os.path.join(relative_path, entry)
            try: mode = os.stat(file_path)
            except Exception: continue
            permissions = self._to_unix(mode)
            timestamp = mode.st_mtime
            date_time = datetime.datetime.utcfromtimestamp(timestamp)
            date_s = date_time.strftime("%b %d  %Y")
            line = "%s    1 %-8s %-8s %8lu %s %s\r\n" %\
                (permissions, "ftp", "ftp", mode.st_size, date_s, entry)
            lines.append(line)

        # returns the final list string result as the joining of the
        # various lines for each of the files (as expected)
        return "".join(lines)

    def _to_unix(self, mode):
        is_dir = "d" if stat.S_ISDIR(mode.st_mode) else "-"
        permissions = str(oct(mode.st_mode)[-3:])
        return is_dir + "".join([PERMISSIONS.get(int(item), item) for item in permissions])

    def _get_path(self, extra = None):
        # tries to decide on own to resolve the base and extra parts
        # of the path taking into account a possible absolute extra
        # value, the current working directory is only used in case
        # the provided extra value is not absolute
        is_absolute = extra.startswith("/") if extra else False
        base = extra[1:] if is_absolute else self.cwd[1:]
        extra = "" if is_absolute else extra or ""

        # gathers the current relative (full) path for the state using
        # the current working directory value and normalizing it, note
        # that in case an extra (relative) path is provided it's joined
        # with the base path to provide the "new" full path
        relative_path = os.path.join(self.base_path, base)
        relative_path = os.path.join(relative_path, extra)
        relative_path = os.path.abspath(relative_path)
        relative_path = os.path.normpath(relative_path)
        return relative_path

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
        self.flush_ftp()

    def on_connection_d(self, connection):
        netius.StreamServer.on_connection_d(self, connection)
        self.connection.closed_ftp()

    def on_data(self, connection, data):
        netius.StreamServer.on_data(self, connection, data)
        self.connection.data_ftp(data)

    def send_ftp(self, data, delay = True, force = False, callback = None):
        if not self.accepted: raise netius.DataError("No connection accepted")
        return self.accepted.send(data, delay = delay, force = force, callback = callback)

    def flush_ftp(self):
        if not self.accepted: return
        self.connection.flush_ftp()

    def close_ftp(self):
        if self.accepted: self.accepted.close(); self.accepted = None
        self.cleanup()

class FTPServer(netius.ContainerServer):
    """
    Abstract ftp server implementation that handles authentication
    and file system based file serving.

    Note that the ftp server does not support multiple user handling
    and runs only as the user running the current process.

    :see: http://tools.ietf.org/html/rfc959
    """

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

    def build_connection(self, socket, address, ssl = False):
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
else:
    __path__ = []
