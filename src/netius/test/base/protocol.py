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

import unittest

import netius

from netius.base import protocol

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ProtocolTest(unittest.TestCase):

    def test_info_dict(self):
        _protocol = protocol.Protocol()

        # a protocol that serves no transport has nothing to describe, so an
        # empty description is what it gives back
        self.assertEqual(_protocol.info_dict(), dict())

    def test_info_dict_transport(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()
        _protocol._transport = mock.MagicMock()

        info = _protocol.info_dict(full=True)

        # the description is the one of the transport that it serves, the
        # depth of it travelling with the request
        self.assertEqual(info, _protocol._transport.info_dict.return_value)
        self.assertEqual(_protocol._transport.info_dict.call_args[1]["full"], True)

    def test_loop_set(self):
        _protocol = protocol.Protocol()
        loop = netius.Base()
        try:
            received = []
            _protocol.bind("loop_set", lambda p: received.append("set"))
            _protocol.bind("loop_unset", lambda p: received.append("unset"))

            _protocol.loop_set(loop)

            # the binding to a loop is announced, as the operations that were
            # waiting on one may only run once there is one
            self.assertEqual(_protocol.loop(), loop)
            self.assertEqual(received, ["set"])

            _protocol.loop_unset()

            # and so is the releasing of it, the protocol being left with no
            # loop to schedule anything on
            self.assertEqual(_protocol.loop(), None)
            self.assertEqual(received, ["set", "unset"])
        finally:
            loop.close()

    def test_pause_writing(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()

        _protocol.pause_writing()

        # a protocol that was told to stop writing holds whatever it is given
        # until it is told that it may write again
        self.assertEqual(_protocol._writing, False)

        with mock.patch.object(_protocol, "_flush_callbacks") as flush_callbacks:
            with mock.patch.object(_protocol, "_flush_send") as flush_send:
                _protocol.resume_writing()

        # once it may write again both what was held and the callbacks that
        # were waiting on it are flushed
        self.assertEqual(_protocol._writing, True)
        self.assertEqual(flush_callbacks.called, True)
        self.assertEqual(flush_send.called, True)

    def test_delay(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        received = []
        _protocol = protocol.Protocol()

        _protocol.delay(lambda: received.append(1))

        # a protocol with no loop has nowhere to defer to, so the callable is
        # run right away instead of being dropped
        self.assertEqual(received, [1])

        loop = netius.Base()
        try:
            _protocol.loop_set(loop)

            _protocol.delay(lambda: received.append(2))

            # one that has a loop of the infra-structure defers into it, and
            # a call with no timeout is one for the next tick
            self.assertEqual(received, [1])
            self.assertEqual(len(loop._delayed), 1)
            self.assertEqual(loop._delayed[0][0], -1)

            _protocol.delay(lambda: received.append(3), timeout=10)

            self.assertEqual(len(loop._delayed), 2)
        finally:
            loop.close()

    def test_delay_compat(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()
        loop = mock.MagicMock(spec=["call_soon", "call_later"])
        _protocol._loop = loop

        callable = lambda: None

        _protocol.delay(callable)

        # a loop that is not one of the infra-structure is driven through the
        # names of the specification instead
        self.assertEqual(loop.call_soon.call_args[0][0], callable)

        _protocol.delay(callable, timeout=10)

        self.assertEqual(loop.call_later.call_args[0], (10, callable))

    def test_unpend(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()

        # a protocol with no loop has nothing scheduled to be cancelled, and
        # asking for it must not raise
        self.assertEqual(_protocol.unpend(None), None)

        loop = netius.Base()
        try:
            _protocol.loop_set(loop)
            callable_t = loop.delay(lambda: None)

            _protocol.unpend(callable_t)

            # the cancelling reaches the loop of the infra-structure, which is
            # the one that holds the queue of the delayed operations
            self.assertEqual(loop._cancelled, 1)
        finally:
            loop.close()

        handle = mock.MagicMock(spec=["cancel"])
        _protocol._loop = mock.MagicMock(spec=["call_soon"])

        _protocol.unpend(handle)

        # under a loop of the specification it is the handle itself that
        # carries the cancelling of the operation
        self.assertEqual(handle.cancel.called, True)

    def test_logging(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()
        loop = netius.Base()
        try:
            _protocol.loop_set(loop)

            # every level is delegated to the loop that the protocol is bound
            # to, which is the one that owns the logger
            for name in ("trace", "debug", "info", "warning", "error", "critical"):
                with mock.patch.object(loop, name) as method:
                    getattr(_protocol, name)("message")

                self.assertEqual(method.call_args[0][0], "message")
        finally:
            loop.close()

    def test_traced(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()

        with mock.patch.object(_protocol, "is_trace", return_value=False):
            with mock.patch.object(_protocol, "trace") as trace:
                _protocol.traced("message")

        # outside of the tracing level nothing at all is gathered, as the
        # building of the report is not free
        self.assertEqual(trace.called, False)

        with mock.patch.object(_protocol, "is_trace", return_value=True):
            with mock.patch.object(_protocol, "trace") as trace:
                _protocol.traced("message %d", 1)

        # the name of the caller is what the report leads with, so that the
        # path taken through the protocol may be followed
        self.assertEqual(trace.call_args[0][1], "ProtocolTest:test_traced()")
        self.assertEqual(trace.call_args[0][3], 1)

        with mock.patch.object(_protocol, "is_trace", return_value=True):
            with mock.patch.object(_protocol, "trace") as trace:
                _protocol.traced()

        # a report with no message of its own still names both the caller and
        # the protocol that it belongs to
        self.assertEqual(trace.call_args[0][1], "ProtocolTest:test_traced()")

    def test_is_devel(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()

        # a protocol with no loop cannot tell the mode of the environment, so
        # it settles for the safest of the answers
        self.assertEqual(_protocol.is_devel(), False)

        _protocol._loop = mock.MagicMock(spec=["call_soon"])

        # and so does one whose loop is not of the infra-structure, as it is
        # the one that carries the notion of the mode
        self.assertEqual(_protocol.is_devel(), False)

        loop = netius.Base()
        try:
            _protocol.loop_set(loop)

            with mock.patch.object(loop, "is_devel", return_value=True):
                self.assertEqual(_protocol.is_devel(), True)
        finally:
            loop.close()

    def test__flush_callbacks(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        received = []
        _protocol = protocol.Protocol()
        _protocol._transport = mock.MagicMock()
        _protocol._callbacks.append(lambda transport: received.append(transport))

        _protocol._flush_callbacks()

        # the callbacks that were waiting are run with the transport of the
        # protocol, and the queue of them is left empty
        self.assertEqual(received, [_protocol._transport])
        self.assertEqual(_protocol._callbacks, [])

    def test__flush_send(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()
        _protocol._delay_send(b"hello")
        _protocol._delay_send(b"world", address=("1.2.3.4", 1234))

        with mock.patch.object(_protocol, "send", create=True) as send:
            _protocol._flush_send()

        # what was held while the writing was paused goes out in the order it
        # was given, the address travelling with the one that named it
        self.assertEqual(send.call_args_list[0][0][0], b"hello")
        self.assertEqual(send.call_args_list[1][0], (b"world", ("1.2.3.4", 1234)))
        self.assertEqual(_protocol._delayed, [])

    def test__flush_send_paused(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        _protocol = protocol.Protocol()
        _protocol._delay_send(b"hello")
        _protocol.pause_writing()

        with mock.patch.object(_protocol, "send", create=True) as send:
            _protocol._flush_send()

        # a protocol that was told to stop writing keeps what it holds, so
        # that the back-pressure of the transport is respected
        self.assertEqual(send.called, False)
        self.assertEqual(len(_protocol._delayed), 1)
