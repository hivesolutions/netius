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

    def _make_socket(self, fileno=1):
        # builds a socket stand-in, the base poll only uses it as a key so
        # no file descriptor operations are required for it
        Socket = collections.namedtuple("Socket", "name")
        return Socket(name="socket-%d" % fileno)


class EpollPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.EpollPoll.name(), "epoll")

    def test_test(self):
        self.assertEqual(poll.EpollPoll.test() in (True, False), True)

    def test_poll(self):
        if not poll.EpollPoll.test():
            self.skipTest("Skipping test: epoll unavailable")

        instance = poll.EpollPoll()
        socket = _Socket()
        instance.fd_m = {socket.fileno(): socket}

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

    def _poll(self, instance, event):
        instance.epoll = _Epoll([(1, event)])
        return instance.poll()


class KqueuePollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.KqueuePoll.name(), "kqueue")

    def test_test(self):
        self.assertEqual(poll.KqueuePoll.test() in (True, False), True)

    def test_poll(self):
        if not poll.KqueuePoll.test():
            self.skipTest("Skipping test: kqueue unavailable")

        instance = poll.KqueuePoll()
        socket = _Socket()
        instance.fd_m = {socket.fileno(): socket}

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

    def _poll(self, instance, filter, flags):
        Event = collections.namedtuple("Event", "filter flags udata")
        instance.kqueue = _Kqueue([Event(filter=filter, flags=flags, udata=1)])
        return instance.poll()


class PollPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.PollPoll.name(), "poll")

    def test_test(self):
        self.assertEqual(poll.PollPoll.test() in (True, False), True)

    def test_poll(self):
        if not poll.PollPoll.test():
            self.skipTest("Skipping test: poll unavailable")

        instance = poll.PollPoll()
        socket = _Socket()
        instance.read_fd = {socket.fileno(): socket}
        instance.write_fd = {socket.fileno(): socket}

        self.assertEqual(self._poll(instance, select.POLLIN), ([socket], [], []))
        self.assertEqual(self._poll(instance, select.POLLOUT), ([], [socket], []))

        # both the error and the hang up conditions are reported as errors,
        # keeping the behaviour aligned with the remaining polls
        self.assertEqual(self._poll(instance, select.POLLERR), ([], [], [socket]))
        self.assertEqual(self._poll(instance, select.POLLHUP), ([], [], [socket]))

    def _poll(self, instance, event):
        instance._poll = _Epoll([(1, event)])
        return instance.poll()


class SelectPollTest(unittest.TestCase):

    def test_name(self):
        self.assertEqual(poll.SelectPoll.name(), "select")

    def test_test(self):
        # the select based poll is the fallback one and so it must be
        # available under every supported platform
        self.assertEqual(poll.SelectPoll.test(), True)

    def test_poll(self):
        instance = poll.SelectPoll()
        instance.timeout = 0.01

        # an empty selection must not reach the select call, returning the
        # three empty sequences after a small sleep instead
        self.assertEqual(instance.poll(), ([], [], []))


class _Socket(object):
    """
    Socket stand-in that reports a fixed file descriptor, so that the
    mapping performed by the polls may be exercised.
    """

    def fileno(self):
        return 1


class _Epoll(object):
    """
    Stand-in for the epoll (and poll) objects, reporting a fixed sequence
    of events so that their classification may be verified.
    """

    def __init__(self, events):
        self.events = events

    def poll(self, *args, **kwargs):
        return self.events


class _Kqueue(object):
    """
    Stand-in for the kqueue object, reporting a fixed sequence of events
    so that their classification may be verified.
    """

    def __init__(self, events):
        self.events = events

    def control(self, *args, **kwargs):
        return self.events
