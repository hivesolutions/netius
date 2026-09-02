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
import struct
import logging
import tempfile
import unittest

import netius
import netius.common
import netius.servers

try:
    import unittest.mock as mock
except ImportError:
    mock = None

NAME = "file.txt"

MODE = "octet"

ADDRESS = ("127.0.0.1", 1234)


class TFTPSessionTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.server = netius.servers.TFTPServer(
            base_path=self.base, level=logging.CRITICAL
        )
        self.sessions = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for session in self.sessions:
            session.close()
        self.server.cleanup()
        shutil.rmtree(self.base)

    def test_close(self):
        self._store(NAME, b"contents")
        session = self._make_session(NAME)
        session.next()
        file = session.file

        session.close()

        # the closing of a session releases the file that it was reading, as
        # holding it would keep the descriptor of it open
        self.assertEqual(file.closed, True)
        self.assertEqual(session.file, None)

    def test_reset(self):
        session = self._make_session(NAME)
        session.completed = True
        session.sequence = 3

        session.reset()

        # a session that is reset carries none of the state of the transfer
        # that came before it, so that it may be used again
        self.assertEqual(session.name, None)
        self.assertEqual(session.mode, None)
        self.assertEqual(session.file, None)
        self.assertEqual(session.completed, False)
        self.assertEqual(session.sequence, 0)

    def test_next(self):
        self._store(NAME, b"0" * 1024)
        session = self._make_session(NAME)

        data = session.next()
        type, sequence = struct.unpack("!HH", data[:4])

        # the block that is given back is led by the header that names the
        # kind of it and the sequence that it takes, which starts at one
        self.assertEqual(type, netius.common.DATA_TFTP)
        self.assertEqual(sequence, 1)
        self.assertEqual(len(data[4:]), 512)
        self.assertEqual(session.completed, False)

        data = session.next()

        # the reading goes on from where it stopped, the sequence of the
        # block that follows being the one after it
        self.assertEqual(struct.unpack("!H", data[2:4])[0], 2)
        self.assertEqual(session.completed, False)

        data = session.next()

        # a block that is shorter than the size that was asked for is the
        # last one of the transfer, which is what completes it
        self.assertEqual(len(data[4:]), 0)
        self.assertEqual(session.completed, True)

        # once the transfer is complete there is nothing left to be given
        # back, whatever is asked of the session
        self.assertEqual(session.next(), None)

    def test_next_increment(self):
        self._store(NAME, b"0" * 16)
        session = self._make_session(NAME)

        data = session.next(increment=False)

        # a block that is read without incrementing keeps the sequence where
        # it was, so the one that names it is the current one
        self.assertEqual(struct.unpack("!H", data[2:4])[0], 0)
        self.assertEqual(session.sequence, 0)

    def test_ack(self):
        self._store(NAME, b"0" * 1024)
        session = self._make_session(NAME)

        # an acknowledge that arrives before anything was sent has no block
        # of its own to answer with
        self.assertEqual(session.ack(), None)

        session.next()
        data = session.ack()

        # once the transfer is under way the acknowledge is answered with the
        # block that follows the one that was taken
        self.assertEqual(struct.unpack("!H", data[2:4])[0], 2)

    def test_increment(self):
        session = self._make_session(NAME)

        session.increment()
        session.increment()

        # the sequence of a session walks one at a time, which is what names
        # the blocks of the transfer in order
        self.assertEqual(session.sequence, 2)

    def test_get_info(self):
        session = self._make_session(NAME)
        session.sequence = 2

        info = session.get_info()

        # the report of a session names the file that it serves and where the
        # transfer of it currently stands
        self.assertEqual("name      := %s" % NAME in info, True)
        self.assertEqual("mode      := %s" % MODE in info, True)
        self.assertEqual("completed := 0" in info, True)
        self.assertEqual("sequence  := 2" in info, True)

    def test_print_info(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        session = self._make_session(NAME)

        with mock.patch("sys.stdout", netius.legacy.StringIO()) as stdout:
            session.print_info()

        # what is printed is the report of the session, so the name of the
        # file that it serves has to be part of it
        self.assertEqual("name      := %s" % NAME in stdout.getvalue(), True)

    def test__get_file(self):
        self._store(NAME, b"contents")
        session = self._make_session("/" + NAME)

        file = session._get_file()

        # a name that is led by a separator is taken as a relative one, or the
        # joining of it would step out of the root of the service
        self.assertEqual(file.read(), b"contents")

        # the file of a session is opened once, the same one being given back
        # for as long as the transfer lasts
        self.assertEqual(session._get_file(), file)

    def test__get_file_absolute(self):
        path = self._store(NAME, b"contents")
        session = self._make_session(path)

        file = session._get_file(allow_absolute=True)

        # under an absolute name the one of the session is taken whole, which
        # used to leave the name unbound and raise
        self.assertEqual(file.read(), b"contents")

    def test__get_file_escape(self):
        outside = os.path.join(os.path.dirname(self.base), "outside.txt")
        file = open(outside, "wb")
        try:
            file.write(b"secret")
        finally:
            file.close()

        session = self._make_session("../outside.txt")

        try:
            # the name of a read request arrives from the wire, so one that
            # walks out of the root must be refused rather than served, or a
            # peer would read any file of the machine
            self.assertRaises(netius.SecurityError, session._get_file)
        finally:
            os.remove(outside)

    def test__get_file_sibling(self):
        parent = os.path.dirname(self.base)
        sibling = os.path.basename(self.base) + "-backup"
        os.makedirs(os.path.join(parent, sibling))

        session = self._make_session("../%s/secret.txt" % sibling)

        try:
            # a directory whose name only starts like the root of the service
            # is not under it, so reaching into it must be refused as well
            self.assertRaises(netius.SecurityError, session._get_file)
        finally:
            shutil.rmtree(os.path.join(parent, sibling))

    def _make_session(self, name):
        # builds a session of the service and keeps it, so that the file it
        # reads is released once the case is over
        session = netius.servers.tftp.TFTPSession(self.server, name=name, mode=MODE)
        self.sessions.append(session)
        return session

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return path


class TFTPRequestTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()
        self.server = netius.servers.TFTPServer(
            base_path=self.base, level=logging.CRITICAL
        )
        self.session = netius.servers.tftp.TFTPSession(self.server)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.session.close()
        self.server.cleanup()
        shutil.rmtree(self.base)

    def test_generate(self):
        netius.servers.tftp.TFTPRequest.generate()

        # the parsers are built once and kept in the class, one of them for
        # each of the operations that the protocol names
        self.assertEqual(
            netius.servers.tftp.TFTPRequest.parsers_l,
            len(netius.servers.tftp.TFTPRequest.parsers_m),
        )
        self.assertEqual(netius.servers.tftp.TFTPRequest.parsers_l, 5)

    def test_get_info(self):
        request = netius.servers.tftp.TFTPRequest(build_rrq(), self.session)
        request.parse()

        info = request.get_info()

        # the report of a request names the operation of it and carries the
        # one of the session that it runs under
        self.assertEqual("op        := %d" % netius.common.RRQ_TFTP in info, True)
        self.assertEqual("name      := %s" % NAME in info, True)

    def test_print_info(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        request = netius.servers.tftp.TFTPRequest(build_rrq(), self.session)
        request.parse()

        with mock.patch("sys.stdout", netius.legacy.StringIO()) as stdout:
            request.print_info()

        # what is printed is the report of the request, the operation of it
        # being what leads the report
        self.assertEqual(
            "op        := %d" % netius.common.RRQ_TFTP in stdout.getvalue(), True
        )

    def test_parse(self):
        request = netius.servers.tftp.TFTPRequest(build_rrq(), self.session)
        request.parse()

        # the reading of a request names the file and the mode that the peer
        # asked for, both of them landing in the session
        self.assertEqual(request.op, netius.common.RRQ_TFTP)
        self.assertEqual(self.session.name, NAME)
        self.assertEqual(self.session.mode, MODE)

    def test_parse_unsupported(self):
        for op in (
            netius.common.WRQ_TFTP,
            netius.common.DATA_TFTP,
            netius.common.ERROR_TFTP,
        ):
            request = netius.servers.tftp.TFTPRequest(
                struct.pack("!H", op), self.session
            )

            # the writing of a file and the two operations that belong to the
            # peer are not served, so reading one of them must refuse it
            self.assertRaises(netius.NotImplemented, request.parse)

    def test_get_type(self):
        request = netius.servers.tftp.TFTPRequest(build_rrq(), self.session)
        request.parse()

        # the kind of a request is the operation of it, named by the label
        # that the protocol gives it
        self.assertEqual(request.get_type(), netius.common.RRQ_TFTP)
        self.assertEqual(request.get_type_s(), "rrq")

        request.op = 0xFF

        # an operation that the protocol does not name has no label of its
        # own to be reported under
        self.assertEqual(request.get_type_s(), None)

    def test_response(self):
        self._store(NAME, b"0" * 1024)
        request = netius.servers.tftp.TFTPRequest(build_rrq(), self.session)
        request.parse()

        data = request.response()

        # a request to read is answered with the first block of the file, as
        # there is nothing that came before it
        self.assertEqual(struct.unpack("!H", data[2:4])[0], 1)

        request = netius.servers.tftp.TFTPRequest(build_ack(1), self.session)
        request.parse()

        data = request.response()

        # an acknowledge is answered with the block that follows the one that
        # it acknowledges, which walks the transfer forward
        self.assertEqual(struct.unpack("!H", data[2:4])[0], 2)

    def test__str(self):
        value, remaining = netius.servers.tftp.TFTPRequest._str(b"name\x00rest")

        # the value is the part that comes before the null and the rest of the
        # sequence is what is left to be read
        self.assertEqual(value, "name")
        self.assertEqual(remaining, b"rest")

        # a sequence that carries no null has no value in it to be taken, so
        # the reading of it cannot be completed
        self.assertRaises(
            ValueError, netius.servers.tftp.TFTPRequest._str, b"no null here"
        )

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return path


class TFTPServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        self.base = tempfile.mkdtemp()
        self.server = netius.servers.TFTPServer(
            base_path=self.base, level=logging.CRITICAL
        )

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for session in netius.legacy.itervalues(self.server.sessions):
            session.close()
        self.server.cleanup()
        shutil.rmtree(self.base)

    def test_serve(self):
        with mock.patch.object(netius.DatagramServer, "serve") as serve:
            self.server.serve()

        # the service listens on the port that the protocol reserves for it
        # unless another one is asked for
        self.assertEqual(serve.call_args[1]["port"], 69)

    def test_on_data(self):
        self._store(NAME, b"0" * 1024)

        with mock.patch.object(self.server, "send") as send:
            self.server.on_data(ADDRESS, build_rrq())

        # a request to read opens a session for the peer and answers it with
        # the first block of the file that was asked for
        self.assertEqual(ADDRESS in self.server.sessions, True)
        self.assertEqual(struct.unpack("!H", send.call_args[0][0][2:4])[0], 1)

        with mock.patch.object(self.server, "send") as send:
            self.server.on_data(ADDRESS, build_ack(1))

        # the session of the peer is the one that is reused, so the block that
        # answers the acknowledge is the one that follows
        self.assertEqual(struct.unpack("!H", send.call_args[0][0][2:4])[0], 2)

    def test_on_data_error(self):
        with mock.patch.object(self.server, "send") as send:
            self.server.on_data(ADDRESS, struct.pack("!H", netius.common.WRQ_TFTP))

        # an operation that is not served is reported back to the peer as an
        # error of the protocol instead of breaking the service
        data = send.call_args[0][0]
        self.assertEqual(struct.unpack("!H", data[:2])[0], netius.common.ERROR_TFTP)

    def test_on_serve(self):
        with mock.patch.object(
            self.server, "get_env", return_value="/other"
        ) as get_env:
            self.server.env = True
            self.server.on_serve()

        # with an environment to read from, the root of the file service is
        # the one that it names
        self.assertEqual(get_env.call_args[0][0], "BASE_PATH")
        self.assertEqual(self.server.base_path, "/other")

        self.server.env = False
        self.server.base_path = self.base

        self.server.on_serve()

        # without one the root stays the one that the service was built with
        self.assertEqual(self.server.base_path, self.base)

    def test_on_data_tftp(self):
        request = mock.MagicMock()
        request.get_type.return_value = netius.common.WRQ_TFTP

        try:
            self.server.on_data_tftp(ADDRESS, request)
        except netius.NetiusError as exception:
            # the operation that was refused is named in the message of the
            # error, which reaches the peer as it reads
            self.assertEqual(
                str(exception),
                "Invalid operation type '%d'" % netius.common.WRQ_TFTP,
            )
        else:
            self.fail("The operation should not have been served")

        request = mock.MagicMock()
        request.get_type.return_value = netius.common.ACK_TFTP
        request.response.return_value = None

        with mock.patch.object(self.server, "send") as send:
            self.server.on_data_tftp(ADDRESS, request)

        # a request that has nothing to answer with (eg: a transfer that is
        # complete) leaves the peer alone instead of sending an empty packet
        self.assertEqual(send.called, False)

    def test_on_error_tftp(self):
        with mock.patch.object(self.server, "send") as send:
            self.server.on_error_tftp(ADDRESS, netius.NetiusError("problem"))

        data = send.call_args[0][0]
        type, code = struct.unpack("!HH", data[:4])

        # the packet of an error names the kind of it and carries the message
        # that describes it, closed by the null that ends it
        self.assertEqual(type, netius.common.ERROR_TFTP)
        self.assertEqual(code, 0)
        self.assertEqual(data[4:], b"problem\x00")

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
        return path


def build_rrq(name=NAME, mode=MODE):
    # builds a request to read as it would arrive from the wire, with the name
    # of the file and the mode of the transfer closed by nulls
    header = struct.pack("!H", netius.common.RRQ_TFTP)
    return (
        header
        + netius.legacy.bytes(name)
        + b"\x00"
        + netius.legacy.bytes(mode)
        + b"\x00"
    )


def build_ack(sequence):
    # builds the acknowledge of a block, which is only the header that names
    # the operation and the sequence that it answers
    return struct.pack("!HH", netius.common.ACK_TFTP, sequence)
