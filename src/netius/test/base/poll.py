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

import select
import unittest
import collections

from netius.base import poll


class PollTest(unittest.TestCase):

    def test_test(self):
        # the abstract implementation carries no platform requirement and
        # so it's reported as available under every environment
        self.assertEqual(poll.Poll.test(), True)

    def test_open(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.open(timeout=1.5)

        # the opening of a poll sets the requested timeout and starts from
        # a clean state, dropping any previous subscription
        self.assertEqual(instance.is_open(), True)
        self.assertEqual(instance.timeout, 1.5)
        self.assertEqual(instance.is_empty(), True)

        # the opening of an already open poll must be a no operation, so
        # that the timeout in use is not replaced by a new one
        instance.open(timeout=3.0)
        self.assertEqual(instance.timeout, 1.5)

    def test_close(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.open()
        instance.sub_read(socket)
        instance.close()

        # the closing of a poll releases every subscription, so that no
        # socket is retained by it after the operation
        self.assertEqual(instance.is_open(), False)
        self.assertEqual(instance.is_empty(), True)

        # the closing of an already closed poll must be a no operation
        instance.close()
        self.assertEqual(instance.is_open(), False)

    def test_poll(self):
        instance = poll.Poll()

        # the base implementation has no underlying structure to be polled
        # so an empty result is reported for every one of the operations
        self.assertEqual(instance.poll(), ([], [], []))

    def test_poll_owner(self):
        instance = poll.Poll()
        first = self._make_socket("first")
        second = self._make_socket("second")

        instance.sub_read(first, owner="owner")
        instance.sub_write(first, owner="owner")
        instance.sub_read(second, owner="other")
        instance.sub_error(second, owner="other")

        instance.poll = lambda: ([first, second], [first], [second])

        # the results must be grouped by the owner of each socket, so that
        # an owner is only handed the sockets that belong to it
        result = instance.poll_owner()
        self.assertEqual(result["owner"], ([first], [first], []))
        self.assertEqual(result["other"], ([second], [], [second]))

    def test_is_open(self):
        instance = poll.Poll()

        # a poll that has not been open yet must not be considered an
        # open one, as no underlying structure exists for it
        self.assertEqual(instance.is_open(), False)

    def test_is_edge(self):
        instance = poll.Poll()

        # the base implementation is a level triggered one, the edge
        # triggered behaviour is specific to some of the concrete ones
        self.assertEqual(instance.is_edge(), False)

    def test_is_empty(self):
        instance = poll.Poll()
        socket = self._make_socket()

        self.assertEqual(instance.is_empty(), True)

        # a poll with at least one subscription is no longer an empty one,
        # becoming empty again once such subscription is removed
        instance.sub_read(socket)
        self.assertEqual(instance.is_empty(), False)

        instance.unsub_read(socket)
        self.assertEqual(instance.is_empty(), True)

    def test_sub_all(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.sub_all(socket)

        # the subscription of every operation must be reflected in each of
        # the three sets that the poll keeps
        self.assertEqual(instance.is_sub_read(socket), True)
        self.assertEqual(instance.is_sub_write(socket), True)
        self.assertEqual(instance.is_sub_error(socket), True)

        instance.unsub_all(socket)

        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_write(socket), False)
        self.assertEqual(instance.is_sub_error(socket), False)
        self.assertEqual(instance.is_empty(), True)

    def test_sub_read(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.sub_read(socket, owner="owner")
        self.assertEqual(instance.is_sub_read(socket), True)
        self.assertEqual(instance.read_o[socket], "owner")

        # the subscription of an already subscribed socket must be a no
        # operation, so that the original owner is not replaced
        instance.sub_read(socket, owner="other")
        self.assertEqual(instance.read_o[socket], "owner")

        # the removal of a subscription that does not exist must also be
        # a no operation, instead of raising an error
        instance.unsub_read(socket)
        instance.unsub_read(socket)
        self.assertEqual(instance.is_sub_read(socket), False)

    def test_unsub_all(self):
        instance = poll.Poll()
        socket = self._make_socket()

        # the removal of the subscriptions of a socket that was never
        # subscribed must be a no operation instead of raising an error
        instance.unsub_all(socket)
        self.assertEqual(instance.is_empty(), True)

    def test_sub_write(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.sub_write(socket, owner="owner")

        # a write subscription must not imply any of the other ones, as
        # each of the operations is tracked on its own
        self.assertEqual(instance.is_sub_write(socket), True)
        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_error(socket), False)

    def test_sub_error(self):
        instance = poll.Poll()
        socket = self._make_socket()

        instance.sub_error(socket, owner="owner")

        self.assertEqual(instance.is_sub_error(socket), True)
        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_write(socket), False)

    def _make_socket(self, name="socket"):
        # builds a socket stand-in, the base poll only uses it as a key so
        # no file descriptor operations are required for it
        Socket = collections.namedtuple("Socket", "name")
        return Socket(name=name)


class EpollPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.EpollPoll.name(), "epoll")

    def test_test(self):
        self.assertEqual(poll.EpollPoll.test() in (True, False), True)

    def test_open(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = poll.EpollPoll()
        instance.open(timeout=1.5)
        try:
            # the opening must create the underlying structure and start
            # from a state with no subscription at all
            self.assertEqual(instance.is_open(), True)
            self.assertEqual(instance.timeout, 1.5)
            self.assertEqual(instance.is_empty(), True)
        finally:
            instance.close()

    def test_close(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = poll.EpollPoll()
        instance.open()
        instance.close()

        # the closing releases the underlying structure, leaving the poll
        # ready to be open once again
        self.assertEqual(instance.is_open(), False)

        instance.open()
        self.assertEqual(instance.is_open(), True)
        instance.close()

    def test_poll(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = poll.EpollPoll()
        socket = self._make_socket()
        instance.fd_m = {1: socket}

        # a readable event is reported as a read operation, the same being
        # true for a writable one and for an error one
        self.assertEqual(self._poll(instance, select.EPOLLIN), ([socket], [], []))
        self.assertEqual(self._poll(instance, select.EPOLLOUT), ([], [socket], []))
        self.assertEqual(self._poll(instance, select.EPOLLERR), ([], [], [socket]))

        # a hang up is an error, note that the read is also reported as the
        # data already buffered still has to be consumed
        self.assertEqual(
            self._poll(instance, select.EPOLLIN | select.EPOLLHUP),
            ([socket], [], [socket]),
        )

    def test_is_edge(self):
        # the epoll based poll is registered in the edge triggered mode, so
        # an event is only reported when the state of the socket changes
        self.assertEqual(poll.EpollPoll().is_edge(), True)

    def test_unsub_all(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_all(socket)

        # the complete unsubscription is the only operation that takes the
        # descriptor out of the poll, releasing every interest at once
        self.assertEqual(instance.epoll.calls[-1], ("unregister", 1))
        self.assertEqual(instance.is_empty(), True)
        self.assertEqual(1 in instance.fd_m, False)

        # the complete unsubscription of a socket that is not subscribed is
        # a no operation, so that no error is raised for it
        instance.unsub_all(socket)
        self.assertEqual(len(instance.epoll.calls), 2)

    def test_unsub_all_read_dropped(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)
        instance.unsub_all(socket)

        # the remaining interests are released even when the read one has
        # already been dropped, leaving no bookkeeping behind
        self.assertEqual(instance.epoll.calls[-1], ("unregister", 1))
        self.assertEqual(instance.is_empty(), True)
        self.assertEqual(1 in instance.fd_m, False)

    def test_sub_read(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket, owner="owner")

        # the first subscription registers the complete set of interests, as
        # the back-end is not able to separate them at poll time
        self.assertEqual(instance.epoll.calls, [("register", 1, self._mask_all())])
        self.assertEqual(instance.is_sub_read(socket), True)
        self.assertEqual(instance.is_sub_write(socket), True)
        self.assertEqual(instance.is_sub_error(socket), True)

        # a repeated subscription must not reach the poll again, avoiding an
        # already registered error being raised by it
        instance.sub_read(socket)
        self.assertEqual(len(instance.epoll.calls), 1)

    def test_sub_read_restored(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)
        instance.sub_read(socket)

        # restoring the read interest of a descriptor that is still
        # registered modifies it, a new registration would be rejected
        self.assertEqual(instance.epoll.calls[-1], ("modify", 1, self._mask_all()))
        self.assertEqual(instance.is_sub_read(socket), True)

    def test_unsub_read(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)

        # dropping the read interest keeps both the write and the error ones
        # alive, so that a pending write may still be flushed
        self.assertEqual(instance.epoll.calls[-1], ("modify", 1, self._mask_write()))
        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_write(socket), True)
        self.assertEqual(instance.is_sub_error(socket), True)

        # the descriptor stays resolvable so that the events that are still
        # subscribed may be routed back to the proper socket
        self.assertEqual(instance.fd_m[1], socket)

        # dropping the read interest of a socket that is not subscribed is a
        # no operation, leaving the poll untouched
        instance.unsub_read(socket)
        self.assertEqual(len(instance.epoll.calls), 2)

    def _poll(self, instance, event):
        instance.epoll = self._make_epoll([(1, event)])
        return instance.poll()

    def _make_socket(self, fileno=1):
        # builds a socket stand-in that exposes the file descriptor under
        # which the interest operations are going to be registered
        class Socket(object):

            def fileno(self):
                return fileno

        return Socket()

    def _make_epoll(self, events):
        # builds an epoll stand-in that reports a fixed sequence of events,
        # so that the classification of them may be verified
        class Epoll(object):

            def poll(self, *args, **kwargs):
                return events

        return Epoll()

    def _make_instance(self):
        # builds a poll that is backed by a recording stand-in, so that no
        # real descriptor is required to verify the interest changes
        instance = poll.EpollPoll()
        instance.fd_m = {}
        instance.epoll = self._make_registry()
        return instance

    def _make_registry(self):
        # builds an epoll stand-in that records the registration operations
        # performed on it, so that the interest changes may be verified
        class Epoll(object):

            def __init__(self):
                self.calls = []

            def register(self, fd, mask):
                self.calls.append(("register", fd, mask))

            def modify(self, fd, mask):
                self.calls.append(("modify", fd, mask))

            def unregister(self, fd):
                self.calls.append(("unregister", fd))

        return Epoll()

    def _mask_all(self):
        return (
            select.EPOLLIN
            | select.EPOLLOUT
            | select.EPOLLERR
            | select.EPOLLHUP
            | select.EPOLLET
        )

    def _mask_write(self):
        return select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP | select.EPOLLET


class KqueuePollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.KqueuePoll.name(), "kqueue")

    def test_test(self):
        self.assertEqual(poll.KqueuePoll.test() in (True, False), True)

    def test_open(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = poll.KqueuePoll()
        instance.open(timeout=1.5)
        try:
            # the opening must create the underlying structure and start
            # from a state with no subscription at all
            self.assertEqual(instance.is_open(), True)
            self.assertEqual(instance.timeout, 1.5)
            self.assertEqual(instance.is_empty(), True)
        finally:
            instance.close()

    def test_close(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = poll.KqueuePoll()
        instance.open()
        instance.close()

        # the closing releases the underlying structure, leaving the poll
        # ready to be open once again
        self.assertEqual(instance.is_open(), False)

        instance.open()
        self.assertEqual(instance.is_open(), True)
        instance.close()

    def test_poll(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = poll.KqueuePoll()
        socket = self._make_socket()
        instance.fd_m = {1: socket}

        # a plain read event is reported as a read operation
        self.assertEqual(
            self._poll(instance, select.KQ_FILTER_READ, 0), ([socket], [], [])
        )

        # an end of file in the read filter must still be reported as a read
        # operation, as the data already buffered has to be consumed, if it
        # were reported as an error such data would be discarded
        self.assertEqual(
            self._poll(instance, select.KQ_FILTER_READ, select.KQ_EV_EOF),
            ([socket], [], []),
        )

        # a plain write event is reported as a write operation, while an end
        # of file in it is an error as no more data may be written
        self.assertEqual(
            self._poll(instance, select.KQ_FILTER_WRITE, 0), ([], [socket], [])
        )
        self.assertEqual(
            self._poll(instance, select.KQ_FILTER_WRITE, select.KQ_EV_EOF),
            ([], [], [socket]),
        )

        # an explicit error flag is reported as an error no matter the filter
        # that has originated the event
        self.assertEqual(
            self._poll(instance, select.KQ_FILTER_READ, select.KQ_EV_ERROR),
            ([], [], [socket]),
        )

    def test_is_edge(self):
        # the kqueue based poll is also an edge triggered one, matching the
        # behaviour of the epoll based implementation
        self.assertEqual(poll.KqueuePoll().is_edge(), True)

    def test_unsub_all(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_all(socket)

        # the complete unsubscription deletes both of the filters that the
        # subscription of the read interest has added
        self.assertEqual(
            instance.kqueue.calls[-2:],
            [
                (1, select.KQ_FILTER_READ, select.KQ_EV_DELETE),
                (1, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE),
            ],
        )
        self.assertEqual(instance.is_empty(), True)
        self.assertEqual(1 in instance.fd_m, False)

        # the complete unsubscription of a socket that is not subscribed is
        # a no operation, so that no error is raised for it
        instance.unsub_all(socket)
        self.assertEqual(len(instance.kqueue.calls), 4)

    def test_unsub_all_read_dropped(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)
        instance.unsub_all(socket)

        # only the write filter is deleted by the complete unsubscription, as
        # deleting an already deleted filter would be rejected
        self.assertEqual(
            instance.kqueue.calls[-1],
            (1, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE),
        )
        self.assertEqual(instance.is_empty(), True)
        self.assertEqual(1 in instance.fd_m, False)

    def test_unsub_read(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)

        # only the read filter is deleted, the write one is kept alive so
        # that a pending write may still be flushed
        self.assertEqual(
            instance.kqueue.calls[-1],
            (1, select.KQ_FILTER_READ, select.KQ_EV_DELETE),
        )
        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_write(socket), True)
        self.assertEqual(instance.is_sub_error(socket), True)

        # the descriptor stays resolvable so that the events that are still
        # subscribed may be routed back to the proper socket
        self.assertEqual(instance.fd_m[1], socket)

        # dropping the read interest of a socket that is not subscribed is a
        # no operation, leaving the poll untouched
        instance.unsub_read(socket)
        self.assertEqual(len(instance.kqueue.calls), 3)

    def test_sub_read_restored(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)
        instance.sub_read(socket)

        # restoring the read interest adds the filter once again, the write
        # one being re-added is tolerated by the back-end
        self.assertEqual(
            instance.kqueue.calls[-2],
            (1, select.KQ_FILTER_READ, select.KQ_EV_ADD | select.KQ_EV_CLEAR),
        )
        self.assertEqual(instance.is_sub_read(socket), True)

    def _poll(self, instance, filter, flags):
        Event = collections.namedtuple("Event", "filter flags udata")
        event = Event(filter=filter, flags=flags, udata=1)
        instance.kqueue = self._make_kqueue([event])
        return instance.poll()

    def _make_socket(self, fileno=1):
        # builds a socket stand-in that exposes the file descriptor under
        # which the interest operations are going to be registered
        class Socket(object):

            def fileno(self):
                return fileno

        return Socket()

    def _make_kqueue(self, events):
        # builds a kqueue stand-in that reports a fixed sequence of events,
        # so that the classification of them may be verified
        class Kqueue(object):

            def control(self, *args, **kwargs):
                return events

        return Kqueue()

    def _make_instance(self):
        # builds a poll that is backed by a recording stand-in, so that no
        # real descriptor is required to verify the interest changes
        instance = poll.KqueuePoll()
        instance.fd_m = {}
        instance.kqueue = self._make_registry()
        return instance

    def _make_registry(self):
        # builds a kqueue stand-in that records the control operations
        # performed on it, so that the interest changes may be verified
        class Kqueue(object):

            def __init__(self):
                self.calls = []

            def control(self, events, *args, **kwargs):
                for event in events:
                    self.calls.append((event.ident, event.filter, event.flags))
                return []

        return Kqueue()


class PollPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.PollPoll.name(), "poll")

    def test_test(self):
        self.assertEqual(poll.PollPoll.test() in (True, False), True)

    def test_open(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = poll.PollPoll()
        instance.open(timeout=1.5)
        try:
            # the opening must create the underlying structure and start
            # from a state with no subscription at all
            self.assertEqual(instance.is_open(), True)
            self.assertEqual(instance.timeout, 1.5)
            self.assertEqual(instance.is_empty(), True)
        finally:
            instance.close()

    def test_close(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = poll.PollPoll()
        instance.open()
        instance.close()

        # the closing releases the underlying structure, leaving the poll
        # ready to be open once again
        self.assertEqual(instance.is_open(), False)

        instance.open()
        self.assertEqual(instance.is_open(), True)
        instance.close()

    def test_poll(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = poll.PollPoll()
        socket = self._make_socket()
        instance.read_fd = {1: socket}
        instance.write_fd = {1: socket}

        self.assertEqual(self._poll(instance, select.POLLIN), ([socket], [], []))
        self.assertEqual(self._poll(instance, select.POLLOUT), ([], [socket], []))

        # both the error and the hang up conditions are reported as errors,
        # keeping the behaviour aligned with the remaining polls
        self.assertEqual(self._poll(instance, select.POLLERR), ([], [], [socket]))
        self.assertEqual(self._poll(instance, select.POLLHUP), ([], [], [socket]))

    def test_is_edge(self):
        # the poll based implementation is a level triggered one, so an
        # event is reported for as long as the condition holds
        self.assertEqual(poll.PollPoll().is_edge(), False)

    def test_sub_read(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket, owner="owner")

        # the first subscription registers the descriptor for the read
        # interest alone, as no other one has been asked for
        self.assertEqual(instance._poll.calls, [("register", 1, select.POLLIN)])
        self.assertEqual(instance.is_sub_read(socket), True)

        # a repeated subscription must not reach the poll again, avoiding an
        # already registered error being raised by it
        instance.sub_read(socket)
        self.assertEqual(len(instance._poll.calls), 1)

    def test_sub_read_write_subscribed(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_write(socket)
        instance.sub_read(socket)

        # the descriptor is already registered for the write interest, so the
        # read one is added to it through a modification
        self.assertEqual(
            instance._poll.calls[-1],
            ("modify", 1, select.POLLIN | select.POLLOUT),
        )

    def test_sub_write(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        # the write interest of a descriptor that is not registered has to
        # register it, instead of modifying a registration that is missing
        instance.sub_write(socket)
        self.assertEqual(instance._poll.calls, [("register", 1, select.POLLOUT)])
        self.assertEqual(instance.is_sub_write(socket), True)

        # a repeated subscription must not reach the poll again, avoiding an
        # already registered error being raised by it
        instance.sub_write(socket)
        self.assertEqual(len(instance._poll.calls), 1)

    def test_unsub_read(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.sub_write(socket)
        instance.unsub_read(socket)

        # dropping the read interest keeps the write one alive, so that a
        # pending write may still be flushed
        self.assertEqual(instance._poll.calls[-1], ("modify", 1, select.POLLOUT))
        self.assertEqual(instance.is_sub_read(socket), False)
        self.assertEqual(instance.is_sub_write(socket), True)

        # dropping the read interest of a socket that is not subscribed is a
        # no operation, leaving the poll untouched
        instance.unsub_read(socket)
        self.assertEqual(len(instance._poll.calls), 3)

    def test_unsub_read_only(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.unsub_read(socket)

        # with no other interest left the descriptor is taken out of the
        # poll, as an empty interest mask is not a valid registration
        self.assertEqual(instance._poll.calls[-1], ("unregister", 1))
        self.assertEqual(instance.is_empty(), True)
        self.assertEqual(1 in instance.read_fd, False)

    def test_unsub_write(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.sub_write(socket)
        instance.unsub_write(socket)

        # dropping the write interest keeps the read one alive, the poll
        # being modified rather than having the descriptor removed
        self.assertEqual(instance._poll.calls[-1], ("modify", 1, select.POLLIN))
        self.assertEqual(instance.is_sub_read(socket), True)
        self.assertEqual(instance.is_sub_write(socket), False)
        self.assertEqual(1 in instance.write_fd, False)

    def test_unsub_write_read_dropped(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = self._make_instance()
        socket = self._make_socket()

        instance.sub_read(socket)
        instance.sub_write(socket)
        instance.unsub_read(socket)
        instance.unsub_write(socket)

        # with the read interest already dropped the descriptor is taken out
        # of the poll instead of being modified, which would be rejected
        self.assertEqual(instance._poll.calls[-1], ("unregister", 1))
        self.assertEqual(instance.is_empty(), True)

        # the bookkeeping of the write interest is released even though the
        # descriptor was no longer registered for the read one
        self.assertEqual(1 in instance.write_fd, False)

    def _poll(self, instance, event):
        instance._poll = self._make_poll([(1, event)])
        return instance.poll()

    def _make_socket(self, fileno=1):
        # builds a socket stand-in that exposes the file descriptor under
        # which the interest operations are going to be registered
        class Socket(object):

            def fileno(self):
                return fileno

        return Socket()

    def _make_poll(self, events):
        # builds a poll stand-in that reports a fixed sequence of events, so
        # that the classification of them may be verified
        class Poll(object):

            def poll(self, *args, **kwargs):
                return events

        return Poll()

    def _make_instance(self):
        # builds a poll that is backed by a recording stand-in, so that no
        # real descriptor is required to verify the interest changes
        instance = poll.PollPoll()
        instance.read_fd = {}
        instance.write_fd = {}
        instance._poll = self._make_registry()
        return instance

    def _make_registry(self):
        # builds a poll stand-in that records the registration operations
        # performed on it, so that the interest changes may be verified
        class Poll(object):

            def __init__(self):
                self.calls = []

            def register(self, fd, mask):
                self.calls.append(("register", fd, mask))

            def modify(self, fd, mask):
                self.calls.append(("modify", fd, mask))

            def unregister(self, fd):
                self.calls.append(("unregister", fd))

        return Poll()


class SelectPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.SelectPoll.name(), "select")

    def test_test(self):
        # the select based poll is the fallback one and so it must be
        # available under every supported platform
        self.assertEqual(poll.SelectPoll.test(), True)

    def test_open(self):
        instance = poll.SelectPoll()
        instance.open(timeout=1.5)
        try:
            self.assertEqual(instance.is_open(), True)
            self.assertEqual(instance.timeout, 1.5)
            self.assertEqual(instance.is_empty(), True)
        finally:
            instance.close()

        # a negative timeout is normalized into an unset one, so that the
        # select call blocks until there's at least one event
        instance = poll.SelectPoll()
        instance.open(timeout=-1)
        try:
            self.assertEqual(instance.timeout, None)
        finally:
            instance.close()

    def test_close(self):
        instance = poll.SelectPoll()
        instance.open()
        instance.close()

        self.assertEqual(instance.is_open(), False)

    def test_poll(self):
        instance = poll.SelectPoll()
        instance.timeout = 0.01

        # an empty selection must not reach the select call, returning the
        # three empty sequences after a small sleep instead
        self.assertEqual(instance.poll(), ([], [], []))

    def test_is_edge(self):
        # the select based implementation is a level triggered one, as the
        # complete set of sockets is verified on every call
        self.assertEqual(poll.SelectPoll().is_edge(), False)
