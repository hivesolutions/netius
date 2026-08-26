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
import datetime
import unittest
import collections

import netius

from netius.base import conn
from netius.base import common
from netius.base import errors
from netius.base import asynchronous

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class BaseTest(unittest.TestCase):

    def test_patch_asyncio(self):
        asyncio = netius.get_asyncio()
        if asyncio == None:
            self.skipTest("Skipping test: asyncio unavailable")

        netius.Base.patch_asyncio()

        # the patching of the infra-structure is a one time operation and
        # the flag is the one that guards it from being run once again
        self.assertEqual(hasattr(asyncio, "_patched"), True)

        # an interpreter that does not provide the pure Python task has
        # nothing to be patched, so there's nothing to be verified
        if not hasattr(asyncio.tasks, "_PyTask"):
            return

        if netius.Base.is_py_task():
            self.assertEqual(asyncio.Task, asyncio.tasks._PyTask)
        else:
            # the global task class must be kept untouched, otherwise the
            # currently running task would no longer be reported by the
            # current task function, breaking the libraries that use it
            self.assertNotEqual(asyncio.Task, asyncio.tasks._PyTask)

    def test_is_py_task(self):
        asyncio = netius.get_asyncio()
        result = netius.Base.is_py_task()

        self.assertEqual(result in (True, False), True)

        if asyncio == None:
            self.assertEqual(result, False)
            return

        # the pure Python implementation of the task may only be used
        # while its bookkeeping of the currently running task is shared
        # with the accelerated one, which stops being the case under the
        # more recent versions of the interpreter
        if hasattr(asyncio.tasks, "_c_current_task"):
            self.assertEqual(result, sys.version_info < (3, 14))
        else:
            self.assertEqual(result, True)

    def test_call_safe(self):
        loop = netius.Base()
        try:
            result = loop.call_safe(
                lambda first, second=0: first + second, args=[1], kwargs=dict(second=2)
            )

            self.assertEqual(result, 3)
        finally:
            loop.close()

    def test_call_safe_error(self):
        loop = netius.Base()
        try:

            def raiser():
                raise RuntimeError("Safe error")

            # the exception raised by the callable is caught and logged, so
            # that the caller is never interrupted by it
            result = loop.call_safe(raiser)

            self.assertEqual(result, None)
        finally:
            loop.close()

    def test_wait_event(self):
        loop = netius.Base()
        try:
            received = []
            callable = lambda data: received.append(data)

            loop.wait_event(callable, name="event")

            self.assertEqual(loop._events["event"], [callable])

            # the notification of the event runs the complete set of binds
            # registered for it, handing them the payload of the event
            loop.notify("event", data="payload")
            loop._notifies()

            self.assertEqual(received, ["payload"])
        finally:
            loop.close()

    def test_wait_event_duplicate(self):
        loop = netius.Base()
        try:
            callable = lambda data: None

            # the same callable may only be bound once to an event, so that
            # a repeated wait operation is not accounted for twice
            loop.wait_event(callable, name="event")
            loop.wait_event(callable, name="event")

            self.assertEqual(len(loop._events["event"]), 1)
        finally:
            loop.close()

    def test_unwait_event(self):
        loop = netius.Base()
        try:
            callable = lambda data: None
            loop.wait_event(callable, name="event")

            loop.unwait_event(callable, name="event")

            # the event is dropped from the map once its last bind has been
            # removed, so that no empty sequences are kept around
            self.assertEqual("event" in loop._events, False)
        finally:
            loop.close()

    def test_unwait_event_remaining(self):
        loop = netius.Base()
        try:
            first = lambda data: None
            second = lambda data: None
            loop.wait_event(first, name="event")
            loop.wait_event(second, name="event")

            loop.unwait_event(first, name="event")

            self.assertEqual(loop._events["event"], [second])
        finally:
            loop.close()

    def test_unwait_event_unknown(self):
        loop = netius.Base()
        try:
            callable = lambda data: None
            loop.wait_event(callable, name="event")

            # neither an unknown event nor a callable that has never been
            # bound to it may raise, the operation is simply ignored
            loop.unwait_event(callable, name="unknown")
            loop.unwait_event(lambda data: None, name="event")

            self.assertEqual(loop._events["event"], [callable])
        finally:
            loop.close()

    def test_delay_immediately(self):
        loop = netius.Base()
        try:
            callable_t = loop.delay(lambda: None, immediately=True)

            # an immediate operation takes priority over the ones scheduled
            # for the next tick, by using a negative target time
            self.assertEqual(callable_t[0], -1)

            callable_t = loop.delay(lambda: None)

            self.assertEqual(callable_t[0], 0)
        finally:
            loop.close()

    def test_delay_verify(self):
        loop = netius.Base()
        try:
            callable = lambda: None
            loop.delay(callable, verify=True)

            # the verification of duplicates skips the insertion of a callable
            # that is already part of the delayed queue for the same target
            result = loop.delay(callable, verify=True)

            self.assertEqual(result, None)
            self.assertEqual(len(loop._delayed), 1)
        finally:
            loop.close()

    def test_delay_safe(self):
        loop = netius.Base()
        try:
            # a delay requested from a thread other than the main one must be
            # routed through the safe operation, landing in the next list
            loop.tid = -1
            result = loop.delay(lambda: None, timeout=60, safe=True)

            self.assertEqual(result, None)
            self.assertEqual(len(loop._delayed_n), 1)
            self.assertEqual(len(loop._delayed), 0)

            loop.delay_m()

            self.assertEqual(len(loop._delayed_n), 0)
            self.assertEqual(len(loop._delayed), 1)
        finally:
            loop.close()

    def test_delay_legacy(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # at exit time the legacy module may already have been collected
            # and the operation must be abandoned instead of raising
            with mock.patch.object(common, "legacy", None):
                result = loop.delay(lambda: None)

            self.assertEqual(result, None)
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test_interval_s(self):
        loop = netius.Base()
        try:
            fired = []
            loop.interval_s(lambda: fired.append("tick"), timeout=60, wakeup=False)
            loop.delay_m()

            self.assertEqual(len(loop._delayed), 1)

            # the wrapper schedules itself once again after every call, so
            # that the callable keeps being run at the requested interval
            loop._delayed[0][2]()

            self.assertEqual(fired, ["tick"])
            self.assertEqual(len(loop._delayed_n), 1)
        finally:
            loop.close()

    def test_unpend(self):
        loop = netius.Base()
        try:
            # a cancelled operation must no longer be considered a valid one
            # so that the callable associated with it is never called
            callable_t = loop.delay(lambda: None, timeout=60)
            loop.unpend(callable_t)
            self.assertEqual(callable_t[4][0], False)

            # the cancelling of an already cancelled operation must be a
            # no operation, so that it's not accounted for more than once
            loop.unpend(callable_t)
            self.assertEqual(loop._cancelled, 1)

            # an invalid callable tuple must be gracefully handled, as the
            # delay operation may not have returned a valid one
            loop.unpend(None)
            self.assertEqual(loop._cancelled, 1)
        finally:
            loop.close()

    def test_unpend_executed(self):
        loop = netius.Base()
        try:
            # an operation that has already been executed is no longer part
            # of the queues, so cancelling its handler must not be accounted
            # for as if it were still pending removal
            callable_t = loop.delay(lambda: None, timeout=60)
            loop._delayed = []
            loop._delayed_o = []
            loop.unpend(callable_t)
            self.assertEqual(loop._cancelled, 1)
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test_compact(self):
        loop = netius.Base()
        try:
            # the cancelled operations must be removed from the delayed
            # queues, keeping only the ones that are still valid
            valid = [loop.delay(lambda: None, timeout=60) for _index in range(10)]
            cancelled = [loop.delay(lambda: None, timeout=60) for _index in range(10)]
            for callable_t in cancelled:
                loop.unpend(callable_t)
            self.assertEqual(len(loop._delayed), 20)

            loop.compact()

            self.assertEqual(len(loop._delayed), 10)
            self.assertEqual(len(loop._delayed_o), 10)
            self.assertEqual(loop._cancelled, 0)
            self.assertEqual(all(callable_t[4][0] for callable_t in valid), True)
        finally:
            loop.close()

    def test_unpend_compact(self):
        loop = netius.Base()
        try:
            # the queues must be compacted on their own once enough of the
            # operations in them have been cancelled, so that a cancelled
            # operation does not occupy the queue until its target time
            callables = [
                loop.delay(lambda: None, timeout=60)
                for _index in range(common.COMPACT_MIN * 2)
            ]
            for callable_t in callables:
                loop.unpend(callable_t)

            self.assertEqual(len(loop._delayed), 0)
            self.assertEqual(loop._cancelled, 0)
        finally:
            loop.close()

    def test_unpend_amortized(self):
        loop = netius.Base()
        try:
            # the compaction only pays off once the cancelled operations are
            # a relevant part of the queue, so a queue that is mostly made of
            # valid operations must be left untouched by the cancelling
            callables = [
                loop.delay(lambda: None, timeout=60)
                for _index in range(common.COMPACT_MIN * 4)
            ]
            for callable_t in callables[: common.COMPACT_MIN]:
                loop.unpend(callable_t)

            self.assertEqual(len(loop._delayed), common.COMPACT_MIN * 4)
            self.assertEqual(loop._cancelled, common.COMPACT_MIN)
        finally:
            loop.close()

    def test__delays(self):
        loop = netius.Base()
        try:
            fired = []
            loop.delay(lambda: fired.append("due"), timeout=-1)
            loop.delay(lambda: fired.append("late"), timeout=30)

            # only the operation that is already due may be run, the one that
            # is still pending must be kept in the queue untouched
            loop._delays()
            self.assertEqual(fired, ["due"])
            self.assertEqual(len(loop._delayed), 1)

            # a new iteration with nothing due must not run anything, note
            # that the pending operation must remain in the queue
            loop._delays()
            self.assertEqual(fired, ["due"])
            self.assertEqual(len(loop._delayed), 1)
            self.assertEqual(len(loop._delayed_o), 1)
        finally:
            loop.close()

    def test__delays_lid(self):
        loop = netius.Base()
        try:
            fired = []
            loop.delay(lambda: fired.append("next"))

            # an operation scheduled for the next tick may not be run in the
            # very same iteration that created it, otherwise a callable that
            # re-schedules itself would loop forever within a single tick
            loop._delays()

            self.assertEqual(fired, [])
            self.assertEqual(len(loop._delayed), 1)

            loop._lid = (loop._lid + 1) % 2147483647
            loop._delays()

            self.assertEqual(fired, ["next"])
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test__delays_cancelled(self):
        loop = netius.Base()
        try:
            fired = []
            callable_t = loop.delay(lambda: fired.append("cancelled"), timeout=-1)
            loop.unpend(callable_t)

            self.assertEqual(loop._cancelled, 1)

            # the cancelled operation is dropped once its target time is
            # reached, releasing the slot it was taking in the counter
            loop._delays()

            self.assertEqual(fired, [])
            self.assertEqual(loop._cancelled, 0)
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test__delays_error(self):
        loop = netius.Base()
        try:

            def raiser():
                raise RuntimeError("Delayed error")

            fired = []
            loop.delay(raiser, timeout=-1)
            loop.delay(lambda: fired.append("after"), timeout=-1)

            # an exception raised by a delayed operation is logged and does
            # not stop the remaining operations from being run
            loop._delays()

            self.assertEqual(fired, ["after"])
            self.assertEqual(len(loop._delayed), 0)
        finally:
            loop.close()

    def test__delays_stop(self):
        loop = netius.Base()
        try:

            def stopper():
                raise errors.StopError("Delayed stop")

            loop.delay(stopper, timeout=-1)

            # the errors that control the life cycle of the loop are not to
            # be swallowed, being propagated to the caller instead
            self.assertRaises(errors.StopError, loop._delays)
        finally:
            loop.close()

    def test__delays_notifies(self):
        loop = netius.Base()
        try:
            received = []
            loop.wait_event(lambda data: received.append(data), name="event")
            loop.notify("event", data="payload")

            # the pending notifications are processed as part of the delays
            # cycle, even though there's no delayed operation to be run
            loop._delays()

            self.assertEqual(received, ["payload"])
            self.assertEqual(loop._notified, [])
        finally:
            loop.close()

    def test_resolve_hostname(self):
        loop = netius.get_main()
        future = loop.resolve_hostname("gmail.com")
        result = loop.run_coroutine(future)
        loop.close()

        self.assertNotEqual(result, None)
        self.assertEqual(isinstance(result, str), True)

    def test_sleep(self):
        loop = netius.Base()
        try:
            future = loop.sleep(1.5)

            self.assertEqual(future.done(), False)
            self.assertEqual(len(loop._delayed), 1)

            # the future is only completed once the delayed operation is run
            # and the result it carries is the requested timeout
            loop._delayed[0][2]()

            self.assertEqual(future.done(), True)
            self.assertEqual(future.result(), 1.5)
        finally:
            loop.close()

    def test_wait(self):
        loop = netius.Base()
        try:
            future = loop.wait("event")

            self.assertEqual(len(loop._events["event"]), 1)

            loop.notify("event", data="payload")
            loop._notifies()

            # the payload of the event becomes the result of the future and
            # the bind is released once the future has been completed
            self.assertEqual(future.result(), "payload")
            self.assertEqual("event" in loop._events, False)
        finally:
            loop.close()

    def test_wait_cancelled(self):
        loop = netius.Base()
        try:
            future = loop.wait("event")
            future.cancel()

            # a notification that arrives once the future has been cancelled
            # must be dropped, as setting a result on it would raise
            loop.notify("event", data="payload")
            loop._notifies()

            self.assertEqual(future.cancelled(), True)
        finally:
            loop.close()

    def test_wait_timeout(self):
        loop = netius.Base()
        try:
            # the future is built with no loop bound to it so that the done
            # callbacks are run inline, a future bound to a loop would have
            # the releasing of the bind delayed to one of its next ticks
            future = asynchronous.Future()
            loop.wait("event", timeout=60, future=future)

            # the canceler is scheduled together with the waiting so that a
            # notification that never arrives does not block forever
            self.assertEqual(len(loop._delayed), 1)

            loop._delayed[0][2]()

            self.assertEqual(future.cancelled(), True)
            self.assertEqual("event" in loop._events, False)
        finally:
            loop.close()

    def test_wait_timeout_notified(self):
        loop = netius.Base()
        try:
            future = loop.wait("event", timeout=60)
            loop.notify("event", data="payload")
            loop._notifies()

            # the canceler is still run once the timeout is reached, but an
            # already completed future may no longer be cancelled by it
            loop._delayed[0][2]()

            self.assertEqual(future.cancelled(), False)
            self.assertEqual(future.result(), "payload")
        finally:
            loop.close()

    def test_notify(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            with mock.patch.object(loop, "wakeup") as wakeup:
                loop.notify("event", data="payload")

            self.assertEqual(loop._notified, [("event", "payload")])

            # a notification issued from the main thread is picked up by the
            # very same loop iteration, so there's nothing to be awaken
            self.assertEqual(wakeup.call_count, 0)

            # an event that no one is waiting for is still processed, being
            # discarded once there's no bind to hand it over to
            count = loop._notifies()

            self.assertEqual(count, 1)
            self.assertEqual(loop._notified, [])
        finally:
            loop.close()

    def test_notify_wakeup(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # a notification issued from a thread other than the main one has
            # to wake the event loop, so that it's processed as soon as possible
            loop.tid = -1

            with mock.patch.object(loop, "wakeup") as wakeup:
                loop.notify("event", data="payload")

            self.assertEqual(loop._notified, [("event", "payload")])
            self.assertEqual(wakeup.call_count, 1)
        finally:
            loop.close()

    def test__notifies(self):
        loop = netius.Base()
        try:
            received = []
            loop.wait_event(lambda data: received.append(data), name="first")
            loop.wait_event(lambda data: received.append(data), name="second")
            loop.notify("first", data=1)
            loop.notify("second", data=2)

            count = loop._notifies()

            # every pending notification is processed in a single cycle, in
            # the very same order by which they have been notified
            self.assertEqual(count, 2)
            self.assertEqual(received, [1, 2])

            # a cycle with nothing pending must be a no operation, so that
            # the delays cycle is able to tell that there's nothing to do
            self.assertEqual(loop._notifies(), 0)
        finally:
            loop.close()

    def test_diag_closed_max(self):
        # the bound of the ring buffer must never be a negative value, as
        # the construction of the deque would otherwise fail at import
        self.assertEqual(common.DIAG_CLOSED_MAX >= 0, True)
        self.assertEqual(
            common.AbstractBase._DIAG_CLOSED.maxlen, common.DIAG_CLOSED_MAX
        )

    def test_on_connection_d(self):
        loop = netius.Base()
        buffer = common.AbstractBase._DIAG_CLOSED
        instance = common.AbstractBase._DIAG_INSTANCE
        try:
            buffer.clear()

            # with no diagnostics running the closing of a connection must
            # not be recorded, sparing the regular execution from its cost
            self._make_connection(loop)

            self.assertEqual(len(buffer), 0)

            # a diagnostics application started from an instance is enough
            # for the recording to happen, even with the configuration unset
            common.AbstractBase._DIAG_INSTANCE = loop
            connection = self._make_connection(loop)

            self.assertEqual(len(buffer), 1)
            self.assertEqual(buffer[0]["id"], connection.id)
        finally:
            common.AbstractBase._DIAG_INSTANCE = instance
            buffer.clear()
            loop.close()

    def test_record_closed(self):
        loop = netius.Base()
        buffer = common.AbstractBase._DIAG_CLOSED
        try:
            buffer.clear()

            # a connection that keeps track of its creation must have the
            # duration of it calculated from the closing timestamp
            connection = self._make_connection(loop, diag=True)
            connection.creation = connection.close_timestamp - 2.0
            connection.close_paired = "other"
            connection.recvs = 3
            connection.sends = 2
            connection.in_bytes = 512
            connection.out_bytes = 1024
            connection.last_recv_ts = connection.close_timestamp - 1.0
            loop.record_closed(connection)

            self.assertEqual(len(buffer), 1)
            self.assertEqual(buffer[0]["id"], connection.id)
            self.assertEqual(buffer[0]["close_reason"], netius.REASON_TIMEOUT)
            self.assertEqual(buffer[0]["close_error"], "idle")
            self.assertEqual(buffer[0]["close_paired"], "other")
            self.assertEqual(buffer[0]["duration"], 2.0)

            # the record must reflect the values of the connection at the
            # moment it was taken, so they are verified one by one
            self.assertEqual(buffer[0]["status"], connection.status)
            self.assertEqual(buffer[0]["recvs"], connection.recvs)
            self.assertEqual(buffer[0]["sends"], connection.sends)
            self.assertEqual(buffer[0]["in_bytes"], connection.in_bytes)
            self.assertEqual(buffer[0]["out_bytes"], connection.out_bytes)
            self.assertEqual(buffer[0]["close_timestamp"], connection.close_timestamp)
            self.assertEqual(
                buffer[0]["last_activity_timestamp"], connection._last_activity()
            )

            # the duration must be the exact distance between the creation
            # and the closing of the connection
            self.assertEqual(
                buffer[0]["duration"],
                connection.close_timestamp - connection.creation,
            )

            # the record is detached from the connection, so a change in the
            # latter must never be reflected in the value already stored
            connection.close_reason = netius.REASON_ERROR
            connection.in_bytes = 0

            self.assertEqual(buffer[0]["close_reason"], netius.REASON_TIMEOUT)
            self.assertEqual(buffer[0]["in_bytes"], 512)

            # a connection with no creation time has no duration associated
            # with it, as there's no value from which to measure it
            connection = self._make_connection(loop)
            loop.record_closed(connection)

            self.assertEqual(len(buffer), 2)
            self.assertEqual(buffer[1]["duration"], None)
            self.assertEqual(buffer[1]["close_paired"], None)
        finally:
            buffer.clear()
            loop.close()

    def test_connections_closed_dict(self):
        loop = netius.Base()
        original = common.AbstractBase._DIAG_CLOSED
        try:
            # replaces the ring buffer by a smaller one so that the bound
            # of it may be verified without a large number of entries
            common.AbstractBase._DIAG_CLOSED = collections.deque(maxlen=2)

            first = self._make_connection(loop)
            second = self._make_connection(loop)
            loop.record_closed(first)
            loop.record_closed(second)

            # the most recently closed connection must be the first one to
            # be reported, so that the latest events are the visible ones
            closed = loop.connections_closed_dict()
            self.assertEqual([info["id"] for info in closed], [second.id, first.id])

            # once the maximum number of entries is reached the oldest of
            # them must be dropped, keeping the memory usage bounded
            third = self._make_connection(loop)
            loop.record_closed(third)

            closed = loop.connections_closed_dict()
            self.assertEqual(len(closed), 2)
            self.assertEqual([info["id"] for info in closed], [third.id, second.id])

            # the listing is a snapshot detached from the ring buffer, so a
            # new record must not change a listing that was already taken
            loop.record_closed(self._make_connection(loop))

            self.assertEqual(len(closed), 2)
            self.assertEqual([info["id"] for info in closed], [third.id, second.id])
        finally:
            common.AbstractBase._DIAG_CLOSED = original
            loop.close()

    def test__format_delta(self):
        loop = netius.Base()
        try:
            # the two most significant components of the delta are the ones
            # reported, with the seconds used only when there's no other
            self.assertEqual(loop._format_delta(datetime.timedelta(seconds=0)), "0s")
            self.assertEqual(loop._format_delta(datetime.timedelta(seconds=1)), "1s")
            self.assertEqual(
                loop._format_delta(datetime.timedelta(seconds=3661)), "1h 1m"
            )
            self.assertEqual(
                loop._format_delta(datetime.timedelta(seconds=90000)), "1d 1h"
            )

            # a negative delta may result from the resolution of the clocks,
            # in which case no duration at all must be reported for it, as
            # its components would otherwise come from the complement of a day
            self.assertEqual(
                loop._format_delta(datetime.timedelta(seconds=-0.001)), "0s"
            )
            self.assertEqual(loop._format_delta(datetime.timedelta(seconds=-60)), "0s")
            self.assertEqual(
                loop._format_delta(datetime.timedelta(seconds=-90000)), "0s"
            )
        finally:
            loop.close()

    def _make_connection(self, loop, diag=False):
        # builds a closed connection registered in the loop, so that it may
        # be recorded in the ring buffer of closed connections
        _socket = socket.socket()
        cls = conn.DiagConnection if diag else conn.BaseConnection
        connection = cls(owner=loop, socket=_socket)
        connection.status = conn.OPEN
        loop.connections.append(connection)
        loop.connections_m[_socket] = connection
        connection.close_reason = netius.REASON_TIMEOUT
        connection.close_error = "idle"
        connection.close()
        return connection
