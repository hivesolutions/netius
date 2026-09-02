#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import shutil
import socket
import logging
import tempfile
import unittest

import netius
import netius.servers

from netius.servers import ftp

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class FTPConnectionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.server = netius.servers.FTPServer(level=logging.CRITICAL)
        self.connection = ftp.FTPConnection.__new__(ftp.FTPConnection)
        self.connection.owner = self.server
        self.connection.cwd = "/"
        self.connection.mode = "ascii"
        self.sent = []
        self.connection.send_ftp = lambda code, message="", **kwargs: self.sent.append(
            (code, message)
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()

    def test_on_user(self):
        self.connection.on_user("joe")

        self.assertEqual(self.connection.username, "joe")
        self.assertEqual(self.sent[-1][0], 200)

    def test_on_pwd(self):
        self.connection.on_pwd("")

        self.assertEqual(self.sent[-1], (257, '"/"'))

    def test_on_type(self):
        # the argument of the command selects the transfer mode, so a
        # binary transfer really has to switch the connection over to it
        self.connection.on_type("I")

        self.assertEqual(self.connection.mode, "binary")
        self.assertEqual(self.sent[-1][0], 200)

    def test_on_type_modes(self):
        for argument, mode in (
            ("A", "ascii"),
            ("E", "ebcdic"),
            ("I", "binary"),
            ("L", "local"),
        ):
            self.connection.on_type(argument)

            self.assertEqual(self.connection.mode, mode)

    def test_on_type_unknown(self):
        # an argument that names no known mode falls back to the textual
        # one, which is the mode a session starts at
        self.connection.on_type("Z")

        self.assertEqual(self.connection.mode, "ascii")

    def test_on_noop(self):
        self.connection.on_noop("")

        self.assertEqual(self.sent[-1][0], 200)

    def test_on_line(self):
        self.connection.on_line("PWD", "")

        self.assertEqual(self.sent[-1], (257, '"/"'))

    def test_on_line_unknown(self):
        # a code that the server does not handle must be rejected as a
        # protocol error instead of reaching any other method
        self.assertRaises(netius.ParserError, self.connection.on_line, "NOPE", "")

    def test_on_line_method(self):
        # the resolution of the handler is restricted to the commands, so
        # that a code that happens to match another method of the
        # connection is never able to reach it
        for code in ("LINE", "FLUSH_LIST", "FLUSH_RETR"):
            self.assertRaises(netius.ParserError, self.connection.on_line, code, "")


class FTPConnectionPathTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.base = tempfile.mkdtemp()
        self.server = netius.servers.FTPServer(
            base_path=self.base, level=logging.CRITICAL
        )
        self.connection = ftp.FTPConnection.__new__(ftp.FTPConnection)
        self.connection.owner = self.server
        self.connection.base_path = os.path.abspath(self.base)
        self.connection.cwd = "/"
        self.connection.mode = "ascii"
        self.connection.data_server = None
        self.connection.remaining = None
        self.sent = []
        self.connection.send_ftp = lambda code, message="", **kwargs: self.sent.append(
            (code, message)
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        file = hasattr(self.connection, "file") and self.connection.file
        if file:
            file.close()
        self.server.cleanup()
        shutil.rmtree(self.base)

    def test_ready(self):
        self.connection.host = "ftp.localhost"

        self.connection.ready()

        # the greeting of the service names the host that it answers for, so
        # that the peer knows what it reached
        self.assertEqual(self.sent[-1][0], 220)
        self.assertEqual("ftp.localhost" in self.sent[-1][1], True)

    def test_ok(self):
        self.connection.ok()
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.not_ok()

        # the two plain answers of the protocol, one for a command that was
        # served and one for a command that was refused
        self.assertEqual(self.sent[-1], (500, "not ok"))

    def test_flush_ftp(self):
        # a connection with nothing left over has no flushing of its own to
        # be done, and must not reach for a handler that does not exist
        self.assertEqual(self.connection.flush_ftp(), None)

        self.connection.remaining = "list"

        with mock.patch.object(self.connection, "flush_list") as flush_list:
            self.connection.flush_ftp()

        # what was left over names the handler that runs, and it is cleared
        # afterwards so that it never runs twice
        self.assertEqual(flush_list.called, True)
        self.assertEqual(self.connection.remaining, None)

        self.connection.remaining = "list"

        with mock.patch.object(self.connection, "flush_list", side_effect=Exception):
            self.assertRaises(Exception, self.connection.flush_ftp)

        # a handler that fails still clears what was left over, or the
        # connection would try the same operation again
        self.assertEqual(self.connection.remaining, None)

    def test_closed_ftp(self):
        # a connection that was never storing a file has none of it to be
        # closed, so the ending of the transfer is a no operation
        self.assertEqual(self.connection.closed_ftp(), None)

        path = self._store("file.txt", b"")
        self.connection.file = open(path, "wb")

        self.connection.closed_ftp()

        # the file that was being received is closed and the peer is told
        # that the transfer of it is complete
        self.assertEqual(self.connection.file, None)
        self.assertEqual(self.sent[-1][0], 226)

    def test_data_ftp(self):
        path = self._store("file.txt", b"")
        self.connection.file = open(path, "wb")
        try:
            self.connection.data_ftp(b"contents")
        finally:
            self.connection.file.close()

        # what arrives over the data connection is written to the file that
        # the transfer opened for it
        file = open(path, "rb")
        try:
            self.assertEqual(file.read(), b"contents")
        finally:
            file.close()

    def test_on_syst(self):
        self.connection.on_syst("")

        # the kind of the system is answered with, carrying the version of
        # the package that serves it
        self.assertEqual(self.sent[-1][0], 215)
        self.assertEqual("UNIX Type: L8" in self.sent[-1][1], True)

    def test_on_opts(self):
        self.connection.on_opts("UTF8 ON")
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.on_port("")

        # neither the options nor the active mode change anything of the
        # session, both of them being answered plainly
        self.assertEqual(self.sent[-1], (200, "ok"))

    def test_on_dele(self):
        path = self._store("file.txt", b"contents")

        self.connection.on_dele("file.txt")

        # the file that was named is removed from the disk and the peer is
        # told that the command was served
        self.assertEqual(os.path.exists(path), False)
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.on_dele("file.txt")

        # a file that is no longer there cannot be removed again, which is
        # reported back rather than raised
        self.assertEqual(self.sent[-1], (500, "not ok"))

    def test_on_mkd(self):
        self.connection.on_mkd("folder")

        # the directory that was named is created under the root of the
        # service, the peer being told that it was
        self.assertEqual(os.path.isdir(os.path.join(self.base, "folder")), True)
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.on_mkd("folder")

        # a directory that is already there cannot be created again
        self.assertEqual(self.sent[-1], (500, "not ok"))

    def test_on_rmd(self):
        os.makedirs(os.path.join(self.base, "folder"))

        self.connection.on_rmd("folder")

        self.assertEqual(os.path.isdir(os.path.join(self.base, "folder")), False)
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.on_rmd("folder")

        # a directory that is no longer there cannot be removed again
        self.assertEqual(self.sent[-1], (500, "not ok"))

    def test_on_rnfr(self):
        self._store("file.txt", b"contents")

        self.connection.on_rnfr("file.txt")
        self.connection.on_rnto("other.txt")

        # the renaming takes two commands, the first one naming the source
        # and the second one the target that it moves to
        self.assertEqual(os.path.exists(os.path.join(self.base, "other.txt")), True)
        self.assertEqual(self.sent[-1], (200, "ok"))

        # both of the paths are cleared once the renaming is over, so that a
        # later one never reuses them
        self.assertEqual(self.connection.source_path, None)
        self.assertEqual(self.connection.target_path, None)

    def test_on_rnto_missing(self):
        self.connection.on_rnfr("missing.txt")
        self.connection.on_rnto("other.txt")

        # a source that is not there cannot be renamed, which is reported
        # back instead of raising
        self.assertEqual(self.sent[-1], (500, "not ok"))
        self.assertEqual(self.connection.source_path, None)

    def test_on_cdup(self):
        self.connection.cwd = "/one/two"

        self.connection.on_cdup("")

        # walking up takes the last part of the working directory off it
        self.assertEqual(self.connection.cwd, "/one")

        self.connection.on_cdup("")
        self.assertEqual(self.connection.cwd, "/")

        self.connection.on_cdup("")

        # the root has nothing above it, so walking up from it stays where
        # it is instead of leaving the working directory empty
        self.assertEqual(self.connection.cwd, "/")

    def test_on_cwd(self):
        os.makedirs(os.path.join(self.base, "folder"))

        self.connection.on_cwd("folder")

        # a directory that exists becomes the working one, named relative to
        # the root of the service
        self.assertEqual(self.connection.cwd, "/folder")
        self.assertEqual(self.sent[-1], (200, "ok"))

        self.connection.on_cwd("/")
        self.assertEqual(self.connection.cwd, "/")

        self.connection.on_cwd("missing")

        # a directory that does not exist cannot be entered, the working one
        # staying where it was
        self.assertEqual(self.sent[-1][0], 550)
        self.assertEqual(self.connection.cwd, "/")

    def test_on_size(self):
        self._store("file.txt", b"0" * 12)

        self.connection.on_size("file.txt")

        # the size of a file is the one on the disk, answered as a plain
        # number of bytes
        self.assertEqual(self.sent[-1], (213, "12"))

        os.makedirs(os.path.join(self.base, "folder"))

        self.connection.on_size("folder")

        # a directory has no size of its own to be reported, so it counts
        # as an empty one
        self.assertEqual(self.sent[-1], (213, "0"))

    def test_on_mdtm(self):
        self._store("file.txt", b"contents")

        self.connection.on_mdtm("file.txt")

        # the moment a file was last written is answered as a stamp of the
        # fourteen digits that name it
        self.assertEqual(self.sent[-1][0], 213)
        self.assertEqual(len(self.sent[-1][1]), 14)

        os.makedirs(os.path.join(self.base, "folder"))

        self.connection.on_mdtm("folder")

        # a directory has no moment of its own, so the start of the epoch is
        # what stands for it
        self.assertEqual(self.sent[-1][1], "19700101000000")

    def test_on_quit(self):
        self.connection.on_quit("")
        self.assertEqual(self.sent[-1][0], 221)

    def test_on_list(self):
        self.connection.data_server = mock.MagicMock()

        self.connection.on_list("")

        # the listing is left over for the data connection to flush, as it
        # is the one that carries it
        self.assertEqual(self.connection.remaining, "list")
        self.assertEqual(self.connection.data_server.flush_ftp.called, True)

        self.connection.on_retr("file.txt")

        # the same holds for a file that is read, the name of it being kept
        # for the flushing that follows
        self.assertEqual(self.connection.remaining, "retr")
        self.assertEqual(self.connection.file_name, "file.txt")

        self.connection.on_stor("other.txt")

        self.assertEqual(self.connection.remaining, "stor")
        self.assertEqual(self.connection.file_name, "other.txt")

    def test_flush_stor(self):
        self.connection.file_name = "file.txt"

        self.connection.flush_stor()
        try:
            # the file that is going to receive the transfer is opened for
            # writing and the peer is told that it may start
            self.assertEqual(self.sent[-1][0], 150)
            self.assertEqual(self.connection.file.closed, False)
        finally:
            self.connection.file.close()

    def test__list(self):
        self._store("file.txt", b"0" * 12)
        os.makedirs(os.path.join(self.base, "folder"))

        listing = self.connection._list()

        # every entry of the working directory takes a line of its own, the
        # directory among them being marked as one
        self.assertEqual("file.txt" in listing, True)
        self.assertEqual("folder" in listing, True)
        self.assertEqual(listing.count("\r\n"), 2)
        self.assertEqual(listing.startswith("d") or "\r\nd" in listing, True)

    def test__list_missing(self):
        self.connection.cwd = "/missing"

        # a working directory that is not there has nothing to be listed, so
        # an empty listing is what comes back instead of raising
        self.assertEqual(self.connection._list(), "")

    def test__to_unix(self):
        os.makedirs(os.path.join(self.base, "folder"))
        mode = os.stat(os.path.join(self.base, "folder"))

        # a directory is marked as one, the rest of the report being the
        # permissions of it rendered the way the protocol expects
        self.assertEqual(self.connection._to_unix(mode)[0], "d")
        self.assertEqual(len(self.connection._to_unix(mode)), 10)

        path = self._store("file.txt", b"")
        mode = os.stat(path)

        self.assertEqual(self.connection._to_unix(mode)[0], "-")

    def test__get_path(self):
        # with nothing extra the working directory is what the path resolves
        # to, taken under the root of the service
        self.assertEqual(self.connection._get_path(), self.connection.base_path)
        self.assertEqual(
            self.connection._get_path("file.txt"),
            os.path.join(self.connection.base_path, "file.txt"),
        )

        # an absolute name is taken from the root of the service rather than
        # from the root of the file system
        self.assertEqual(
            self.connection._get_path("/file.txt"),
            os.path.join(self.connection.base_path, "file.txt"),
        )

    def test__get_path_escape(self):
        # a name that walks out of the root of the service must be refused,
        # or a peer would reach any file of the machine
        self.assertRaises(
            netius.SecurityError, self.connection._get_path, "../../../etc/passwd"
        )

        self.connection.cwd = "/folder"

        self.assertRaises(
            netius.SecurityError, self.connection._get_path, "../../../../etc/passwd"
        )

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return path


class FTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.base = tempfile.mkdtemp()
        self.server = netius.servers.FTPServer(
            base_path=self.base, level=logging.CRITICAL
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.server.cleanup()
        shutil.rmtree(self.base)

    def test_serve(self):
        with mock.patch.object(netius.ContainerServer, "serve") as serve:
            self.server.serve()

        # the service listens on the port that the protocol reserves for it
        self.assertEqual(serve.call_args[1]["port"], 21)

        # the host is the name that the service answers for rather than the
        # one that it binds to, so it is taken after the serving started
        self.assertEqual(self.server.host, "ftp.localhost")

    def test_on_connection_c(self):
        connection = mock.MagicMock()

        self.server.on_connection_c(connection)

        # a peer that reaches the service is greeted as soon as it is taken,
        # which is what starts the session of it
        self.assertEqual(connection.ready.called, True)

    def test_on_data(self):
        connection = mock.MagicMock()

        self.server.on_data(connection, b"NOOP\r\n")

        # what arrives from a peer is given to the parser of the connection,
        # which is the one that takes the commands apart
        self.assertEqual(connection.parse.call_args[0][0], b"NOOP\r\n")

    def test_on_serve(self):
        with mock.patch.object(
            self.server,
            "get_env",
            side_effect=lambda name, default, **kwargs: {
                "BASE_PATH": "/other",
                "AUTH": "dummy",
            }.get(name, default),
        ):
            self.server.env = True
            self.server.on_serve()

        # with an environment to read from, the root of the file service is
        # the one that it names
        self.assertEqual(self.server.base_path, "/other")

    def test_build_connection(self):
        _socket = socket.socket()
        try:
            connection = self.server.build_connection(_socket, ("host.domain", 8080))

            # the connection that the service builds carries the root and the
            # host that the service answers for
            self.assertEqual(isinstance(connection, ftp.FTPConnection), True)
            self.assertEqual(connection.base_path, os.path.abspath(self.base))
            self.assertEqual(connection.host, self.server.host)
        finally:
            _socket.close()
