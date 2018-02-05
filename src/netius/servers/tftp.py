#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import struct

import netius.common

class TFTPSession(object):

    def __init__(self, owner, name = None, mode = None):
        self.owner = owner
        self.name = name
        self.mode = mode
        self.file = None
        self.completed = False
        self.sequence = 0

    def close(self):
        self.reset()

    def reset(self):
        if self.file: self.file.close()
        self.name = None
        self.mode = None
        self.file = None
        self.completed = False
        self.sequence = 0

    def next(self, size = 512, increment = True):
        if self.completed: return None
        file = self._get_file()
        data = file.read(size)
        self.completed = len(data) < size
        if increment: self.increment()
        header = struct.pack("!HH", netius.common.DATA_TFTP, self.sequence)
        return header + data

    def ack(self, size = 512, increment = True):
        if self.sequence == 0: return None
        return self.next(size = size, increment = increment)

    def increment(self):
        self.sequence += 1

    def get_info(self):
        buffer = netius.legacy.StringIO()
        buffer.write("name      := %s\n" % self.name)
        buffer.write("mode      := %s\n" % self.mode)
        buffer.write("completed := %d\n" % self.completed)
        buffer.write("sequence  := %d" % self.sequence)
        buffer.seek(0)
        info = buffer.read()
        return info

    def print_info(self):
        info = self.get_info()
        print(info)

    def _get_file(self, allow_absolute = False):
        if self.file: return self.file
        if not allow_absolute: name = self.name.lstrip("/")
        path = os.path.join(self.owner.base_path, name)
        self.file = open(path, "rb")
        return self.file

class TFTPRequest(object):

    parsers_m = None
    parsers_l = None

    def __init__(self, data, session):
        self.data = data
        self.session = session

        cls = self.__class__
        cls.generate()

    @classmethod
    def generate(cls):
        if cls.parsers_m: return
        cls.parsers_m = (
            cls._parse_rrq,
            cls._parse_wrq,
            cls._parse_data,
            cls._parse_ack,
            cls._parse_error
        )
        cls.parsers_l = len(cls.parsers_m)

    def get_info(self):
        session_info = self.session.get_info()
        buffer = netius.legacy.StringIO()
        buffer.write("op        := %d\n" % self.op)
        buffer.write("payload   := %s" % repr(self.payload))
        if session_info: buffer.write("\n" + session_info)
        buffer.seek(0)
        info = buffer.read()
        return info

    def print_info(self):
        info = self.get_info()
        print(info)

    def parse(self):
        cls = self.__class__

        format = "!H"

        self.header = self.data[:2]
        self.payload = self.data[2:]
        result = struct.unpack(format, self.header)
        self.op = result[0]

        method = cls.parsers_m[self.op - 1]
        method(self)

    def get_type(self):
        return self.op

    def get_type_s(self):
        type = self.get_type()
        type_s = netius.common.TYPES_TFTP.get(type, None)
        return type_s

    def response(self, options = {}):
        if self.op == netius.common.ACK_TFTP: return self.session.ack()
        return self.session.next()

    @classmethod
    def _parse_rrq(cls, self):
        payload = self.payload
        self.session.reset()
        self.session.name, payload = cls._str(payload)
        self.session.mode, payload = cls._str(payload)

    @classmethod
    def _parse_wrq(cls, self):
        raise netius.NotImplemented("Operation not implemented")

    @classmethod
    def _parse_data(cls, self):
        raise netius.NotImplemented("Operation not implemented")

    @classmethod
    def _parse_ack(cls, self):
        pass

    @classmethod
    def _parse_error(cls, self):
        raise netius.NotImplemented("Operation not implemented")

    @classmethod
    def _str(cls, data):
        index = data.index(b"\x00")
        value, remaining = data[:index], data[index + 1:]
        value = netius.legacy.str(value)
        return value, remaining

class TFTPServer(netius.DatagramServer):
    """
    Abstract trivial ftp server implementation that handles simple
    file system based file serving.

    :see: http://tools.ietf.org/html/rfc1350
    """

    ALLOWED_OPERATIONS = (
        netius.common.RRQ_TFTP,
        netius.common.ACK_TFTP
    )

    def __init__(self, base_path = "", *args, **kwargs):
        netius.DatagramServer.__init__(self, *args, **kwargs)
        self.base_path = base_path
        self.sessions = dict()

    def serve(self, port = 69, *args, **kwargs):
        netius.DatagramServer.serve(self, port = port, *args, **kwargs)

    def on_data(self, address, data):
        netius.DatagramServer.on_data(self, address, data)

        try:
            session = self.sessions.get(address, None)
            if not session: session = TFTPSession(self)
            self.sessions[address] = session

            request = TFTPRequest(data, session)
            request.parse()

            self.on_data_tftp(address, request)
        except BaseException as exception:
            self.on_error_tftp(address, exception)

    def on_serve(self):
        netius.DatagramServer.on_serve(self)
        if self.env: self.base_path = self.get_env("BASE_PATH", self.base_path)
        self.info("Starting TFTP server ...")
        self.info("Defining '%s' as the root of the file server ..." % (self.base_path or "."))

    def on_data_tftp(self, address, request):
        cls = self.__class__

        type = request.get_type()
        type_s = request.get_type_s()

        self.debug("Received %s message from '%s'" % (type_s, address))

        if not type in cls.ALLOWED_OPERATIONS:
            raise netius.NetiusError(
                "Invalid operation type '%d'", type
            )

        response = request.response()
        if not response: return

        self.send(response, address)

    def on_error_tftp(self, address, exception):
        message = str(exception)
        message_b = netius.legacy.bytes(message)
        header = struct.pack("!HH", netius.common.ERROR_TFTP, 0)
        response = header + message_b + b"\x00"
        self.send(response, address)
        self.info("Sent error message '%s' to '%s'" % (message, address))

if __name__ == "__main__":
    import logging
    server = TFTPServer(level = logging.DEBUG)
    server.serve(env = True)
else:
    __path__ = []
