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
import ssl
import sys
import errno
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

    def test_socket_tcp(self):
        loop = netius.Base()
        try:
            _socket = loop.socket_tcp(receive_buffer=32768, send_buffer=32768)
            try:
                # the socket of a service never blocks, as every operation of
                # it is driven by the poll instead of by the call itself
                self.assertEqual(_socket.gettimeout(), 0.0)
                self.assertEqual(_socket.family, socket.AF_INET)

                # the address is reusable so that a restart does not have to
                # wait out the lingering of the previous socket
                self.assertNotEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0
                )
                self.assertNotEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE), 0
                )

                # the delaying of the small writes is off, as a protocol that
                # answers in small messages would otherwise be held back
                self.assertNotEqual(
                    _socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY), 0
                )

                # the sizes that were asked for reach the buffers, the kernel
                # being free to round them up
                self.assertGreaterEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF), 32768
                )
                self.assertGreaterEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF), 32768
                )
            finally:
                _socket.close()
        finally:
            loop.close()

    def test_socket_tcp_unix(self):
        if not hasattr(socket, "AF_UNIX"):
            self.skipTest("Skipping test: Unix domain sockets unavailable")

        loop = netius.Base()
        try:
            _socket = loop.socket_tcp(family=socket.AF_UNIX)
            try:
                # a socket of the domain of the machine has no notion of the
                # options of TCP, so none of them is set on it
                self.assertEqual(_socket.family, socket.AF_UNIX)
                self.assertNotEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0
                )
            finally:
                _socket.close()
        finally:
            loop.close()

    def test_socket_tcp_ssl(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            with mock.patch.object(loop, "_ssl_wrap") as ssl_wrap:
                loop.socket_tcp(ssl=True, ca_file="net.ca", ssl_verify=True)

            # a secure service wraps its socket before anything is set on it,
            # and it does so as the server side of the exchange
            self.assertEqual(ssl_wrap.call_args[1]["server"], True)
            self.assertEqual(ssl_wrap.call_args[1]["ca_file"], "net.ca")
            self.assertEqual(ssl_wrap.call_args[1]["ssl_verify"], True)
        finally:
            loop.close()

    def test_socket_udp(self):
        loop = netius.Base()
        try:
            _socket = loop.socket_udp()
            try:
                self.assertEqual(_socket.gettimeout(), 0.0)

                # the flag of the non blocking mode leaks into the type of the
                # socket under the older runtimes, so it is masked out of the
                # verification of it
                type_v = _socket.type & ~getattr(socket, "SOCK_NONBLOCK", 0)
                self.assertEqual(type_v, socket.SOCK_DGRAM)

                # a datagram service may be asked to reach every host of the
                # network, which is what the broadcasting allows for
                self.assertNotEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST), 0
                )
                self.assertNotEqual(
                    _socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR), 0
                )
            finally:
                _socket.close()
        finally:
            loop.close()

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

    def test_on_read(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = [b"hello", b""]

            loop.on_read(_socket)

            # every chunk that comes off the socket is handed over until the
            # peer closes it, which is what an empty read stands for
            self.assertEqual(connection.set_data.call_args_list[0][0][0], b"hello")
            self.assertEqual(
                connection.close.call_args[1]["reason"], netius.REASON_CLIENT_EOF
            )
        finally:
            loop.close()

    def test_on_read_callbacks(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()
            callback = mock.MagicMock()
            loop.callbacks_m[_socket] = [callback]

            # a socket that names no connection still notifies the callbacks
            # registered for it, as they are what a raw reader relies on
            loop.on_read(_socket)

            self.assertEqual(callback.call_args[0], ("read", _socket))
        finally:
            loop.callbacks_m.pop(_socket, None)
            loop.close()

    def test_on_read_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # a connection that is no longer open, or one whose reading was
            # turned off, is left alone instead of being read from
            for attribute, value in (
                ("status", netius.CLOSED),
                ("renable", False),
            ):
                _socket, connection = self._make_readable(loop)
                setattr(connection, attribute, value)

                loop.on_read(_socket)

                self.assertEqual(connection.recv.called, False)
        finally:
            loop.close()

    def test_on_read_connecting(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.connecting = True
            connection.recv.side_effect = [b""]

            with mock.patch.object(loop, "_connectf") as connectf:
                loop.on_read(_socket)

            # a connection that is still being established is finished before
            # anything is read from it, as the reading depends on it
            self.assertEqual(connectf.call_args[0][0], connection)
        finally:
            loop.close()

    def test_on_read_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.run_starter.return_value = True

            loop.on_read(_socket)

            # with a starter still running in the connection nothing is read,
            # as it has to complete before the payload may be handled
            self.assertEqual(connection.recv.called, False)
        finally:
            loop.close()

    def test_on_read_interrupted(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # the loop stops reading as soon as the connection is no longer in
            # a state that allows it, so that a close taken in the middle of
            # the reading is not overrun by the chunk that follows it
            def close(*args, **kwargs):
                connection.status = netius.CLOSED

            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = [b"first", b"second"]
            connection.set_data.side_effect = close

            loop.on_read(_socket)

            self.assertEqual(connection.recv.call_count, 1)

            def disable(*args, **kwargs):
                connection.renable = False

            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = [b"first", b"second"]
            connection.set_data.side_effect = disable

            loop.on_read(_socket)

            self.assertEqual(connection.recv.call_count, 1)

            def replace(*args, **kwargs):
                connection.socket = mock.MagicMock()

            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = [b"first", b"second"]
            connection.set_data.side_effect = replace

            loop.on_read(_socket)

            self.assertEqual(connection.recv.call_count, 1)
        finally:
            loop.close()

    def test_on_read_ssl_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # an error that is expected drops the connection quietly, one that
            # is part of the retrying is ignored altogether, and any other one
            # is reported as the exception that it is
            for error, expected, exception in (
                (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
                (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
                (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
            ):
                _socket, connection = self._make_readable(loop)
                connection.recv.side_effect = error

                with mock.patch.object(loop, "on_expected") as on_expected:
                    with mock.patch.object(loop, "on_exception") as on_exception:
                        loop.on_read(_socket)

                self.assertEqual(on_expected.called, expected)
                self.assertEqual(on_exception.called, exception)
        finally:
            loop.close()

    def test_on_read_ssl_reason(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # the reason of the error is what tells a peer that spoke the wrong
            # protocol from a proper failure, and it is read from the attribute
            # when the runtime maps it
            error = ssl.SSLError(ssl.SSL_ERROR_SSL)
            error.reason = "WRONG_VERSION_NUMBER"

            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = error

            with mock.patch.object(loop, "on_expected") as on_expected:
                loop.on_read(_socket)

            self.assertEqual(on_expected.called, True)

            # and from the text of it when the runtime does not, which is the
            # fallback that keeps the behaviour the same across them
            error = ssl.SSLError(
                ssl.SSL_ERROR_SSL,
                "[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1006)",
            )

            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = error

            with mock.patch.object(loop, "on_expected") as on_expected:
                loop.on_read(_socket)

            self.assertEqual(on_expected.called, True)
        finally:
            loop.close()

    def test_on_read_socket_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # the errors of the socket are classified in the same three ways,
            # the ones that merely say that there is nothing to read being the
            # ones that must not reach the caller at all
            for value, expected, exception in (
                (errno.ECONNRESET, True, False),
                (errno.EWOULDBLOCK, False, False),
                (errno.EBADF, False, True),
            ):
                _socket, connection = self._make_readable(loop)
                connection.recv.side_effect = socket.error(value, "error")

                with mock.patch.object(loop, "on_expected") as on_expected:
                    with mock.patch.object(loop, "on_exception") as on_exception:
                        loop.on_read(_socket)

                self.assertEqual(on_expected.called, expected)
                self.assertEqual(on_exception.called, exception)
        finally:
            loop.close()

    def test_on_read_exception(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = ValueError("broken")

            with mock.patch.object(loop, "on_exception") as on_exception:
                loop.on_read(_socket)

            # any other failure is caught and reported, as letting it out would
            # take the whole of the loop down with the connection
            self.assertEqual(on_exception.call_args[0][1], connection)

            # the ones that ask for the process to end are the exception to
            # that, as they must not be swallowed by the loop
            _socket, connection = self._make_readable(loop)
            connection.recv.side_effect = KeyboardInterrupt()

            self.assertRaises(KeyboardInterrupt, loop.on_read, _socket)
        finally:
            loop.close()

    def test_on_write(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)

            loop.on_write(_socket)

            # a socket that became writable flushes whatever the connection
            # still holds in its buffer
            self.assertEqual(connection._send.called, True)
        finally:
            loop.close()

    def test_on_write_callbacks(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()
            callback = mock.MagicMock()
            loop.callbacks_m[_socket] = [callback]

            loop.on_write(_socket)

            self.assertEqual(callback.call_args[0], ("write", _socket))
        finally:
            loop.callbacks_m.pop(_socket, None)
            loop.close()

    def test_on_write_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.status = netius.CLOSED

            # a connection that is no longer open has nothing to flush, the
            # buffer of it having been dropped with the closing
            loop.on_write(_socket)

            self.assertEqual(connection._send.called, False)
        finally:
            loop.close()

    def test_on_write_connecting(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket, connection = self._make_readable(loop)
            connection.connecting = True

            with mock.patch.object(loop, "_connectf") as connectf:
                loop.on_write(_socket)

            # the becoming writable of a socket is what says that a connection
            # was established, so it is finished before anything is sent
            self.assertEqual(connectf.call_args[0][0], connection)
        finally:
            loop.close()

    def test_on_write_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # the sending classifies the failures exactly as the reading does,
            # which is what keeps the two sides of a connection consistent
            for error, expected, exception in (
                (ssl.SSLError(ssl.SSL_ERROR_ZERO_RETURN), True, False),
                (ssl.SSLError(ssl.SSL_ERROR_WANT_WRITE), False, False),
                (socket.error(errno.EPIPE, "error"), True, False),
                (socket.error(errno.EAGAIN, "error"), False, False),
                (socket.error(errno.EBADF, "error"), False, True),
                (ValueError("broken"), False, True),
            ):
                _socket, connection = self._make_readable(loop)
                connection._send.side_effect = error

                with mock.patch.object(loop, "on_expected") as on_expected:
                    with mock.patch.object(loop, "on_exception") as on_exception:
                        loop.on_write(_socket)

                self.assertEqual(on_expected.called, expected)
                self.assertEqual(on_exception.called, exception)

            _socket, connection = self._make_readable(loop)
            connection._send.side_effect = SystemExit()

            self.assertRaises(SystemExit, loop.on_write, _socket)
        finally:
            loop.close()

    def test_on_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()
            callback = mock.MagicMock()
            loop.callbacks_m[_socket] = [callback]

            # a socket that names no connection still notifies the callbacks
            # registered for it, and nothing else is done for it
            loop.on_error(_socket)

            self.assertEqual(callback.call_args[0], ("error", _socket))

            _socket, connection = self._make_readable(loop)

            loop.on_error(_socket)

            # a connection whose socket is in error is dropped, the reason
            # naming it so that the diagnostics may tell it apart
            self.assertEqual(
                connection.close.call_args[1]["reason"], netius.REASON_ERROR
            )

            _socket, connection = self._make_readable(loop)
            connection.status = netius.CLOSED

            # one that is already closed is left alone, instead of being
            # closed a second time
            loop.on_error(_socket)

            self.assertEqual(connection.close.called, False)
        finally:
            loop.callbacks_m.clear()
            loop.close()

    def test_on_read_s(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            service = mock.MagicMock()
            _socket = mock.MagicMock()
            first, second = mock.MagicMock(), mock.MagicMock()
            _socket.accept.side_effect = [
                (first, ("1.2.3.4", 1234)),
                (second, ("5.6.7.8", 5678)),
                socket.error(errno.EWOULDBLOCK, "error"),
            ]

            loop.on_read_s(_socket, service)

            # the accepting goes on until the queue of the kernel is empty,
            # so that a single wake up of the poll takes every connection
            self.assertEqual(service.on_socket_c.call_count, 2)
            self.assertEqual(service.on_socket_c.call_args_list[0][0][0], first)
        finally:
            loop.close()

    def test_on_read_s_refused(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            service = mock.MagicMock()
            service.on_socket_c.side_effect = ValueError("broken")
            _socket = mock.MagicMock()
            socket_c = mock.MagicMock()
            _socket.accept.side_effect = [(socket_c, ("1.2.3.4", 1234))]

            with mock.patch.object(loop, "on_exception_s") as on_exception_s:
                loop.on_read_s(_socket, service)

            # a socket that the service refused is closed rather than leaked,
            # and the failure is still reported as the exception that it is
            self.assertEqual(socket_c.close.called, True)
            self.assertEqual(on_exception_s.called, True)
        finally:
            loop.close()

    def test_on_read_s_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # the accepting classifies the failures as the reading does, with
            # no connection to be dropped as none was established
            for error, expected, exception in (
                (ssl.SSLError(ssl.SSL_ERROR_EOF), True, False),
                (ssl.SSLError(ssl.SSL_ERROR_WANT_READ), False, False),
                (ssl.SSLError(ssl.SSL_ERROR_SSL), False, True),
                (socket.error(errno.ECONNABORTED, "error"), True, False),
                (socket.error(errno.EAGAIN, "error"), False, False),
                (socket.error(errno.EBADF, "error"), False, True),
                (ValueError("broken"), False, True),
            ):
                service = mock.MagicMock()
                _socket = mock.MagicMock()
                _socket.accept.side_effect = error

                with mock.patch.object(loop, "on_expected_s") as on_expected_s:
                    with mock.patch.object(loop, "on_exception_s") as on_exception_s:
                        loop.on_read_s(_socket, service)

                self.assertEqual(on_expected_s.called, expected)
                self.assertEqual(on_exception_s.called, exception)

            service = mock.MagicMock()
            _socket = mock.MagicMock()
            _socket.accept.side_effect = KeyboardInterrupt()

            self.assertRaises(KeyboardInterrupt, loop.on_read_s, _socket, service)
        finally:
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

    def test__connect(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = self._make_connecting()

            with mock.patch.object(loop, "_connectf") as connectf:
                loop._connect(connection)

            # the connection is opened before the reaching of the peer, and
            # the establishment is finished as soon as that one returns
            self.assertEqual(connection.open.call_args[1]["connect"], True)
            self.assertEqual(
                connection.socket.connect.call_args[0][0], connection.address
            )
            self.assertEqual(connectf.call_args[0][0], connection)
        finally:
            loop.close()

    def test__connect_closed(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = self._make_connecting()
            connection.status = netius.CLOSED

            # a connection that was closed while it waited for its turn is
            # left alone, instead of a socket being reached for it
            loop._connect(connection)

            self.assertEqual(connection.open.called, False)
        finally:
            loop.close()

    def test__connect_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # an error that merely says that the establishment is under way
            # leaves the connection open, the poll being the one that says
            # when it has finished
            for error in (
                ssl.SSLError(ssl.SSL_ERROR_WANT_WRITE),
                socket.error(errno.EINPROGRESS, "error"),
                socket.error(errno.EWOULDBLOCK, "error"),
            ):
                connection = self._make_connecting()
                connection.socket.connect.side_effect = error

                with mock.patch.object(loop, "_connectf") as connectf:
                    loop._connect(connection)

                self.assertEqual(connection.close.called, False)
                self.assertEqual(connectf.called, False)
        finally:
            loop.close()

    def test__connect_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # one that says that the peer cannot be reached drops the
            # connection, naming the reason so that the caller may tell it
            # apart from a closing of its own
            for error in (
                ssl.SSLError(ssl.SSL_ERROR_SSL),
                socket.error(errno.ECONNREFUSED, "error"),
            ):
                connection = self._make_connecting()
                connection.socket.connect.side_effect = error

                loop._connect(connection)

                self.assertEqual(
                    connection.close.call_args[1]["reason"], netius.REASON_ERROR
                )
        finally:
            loop.close()

    def test__connect_exception(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = self._make_connecting()
            connection.socket.connect.side_effect = ValueError("broken")

            # a failure that is none of the expected ones drops the connection
            # and still reaches the caller, as it names a defect and not a
            # state of the network
            self.assertRaises(ValueError, loop._connect, connection)
            self.assertEqual(
                connection.close.call_args[1]["reason"], netius.REASON_ERROR
            )

            connection = self._make_connecting()
            connection.socket.connect.side_effect = KeyboardInterrupt()

            self.assertRaises(KeyboardInterrupt, loop._connect, connection)
            self.assertEqual(connection.close.called, False)
        finally:
            loop.close()

    def test__socket_keepalive(self):
        loop = netius.Base()
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                loop._socket_keepalive(_socket, timeout=120, interval=12, count=5)

                # the tuning of the keeping alive is the one that was asked
                # for, as the defaults of the kernel are counted in hours
                for name, expected in (
                    ("TCP_KEEPIDLE", 120),
                    ("TCP_KEEPINTVL", 12),
                    ("TCP_KEEPCNT", 5),
                ):
                    option = getattr(socket, name, None)
                    if option == None:
                        continue
                    self.assertEqual(
                        _socket.getsockopt(socket.IPPROTO_TCP, option), expected
                    )

                # the port is reusable so that more than one process may
                # accept on it, which is what a pre-forked service asks for
                if hasattr(socket, "SO_REUSEPORT"):
                    self.assertNotEqual(
                        _socket.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT), 0
                    )
            finally:
                _socket.close()
        finally:
            loop.close()

    def test__socket_keepalive_defaults(self):
        loop = netius.Base()
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                loop._socket_keepalive(_socket)

                # with nothing asked for the values of the infra-structure are
                # the ones that reach the socket
                option = getattr(socket, "TCP_KEEPIDLE", None)
                if not option == None:
                    self.assertEqual(
                        _socket.getsockopt(socket.IPPROTO_TCP, option),
                        loop.keepalive_timeout,
                    )
            finally:
                _socket.close()
        finally:
            loop.close()

    def test__socket_keepalive_unix(self):
        if not hasattr(socket, "AF_UNIX"):
            self.skipTest("Skipping test: Unix domain sockets unavailable")

        loop = netius.Base()
        try:
            _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                # none of the options belongs to a socket of the domain of the
                # machine, so asking for them must be skipped rather than left
                # to the kernel to reject
                loop._socket_keepalive(_socket)
            finally:
                _socket.close()
        finally:
            loop.close()

    def test__ssl_init(self):
        loop = netius.Base()
        try:
            loop._ssl_init(env=False)

            # with the environment ignored the context is still built, under
            # the least strict of the security levels and with no option
            self.assertNotEqual(loop._ssl_context, None)
            self.assertEqual(loop._ssl_secure, 0)
            self.assertEqual(loop._ssl_context_options, [])
            self.assertEqual(loop._ssl_contexts, dict())
        finally:
            loop.close()

    def test__ssl_init_contexts(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            values = dict(
                SSL_SECURE=2,
                SSL_CONTEXT_OPTIONS=["OP_NO_TICKET"],
                SSL_CONTEXTS=dict(netius=dict(ssl_verify=False)),
            )

            with mock.patch.object(
                loop,
                "get_env",
                lambda name, default, cast=None: values.get(name, default),
            ):
                loop._ssl_init()

            # a context is built for every host name of the map, kept together
            # with the values that produced it so that they may be read later
            context, _values = loop._ssl_contexts["netius"]
            self.assertEqual(_values, dict(ssl_verify=False))
            self.assertEqual(loop._ssl_secure, 2)

            # the security level and the options of the environment reach both
            # the main context and the ones of the host names
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1_1), True)
            if hasattr(ssl, "OP_NO_TICKET"):
                self.assertEqual(bool(context.options & ssl.OP_NO_TICKET), True)
        finally:
            loop.close()

    def test__ssl_init_unstrict(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            # a context that cannot be told about the host name of the peer is
            # unset under the strict mode, as it would serve the wrong
            # certificate for every host other than the default one
            with mock.patch.object(common.ssl, "SSLContext", _MockContext):
                loop._ssl_init(env=False)
                self.assertEqual(loop._ssl_context, None)

                loop._ssl_init(strict=False, env=False)
                self.assertNotEqual(loop._ssl_context, None)
        finally:
            loop.close()

    def test__ssl_reload(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            loop._ssl_contexts = dict()

            # a plain map has no notion of reloading, so nothing is asked of
            # it and no message is produced for it
            with mock.patch.object(loop, "info") as info:
                loop._ssl_reload()

            self.assertEqual(info.called, False)

            loop._ssl_contexts = mock.MagicMock()
            loop._ssl_contexts.reload.return_value = False

            # a map that supports it is reloaded, the absence of a change
            # keeping the operation silent
            with mock.patch.object(loop, "info") as info:
                loop._ssl_reload()

            self.assertEqual(loop._ssl_contexts.reload.called, True)
            self.assertEqual(info.called, False)

            loop._ssl_contexts.reload.return_value = True

            # only a reload that picked up a new certificate is reported, so
            # that the log is not filled by the periodic verification
            with mock.patch.object(loop, "info") as info:
                loop._ssl_reload()

            self.assertEqual(info.called, True)
        finally:
            loop._ssl_contexts = dict()
            loop.close()

    def test__ssl_callback(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            hostname = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_contexts = dict(netius=(hostname, dict()))

            loop._ssl_callback(_socket, "netius", context)

            # the context of the host name is the one that ends up serving the
            # connection, replacing the default one that was offered
            self.assertEqual(_socket.context, hostname)

            loop._ssl_callback(_socket, "other", context)

            # a host name that names no context of its own keeps the default
            # one, which is what the fallback of the map gives back
            self.assertEqual(_socket.context, context)
        finally:
            loop._ssl_contexts = dict()
            loop.close()

    def test__ssl_callback_verification(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            connection = mock.MagicMock()
            loop.connections_m[_socket] = connection
            loop._ssl_contexts = dict(
                netius=(context, dict(ssl_host="netius.hive", ssl_fingerprint="ab:cd"))
            )

            loop._ssl_callback(_socket, "netius", context)

            # the verification values of the host name travel to the connection,
            # as it is the one that runs them once the handshake is done
            self.assertEqual(connection.ssl_host, "netius.hive")
            self.assertEqual(connection.ssl_fingerprint, "ab:cd")

            # values that ask for no verification at all leave the connection
            # untouched, instead of overwriting what it already holds, and so
            # do the ones that carry only the paths of the certificates
            for values in (dict(), dict(key_file="net.key")):
                loop._ssl_contexts = dict(netius=(context, values))
                connection = mock.MagicMock()
                loop.connections_m[_socket] = connection
                loop._ssl_callback(_socket, "netius", context)

                self.assertEqual(connection.mock_calls, [])

            # a socket that names no connection is ignored, which is the case
            # of one that was closed while the handshake was under way
            del loop.connections_m[_socket]
            loop._ssl_contexts = dict(
                netius=(context, dict(ssl_host="netius.hive", ssl_fingerprint=None))
            )
            self.assertEqual(loop._ssl_callback(_socket, "netius", context), None)
        finally:
            loop.connections_m.pop(_socket, None)
            loop._ssl_contexts = dict()
            loop.close()

    def test__ssl_ctx(self):
        loop = netius.Base()
        try:
            context = loop._ssl_ctx(dict(), secure=1)

            # the verification of the peer is off unless it is asked for, as
            # the common case of a server is to not require a client
            # certificate at all
            self.assertEqual(context.verify_mode, ssl.CERT_NONE)

            context = loop._ssl_ctx(dict(ssl_verify=True), secure=1)

            # a context that asks for the verification requires the
            # certificate of the peer rather than merely accepting one
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        finally:
            loop.close()

    def test__ssl_ctx_base(self):
        loop = netius.Base()
        try:
            # the lowest of the levels leaves the old protocols in place, as
            # it exists for the peers that cannot speak anything newer
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_ctx_base(context, secure=0)
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1), False)
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1_1), False)

            # the default level keeps TLSv1 and TLSv1.1 available while the
            # strict one disables both of them
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_ctx_base(context, secure=1)
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1), False)

            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_ctx_base(context, secure=2)
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1), True)
            self.assertEqual(bool(context.options & ssl.OP_NO_TLSv1_1), True)

            # the minimum version follows the level, when the runtime is able
            # to express it (only from Python 3.7 onwards)
            if hasattr(context, "minimum_version") and hasattr(ssl, "TLSVersion"):
                self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        finally:
            loop.close()

    def test__ssl_ctx_base_options(self):
        loop = netius.Base()
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_ctx_base(
                context, secure=1, context_options=["OP_NO_TICKET", "OP_NOT_A_THING"]
            )

            # an option that the runtime knows about is applied and one that it
            # does not is skipped, instead of breaking the build of the context
            if hasattr(ssl, "OP_NO_TICKET"):
                self.assertEqual(bool(context.options & ssl.OP_NO_TICKET), True)
        finally:
            loop.close()

    def test__ssl_ctx_base_ciphers(self):
        loop = netius.Base()
        try:
            for secure, first, fallback in (
                (0, "ALL:@SECLEVEL=0", "ALL"),
                (1, "DEFAULT:@SECLEVEL=0", "DEFAULT"),
                (2, "DEFAULT:@SECLEVEL=1", "DEFAULT"),
            ):
                # the level of the security travels in the string that selects
                # the suites, so that the old ones are only taken where asked
                context = _MockContext()
                loop._ssl_ctx_base(context, secure=secure)
                self.assertEqual(context.ciphers, [first])

                # a library that cannot express a level in that string rejects
                # it, and the selection falls back to the plain name of the
                # suite instead of the build of the context failing
                context = _MockContext(seclevel=False)
                loop._ssl_ctx_base(context, secure=secure)
                self.assertEqual(context.ciphers, [fallback])
        finally:
            loop.close()

    def test__ssl_ctx_protocols(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            context = mock.MagicMock()

            # an infra-structure that negotiates no protocol at all must not
            # offer an empty list to the peer, so nothing is set on the context
            loop._ssl_ctx_protocols(context)
            self.assertEqual(context.set_alpn_protocols.called, False)

            with mock.patch.object(loop, "get_protocols", return_value=["h2"]):
                loop._ssl_ctx_protocols(context)

            # the protocols of the infra-structure are the ones announced,
            # under whichever of the two negotiations the runtime supports
            if getattr(ssl, "HAS_ALPN", False):
                self.assertEqual(context.set_alpn_protocols.call_args[0][0], ["h2"])
            if getattr(ssl, "HAS_NPN", False):
                self.assertEqual(context.set_npn_protocols.call_args[0][0], ["h2"])
        finally:
            loop.close()

    def test__ssl_ctx_debug(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_ctx_base(context, secure=2)

            with mock.patch.object(loop, "is_debug", return_value=True):
                with mock.patch.object(loop, "debug") as debug:
                    loop._ssl_ctx_debug(
                        context, secure=2, context_options=["OP_NO_TICKET"]
                    )

            # the first of the messages reports the protocols, the strict level
            # naming the old ones as disabled and the current ones as allowed
            created = debug.call_args_list[0][0]
            self.assertEqual(created[1], 2)
            self.assertEqual("TLSv1.0" in created[3], True)
            self.assertEqual("TLSv1.1" in created[3], True)
            self.assertEqual("TLSv1.2" in created[2], True)

            # the options that were asked for are reported as they are, so that
            # a configuration may be told apart from what the level implies
            messages = [call[0][0] for call in debug.call_args_list]
            self.assertEqual("SSL custom options: %s" in messages, True)
        finally:
            loop.close()

    def test__ssl_ctx_debug_options(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

            # every option that the report knows about is turned on, so that
            # the naming of each of them is exercised
            for name in (
                "OP_NO_SSLv2",
                "OP_NO_SSLv3",
                "OP_NO_TLSv1",
                "OP_NO_TLSv1_1",
                "OP_NO_TLSv1_2",
                "OP_NO_TLSv1_3",
                "OP_SINGLE_DH_USE",
                "OP_SINGLE_ECDH_USE",
                "OP_CIPHER_SERVER_PREFERENCE",
                "OP_NO_COMPRESSION",
                "OP_NO_TICKET",
                "OP_NO_RENEGOTIATION",
                "OP_LEGACY_SERVER_CONNECT",
            ):
                context.options |= getattr(ssl, name, 0)

            with mock.patch.object(loop, "is_debug", return_value=True):
                with mock.patch.object(loop, "get_protocols", return_value=["h2"]):
                    with mock.patch.object(loop, "debug") as debug:
                        loop._ssl_ctx_debug(context, secure=2)

            # every protocol whose option the runtime actually carries is
            # named as disabled, the ones it cannot express (the value of the
            # option being zero) staying among the allowed ones
            created = debug.call_args_list[0][0]
            for label, name in (
                ("SSLv2", "OP_NO_SSLv2"),
                ("SSLv3", "OP_NO_SSLv3"),
                ("TLSv1.0", "OP_NO_TLSv1"),
                ("TLSv1.1", "OP_NO_TLSv1_1"),
                ("TLSv1.2", "OP_NO_TLSv1_2"),
                ("TLSv1.3", "OP_NO_TLSv1_3"),
            ):
                expected = bool(getattr(ssl, name, 0))
                self.assertEqual(label in created[3], expected)
                self.assertEqual(label in created[2], not expected)

            messages = [call[0][0] for call in debug.call_args_list]
            self.assertEqual("SSL security options: %s" in messages, True)

            # the protocols that are announced to the peer are reported under
            # whichever of the two negotiations the runtime supports
            if getattr(ssl, "HAS_ALPN", False):
                self.assertEqual("SSL ALPN protocols: %s" in messages, True)
            if getattr(ssl, "HAS_NPN", False):
                self.assertEqual("SSL NPN protocols: %s" in messages, True)
        finally:
            loop.close()

    def test__ssl_ctx_debug_quiet(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            context = mock.MagicMock()

            # outside of the debug level nothing at all is gathered, as the
            # building of the report is not free
            with mock.patch.object(loop, "is_debug", return_value=False):
                with mock.patch.object(loop, "debug") as debug:
                    loop._ssl_ctx_debug(context)

            self.assertEqual(debug.called, False)
        finally:
            loop.close()

    def test__ssl_certs(self):
        loop = netius.Base()
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_certs(context)

            # the pair that ships with the package is the default one, and no
            # verification of the peer is asked for with it
            self.assertEqual(context.verify_mode, ssl.CERT_NONE)
            if hasattr(context, "check_hostname"):
                self.assertEqual(context.check_hostname, False)

            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            loop._ssl_certs(context, verify_mode=ssl.CERT_REQUIRED, ca_root=False)

            # a context that verifies the peer accepts a chain that is trusted
            # only from an intermediate onwards, which is what a private
            # authority typically hands out
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            if hasattr(ssl, "VERIFY_X509_PARTIAL_CHAIN"):
                self.assertEqual(
                    bool(context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN), True
                )
        finally:
            loop.close()

    def test__ssl_certs_authority(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ca_file = os.path.join(
                os.path.dirname(common.__file__), "extras", "net.cer"
            )

            with mock.patch.object(loop, "is_debug", return_value=True):
                with mock.patch.object(loop, "debug") as debug:
                    loop._ssl_certs(
                        context, ca_file=ca_file, verify_mode=ssl.CERT_REQUIRED
                    )

            # the authority that was named is the one trusted to sign the
            # certificate of the peer, and it reaches the store of the context
            self.assertEqual(len(context.get_ca_certs()), 1)
            self.assertEqual(debug.called, True)
        finally:
            loop.close()

    def test__ssl_upgrade(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            _socket = mock.MagicMock()

            with mock.patch.object(loop, "_ssl_wrap") as ssl_wrap:
                result = loop._ssl_upgrade(
                    _socket,
                    ca_file="net.ca",
                    server=False,
                    ssl_verify=True,
                    server_hostname="netius.hive",
                )

            # every value of the upgrade reaches the wrapping, the host name in
            # particular, as without it the certificate of the peer cannot be
            # matched against the one that was asked for
            self.assertEqual(ssl_wrap.call_args[0][0], _socket)
            self.assertEqual(ssl_wrap.call_args[1]["ca_file"], "net.ca")
            self.assertEqual(ssl_wrap.call_args[1]["server"], False)
            self.assertEqual(ssl_wrap.call_args[1]["ssl_verify"], True)
            self.assertEqual(ssl_wrap.call_args[1]["server_hostname"], "netius.hive")
            self.assertEqual(result, ssl_wrap.return_value)
        finally:
            loop.close()

    def test__ssl_handshake(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = mock.MagicMock()

            loop._ssl_handshake(connection)

            # a handshake that completed marks the connection as such and moves
            # the initialization of it to the starter that follows
            self.assertEqual(connection.ssl_handshake, True)
            self.assertEqual(connection.ssl_connecting, False)
            self.assertEqual(connection.end_starter.called, True)
        finally:
            loop.close()

    def test__ssl_handshake_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = mock.MagicMock()
            connection.socket.do_handshake.side_effect = ssl.SSLError(
                ssl.SSL_ERROR_WANT_WRITE
            )

            with mock.patch.object(loop, "is_sub_write", return_value=False):
                with mock.patch.object(loop, "sub_write") as sub_write:
                    loop._ssl_handshake(connection)

            # a handshake that asks for a write is resumed once the socket
            # becomes writable, so it is registered in the poll for it
            self.assertEqual(sub_write.call_args[0][0], connection.socket)
            self.assertEqual(connection.ssl_handshake, False)
            self.assertEqual(connection.ssl_connecting, True)

            connection.socket.do_handshake.side_effect = ssl.SSLError(
                ssl.SSL_ERROR_WANT_READ
            )

            with mock.patch.object(loop, "is_sub_write", return_value=True):
                with mock.patch.object(loop, "unsub_write") as unsub_write:
                    loop._ssl_handshake(connection)

            # one that asks for a read no longer needs the write registration,
            # which is dropped so that the poll is not woken up for nothing
            self.assertEqual(unsub_write.call_args[0][0], connection.socket)
        finally:
            loop.close()

    def test__ssl_handshake_error(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = mock.MagicMock()
            connection.socket.do_handshake.side_effect = ssl.SSLError(
                "unexpected failure"
            )

            # an error that is not part of the retrying of the handshake is a
            # proper failure, so it is raised to the caller instead of swallowed
            self.assertRaises(ssl.SSLError, loop._ssl_handshake, connection)
        finally:
            loop.close()

    def test__ssl_client_handshake(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = mock.MagicMock()

            with mock.patch.object(loop, "on_client_ssl") as on_client_ssl:
                loop._ssl_client_handshake(connection)

            # the client side notifies the infra-structure once the handshake
            # is done, which is what drives the verification of the peer
            self.assertEqual(connection.ssl_handshake, True)
            self.assertEqual(connection.end_starter.called, True)
            self.assertEqual(on_client_ssl.call_args[0][0], connection)
        finally:
            loop.close()

    def test__ssl_client_handshake_pending(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        loop = netius.Base()
        try:
            connection = mock.MagicMock()
            connection.socket.do_handshake.side_effect = ssl.SSLError(
                ssl.SSL_ERROR_WANT_WRITE
            )

            with mock.patch.object(loop, "is_sub_write", return_value=False):
                with mock.patch.object(loop, "sub_write") as sub_write:
                    loop._ssl_client_handshake(connection)

            # a handshake that asks for a write is resumed once the socket
            # becomes writable, so it is registered in the poll for it
            self.assertEqual(sub_write.call_args[0][0], connection.socket)

            connection.socket.do_handshake.side_effect = ssl.SSLError(
                ssl.SSL_ERROR_WANT_READ
            )

            with mock.patch.object(loop, "is_sub_write", return_value=True):
                with mock.patch.object(loop, "unsub_write") as unsub_write:
                    loop._ssl_client_handshake(connection)

            self.assertEqual(unsub_write.call_args[0][0], connection.socket)

            connection.socket.do_handshake.side_effect = ssl.SSLError("unexpected")

            # an error that is not part of the retrying is a proper failure,
            # so it reaches the caller instead of being swallowed
            self.assertRaises(ssl.SSLError, loop._ssl_client_handshake, connection)
        finally:
            loop.close()

    def test__ssl_reason(self):
        loop = netius.Base()
        try:
            # the reason is recovered from the text of the error, which is the
            # only place it can be found under a runtime that does not map the
            # complete set of the codes of the library
            self.assertEqual(
                loop._ssl_reason(
                    ssl.SSLError(
                        "[SSL: WRONG_VERSION_NUMBER] wrong version number (_ssl.c:1006)"
                    )
                ),
                "WRONG_VERSION_NUMBER",
            )
            self.assertEqual(
                loop._ssl_reason(
                    ssl.SSLError(
                        "[SSL: SSLV3_ALERT_BAD_CERTIFICATE] sslv3 alert bad certificate (_ssl.c:1006)"
                    )
                ),
                "SSLV3_ALERT_BAD_CERTIFICATE",
            )

            # an error that names no known reason gives nothing back, so that
            # the caller may tell it apart from a silenced one
            self.assertEqual(loop._ssl_reason(ssl.SSLError("something else")), None)

            # the match is done against the rendering that the library writes
            # out, so a reason is found whatever the case of the text
            self.assertEqual(
                loop._ssl_reason(ssl.SSLError("Wrong Version Number")),
                "WRONG_VERSION_NUMBER",
            )
        finally:
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

    def _make_connecting(self):
        # builds a connection stand-in in the state that the establishment of
        # a connection to the peer requires
        connection = mock.MagicMock()
        connection.status = netius.PENDING
        connection.address = ("1.2.3.4", 1234)
        connection.ssl = False
        return connection

    def _make_readable(self, loop):
        # builds a connection stand-in registered in the loop, in the state
        # that the handlers of the poll require to operate on it
        _socket = mock.MagicMock()
        connection = mock.MagicMock()
        connection.socket = _socket
        connection.status = netius.OPEN
        connection.renable = True
        connection.connecting = False
        connection.run_starter.return_value = False
        connection.recv.return_value = b""
        loop.connections_m[_socket] = connection
        return _socket, connection

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


class _MockContext(object):
    """
    Stand in for an SSL context that keeps the values that are set
    on it, used both for the runtime that offers no way of being
    told about the host name of the peer, the case that the strict
    mode of the initialization exists for, and for the one whose
    methods cannot be replaced (they are read only under it).
    """

    def __init__(self, protocol=None, seclevel=True):
        self.protocol = protocol
        self.options = 0
        self.verify_mode = ssl.CERT_NONE
        self.ciphers = []
        self._seclevel = seclevel

    def set_ciphers(self, value):
        # a library that cannot express a security level in the string
        # that selects the suites rejects the whole of the selection
        if not self._seclevel and "@SECLEVEL" in value:
            raise ssl.SSLError("no cipher match")
        self.ciphers.append(value)

    def load_cert_chain(self, cer_file, keyfile=None):
        pass

    def load_default_certs(self, purpose=None):
        pass

    def load_verify_locations(self, cafile=None):
        pass
