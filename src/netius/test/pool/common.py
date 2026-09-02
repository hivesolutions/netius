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

import time
import unittest

import netius
import netius.pool

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class EventPoolTest(unittest.TestCase):

    def test_pop_all(self):
        pool = netius.pool.EventPool()
        pool.push_event(("first", 1))
        pool.push_event(("second", 2))

        events = pool.pop_all()

        # every event that was queued comes back in the order it was pushed,
        # and the queue is left empty behind them
        self.assertEqual(events, [("first", 1), ("second", 2)])
        self.assertEqual(pool.events, [])

        # a pop over an empty queue gives nothing back and asks nothing of
        # the notification, as there is nothing to be undone
        self.assertEqual(pool.pop_all(denotify=True), [])

    def test_pop_all_denotify(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        pool = netius.pool.EventPool()
        try:
            pool.eventfd()
            pool.push_event(("first", 1))

            with mock.patch.object(pool, "denotify") as denotify:
                pool.pop_all(denotify=True)

            # the taking of the events undoes the notification, so that a loop
            # that waits on the file is not woken up for ones already handled
            self.assertEqual(denotify.called, True)

            with mock.patch.object(pool, "denotify") as denotify:
                pool.pop_all(denotify=True)

            # with nothing queued there is no notification to be undone, so
            # the file is left exactly as it is
            self.assertEqual(denotify.called, False)
        finally:
            pool.stop(join=False)

    def test_eventfd(self):
        pool = netius.pool.EventPool()
        try:
            eventfd = pool.eventfd()

            # the file is built once and kept, as the loop registers it in the
            # poll and would not notice a second one
            self.assertEqual(pool.eventfd(), eventfd)
            self.assertNotEqual(eventfd.fileno(), None)
            self.assertEqual(eventfd.fileno(), eventfd.rfileno())
        finally:
            pool.stop(join=False)

    def test_notify_unset(self):
        pool = netius.pool.EventPool()

        # a pool that never built a file has nothing to notify, and asking
        # for it must not raise
        self.assertEqual(pool.notify(), None)
        self.assertEqual(pool.denotify(), None)

    def test_stop(self):
        pool = netius.pool.EventPool()
        pool.eventfd()

        pool.stop(join=False)

        # the stopping releases the file, so that the descriptor of it is not
        # left behind by a pool that is no longer running
        self.assertEqual(pool._eventfd, None)

        # and asking for it a second time is a no operation, there being no
        # file left to be released
        self.assertEqual(pool.stop(join=False), None)

    def test_event(self):
        pool = netius.pool.EventPool()
        pool.push_event(("test", 1))

        self.assertNotEqual(pool.events, [])
        self.assertEqual(pool.pop_event(), ("test", 1))


class ThreadPoolTest(unittest.TestCase):

    def test_build(self):
        pool = netius.pool.ThreadPool(count=2)
        pool.build()

        # the threads of the pool are built once, so that asking for them a
        # second time does not double the count of them
        self.assertEqual(len(pool.instances), 2)

        pool.build()

        self.assertEqual(len(pool.instances), 2)

    def test_push(self):
        pool = netius.pool.ThreadPool(count=1)

        # the queue is served in the order it was filled, which is what makes
        # the pool a fair one
        pool.push(("first",))
        pool.push(("second",))

        self.assertEqual(pool.peek(), ("first",))
        self.assertEqual(pool.pop(), ("first",))
        self.assertEqual(pool.pop(), ("second",))

        # an empty queue names no work at all, instead of the peeking of it
        # raising
        self.assertEqual(pool.peek(), None)

    def test_execute(self):
        received = []
        pool = netius.pool.ThreadPool(count=1)
        thread = netius.pool.Thread(0, owner=pool)

        thread.execute((netius.pool.common.CALLABLE_WORK, lambda: received.append(1)))

        # a unit of work that names a callable is run as it is, which is the
        # only kind that the pool knows about
        self.assertEqual(received, [1])

        # one of a kind that it does not know cannot be run, so it is refused
        # instead of being dropped quietly
        self.assertRaises(netius.NotImplemented, thread.execute, (-1,))

    def test_start_stop(self):
        received = []
        pool = netius.pool.ThreadPool(count=2)
        pool.start()
        try:
            pool.push_callable(lambda: received.append(1))

            # the work that was queued is run by one of the threads, which is
            # what the starting of the pool is for
            for _index in range(100):
                if received:
                    break
                time.sleep(0.01)

            self.assertEqual(received, [1])
        finally:
            pool.stop()

        # every thread of the pool is joined by the stopping of it, so that
        # none of them is left behind
        for instance in pool.instances:
            self.assertEqual(instance.is_alive(), False)


class EventFileTest(unittest.TestCase):
    """
    Tests for the files that wake the loop up, each of which is
    the one picked on exactly one kind of platform, so that the
    ones that are not picked here are still exercised.
    """

    def test_unix(self):
        if not netius.pool.UnixEventFile.available():
            self.skipTest("Skipping test: the event file is unavailable")

        self._verify(netius.pool.UnixEventFile())

    def test_pipe(self):
        # the class is reached through the module as the package exports the
        # two other kinds of file but not this one
        cls = netius.pool.common.PipeEventFile

        if not cls.available():
            self.skipTest("Skipping test: the pipe is unavailable")

        self._verify(cls())

    def test_socket(self):
        self._verify(netius.pool.SocketEventFile())

    def test_socket_denotify_empty(self):
        eventfd = netius.pool.SocketEventFile()
        try:
            # a file that carries no notification has none to be undone, so
            # the reading of it is skipped and the loop is not blocked on it
            self.assertEqual(eventfd.denotify(), None)
            self.assertEqual(eventfd._count, 0)
        finally:
            eventfd.close()

    def _verify(self, eventfd):
        try:
            # the two ends of the file are named by descriptors of their own,
            # the reading one being the one the poll is told about
            self.assertNotEqual(eventfd.rfileno(), None)
            self.assertNotEqual(eventfd.wfileno(), None)
            self.assertEqual(eventfd.fileno(), eventfd.rfileno())
            self.assertEqual(eventfd.closed, False)

            eventfd.notify()
            eventfd.denotify()

            # what was written is taken back out, so that the loop is woken up
            # once for every notification and not once more, the count being
            # kept only by the kinds that do not have one of the kernel
            if hasattr(eventfd, "_count"):
                self.assertEqual(eventfd._count, 0)
        finally:
            eventfd.close()

        # a file that was closed says so, and writing to it is a no operation
        # rather than a failure
        self.assertEqual(eventfd.closed, True)
        self.assertEqual(eventfd._write(b"1"), None)
        self.assertEqual(eventfd._read(), None)
