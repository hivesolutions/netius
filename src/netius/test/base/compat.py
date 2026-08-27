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

import sys
import socket
import unittest

import netius

from netius.base import compat
from netius.base import errors
from netius.base import legacy
from netius.base import asynchronous

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class CompatLoopTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.loop = netius.Base()
        self.compat = compat.CompatLoop(self.loop)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.loop.close()

    def test__getattr__(self):
        # anything that the compatibility layer does not implement is
        # searched for in the loop that it wraps
        self.assertEqual(self.compat.poll_name, self.loop.poll_name)

        # an attribute that neither of them provides must raise, otherwise
        # a missing implementation would be silently ignored
        self.assertRaises(AttributeError, lambda: self.compat.missing)

    def test_time(self):
        result = self.compat.time()

        self.assertEqual(isinstance(result, float), True)

    def test_call_soon(self):
        handle = self.compat.call_soon(lambda: None)

        # a call for the next tick is scheduled with a negative target so
        # that it takes priority over the operations already in the queue
        self.assertEqual(isinstance(handle, asynchronous.Handle), True)
        self.assertEqual(len(self.loop._delayed), 1)
        self.assertEqual(self.loop._delayed[0][0], -1)

    def test_call_soon_arguments(self):
        received = []
        self.compat.call_soon(lambda *args: received.append(args), 1, 2)

        # the arguments are captured by the closure built around the
        # callback, so that they reach it once it's finally called
        self.loop._delayed[0][2]()

        self.assertEqual(received, [(1, 2)])

    def test_call_soon_threadsafe(self):
        self.loop.tid = -1
        handle = self.compat.call_soon_threadsafe(lambda: None)

        # a call made from a thread other than the loop one lands in the
        # next list, being merged into the queue on the following tick
        self.assertEqual(len(self.loop._delayed_n), 1)
        self.assertEqual(len(self.loop._delayed), 0)

        # the safe insertion has no callable tuple to hold on to, so the
        # handle it yields is not able to cancel the operation
        self.assertEqual(handle._callable_t, None)

        handle.cancel()

        self.assertEqual(len(self.loop._delayed_n), 1)

    def test_call_at(self):
        self.compat.call_at(self.compat.time() + 60, lambda: None)

        # an absolute time is converted into the delay that separates it
        # from the present, as that's what the loop expects
        self.assertEqual(self.loop._delayed[0][0] > self.compat.time(), True)

    def test_call_later(self):
        handle = self.compat.call_later(60, lambda: None)

        self.assertEqual(isinstance(handle, asynchronous.Handle), True)
        self.assertEqual(self.loop._delayed[0][0] > self.compat.time(), True)

    def test_create_future(self):
        future = self.compat.create_future()

        self.assertEqual(future.done(), False)

    def test_create_task(self):
        task = self.compat.create_task(self._coroutine())

        # the task is built by the currently configured factory, so that
        # it may be replaced by a compatible implementation
        self.assertEqual(isinstance(task, asynchronous.Task), True)

    def test_getaddrinfo(self):
        # the coroutine is driven by hand instead of through the loop, as
        # the driving helper binds a future of its own to the global loop,
        # which is not the one being run and would never complete it
        coroutine = self.compat.getaddrinfo("127.0.0.1", 80)
        future = next(coroutine)

        self.assertEqual(future.done(), False)

        # the resolution is already done by then, the result of it only
        # reaches the future once the delayed operation is run
        self.loop._delays()

        self.assertEqual(future.done(), True)

        result = future.result()

        self.assertEqual(len(result) > 0, True)
        self.assertEqual(result[0][0], socket.AF_INET)

    def test_getnameinfo(self):
        # the reverse resolution is not implemented and, as the underlying
        # method is not a generator, it announces itself right away instead
        # of only doing so once the coroutine is finally run
        self.assertRaises(errors.NotImplemented, self.compat.getnameinfo, ())

    def test_run_until_complete(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")
        if compat.asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        current = []
        coroutine = self._coroutine()

        def run_coroutine(future):
            current.append(self.compat._current_tasks.get(self.compat, None))
            return "result"

        with mock.patch.object(self.loop, "run_coroutine", run_coroutine):
            result = self.compat.run_until_complete(coroutine)

        # the coroutine is registered as the currently running task while
        # it runs, and the registration is released once it's done
        self.assertEqual(result, "result")
        self.assertEqual(current, [coroutine])
        self.assertEqual(self.compat._current_tasks.get(self.compat, None), None)

    def test_run_forever(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.loop, "run_forever") as run_forever:
            self.compat.run_forever()

        self.assertEqual(run_forever.call_count, 1)

    def test_run_in_executor(self):
        if compat.asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        result = self.compat.run_in_executor(None, lambda: None)

        # the wrapper that makes the coroutine awaitable is only part of the
        # newer implementation, the older one yields a plain generator
        self.assertEqual(isinstance(result, asynchronous.AwaitWrapper), True)

    def test_stop(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        # the stopping of an asyncio loop is a pause under netius, as the
        # loop is meant to be resumable instead of being torn down
        with mock.patch.object(self.loop, "pause") as pause:
            self.compat.stop()

        self.assertEqual(pause.call_count, 1)

    def test_close(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        with mock.patch.object(self.loop, "close") as close:
            self.compat.close()

        self.assertEqual(close.call_count, 1)

    def test_get_exception_handler(self):
        # the default handler is the one in place until a custom one has
        # been set by the code that drives the loop
        self.assertEqual(
            self.compat.get_exception_handler(), self.compat._default_handler
        )

    def test_set_exception_handler(self):
        handler = lambda context: None
        self.compat.set_exception_handler(handler)

        self.assertEqual(self.compat.get_exception_handler(), handler)

    def test_default_exception_handler(self):
        buffer = legacy.StringIO()
        stderr = sys.stderr
        sys.stderr = buffer
        try:
            self.compat.default_exception_handler(dict(message="Broken"))
        finally:
            sys.stderr = stderr

        # the default handling stays reachable even once a custom handler
        # has taken its place, as the report of it may still be wanted
        self.assertEqual(buffer.getvalue(), "Broken\n")

    def test_call_exception_handler(self):
        received = []
        self.compat.set_exception_handler(lambda context: received.append(context))

        self.compat.call_exception_handler(dict(message="Broken"))

        self.assertEqual(received, [dict(message="Broken")])

    def test_call_exception_handler_unset(self):
        self.compat.set_exception_handler(None)

        # with no handler in place the context is dropped, as there's no
        # sensible destination left for it
        self.assertEqual(
            self.compat.call_exception_handler(dict(message="Broken")), None
        )

    def test_get_debug(self):
        self.assertEqual(self.compat.get_debug(), self.loop.is_debug())

    def test_set_debug(self):
        # the debug mode of an asyncio loop has no counterpart, so setting
        # it must be a no operation instead of an error
        self.compat.set_debug(True)

        self.assertEqual(self.compat.get_debug(), self.loop.is_debug())

    def test_set_default_executor(self):
        executor = object()
        self.compat.set_default_executor(executor)

        self.assertEqual(self.compat._executor, executor)

    def test_get_task_factory(self):
        self.assertEqual(self.compat.get_task_factory(), asynchronous.Task)

    def test_set_task_factory(self):
        factory = lambda future: None
        self.compat.set_task_factory(factory)

        self.assertEqual(self.compat.get_task_factory(), factory)

    def test_is_running(self):
        self.assertEqual(self.compat.is_running(), self.loop.is_running())

    def test_is_closed(self):
        self.assertEqual(self.compat.is_closed(), self.loop.is_stopped())

    def test__set_current_task(self):
        if compat.asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        task = object()
        self.compat._set_current_task(task)

        self.assertEqual(self.compat._current_tasks.get(self.compat, None), task)

        self.compat._unset_current_task()

        self.assertEqual(self.compat._current_tasks.get(self.compat, None), None)

    def test__set_current_task_no_asyncio(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")
        if compat.asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        # the tracking of the running task only makes sense while asyncio
        # is around, as it's the global state of asyncio that is updated
        with mock.patch.object(asynchronous, "get_asyncio", return_value=None):
            self.compat._set_current_task(object())
            self.compat._unset_current_task()

        self.assertEqual(self.compat._current_tasks.get(self.compat, None), None)

    def test__unset_current_task_unset(self):
        if compat.asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        # the releasing of a task that was never registered must be a no
        # operation, as the registration is a best effort one
        self.compat._unset_current_task()

        self.assertEqual(self.compat._current_tasks.get(self.compat, None), None)

    def test__call_delay(self):
        handle = self.compat._call_delay(lambda: None, (), timeout=60)

        self.assertEqual(isinstance(handle, asynchronous.Handle), True)
        self.assertEqual(len(self.loop._delayed), 1)

        # the handle is the only way back to the scheduled operation, so
        # cancelling it must take the operation out of the queue
        handle.cancel()

        self.assertEqual(self.loop._delayed[0][4][0], False)

    def test__default_handler(self):
        buffer = legacy.StringIO()
        stderr = sys.stderr
        sys.stderr = buffer
        try:
            self.compat._default_handler(dict(message="Broken", detail="extra"))
        finally:
            sys.stderr = stderr

        # the message leads the report and the remaining context follows
        # it, one key per line, so that it's readable in a terminal
        self.assertEqual(buffer.getvalue(), "Broken\ndetail: extra\n")

    def test__thread_id(self):
        self.assertEqual(self.compat._thread_id, self.loop.tid)

    def _coroutine(self):
        future = self.compat.create_future()
        self.loop.delay(lambda: future.set_result(None), immediately=True)
        yield future
