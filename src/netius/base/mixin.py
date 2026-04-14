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


class ConnectionCompat(object):
    """
    Mixin that delegates `Connection`-level attributes and
    methods through a `connection` property, allowing
    `Protocol` and `Transport` objects to be used transparently
    in code paths that still expect the older `Connection`
    interface (eg proxy servers, throttle callbacks).

    Host classes must provide a `connection` property
    that returns the underlying `Connection` instance
    (or `None` when unavailable).
    """

    @property
    def id(self):
        connection = self.connection
        if not connection:
            return None
        return connection.id

    @property
    def socket(self):
        connection = self.connection
        if not connection:
            return None
        return connection.socket

    @property
    def address(self):
        connection = self.connection
        if connection:
            return connection.address
        return getattr(self, "_address", None)

    @address.setter
    def address(self, value):
        self._address = value
        connection = self.connection
        if connection:
            connection.address = value

    @property
    def status(self):
        connection = self.connection
        if connection:
            return connection.status
        return getattr(self, "_status", None)

    @status.setter
    def status(self, value):
        self._status = value
        connection = self.connection
        if connection:
            connection.status = value

    @property
    def renable(self):
        connection = self.connection
        if not connection:
            return True
        return connection.renable

    @renable.setter
    def renable(self, value):
        connection = self.connection
        if not connection:
            return
        connection.renable = value

    def is_throttleable(self):
        connection = self.connection
        if not connection:
            return False
        return connection.is_throttleable()

    def is_exhausted(self):
        connection = self.connection
        if not connection:
            return False
        return connection.is_exhausted()

    def is_restored(self):
        connection = self.connection
        if not connection:
            return True
        return connection.is_restored()

    def disable_read(self):
        connection = self.connection
        if not connection:
            return
        connection.disable_read()

    def enable_read(self):
        connection = self.connection
        if not connection:
            return
        connection.enable_read()

    @property
    def max_pending(self):
        connection = self.connection
        if connection:
            return connection.max_pending
        return getattr(self, "_max_pending", -1)

    @max_pending.setter
    def max_pending(self, value):
        self._max_pending = value
        connection = self.connection
        if connection:
            connection.max_pending = value

    @property
    def min_pending(self):
        connection = self.connection
        if connection:
            return connection.min_pending
        return getattr(self, "_min_pending", -1)

    @min_pending.setter
    def min_pending(self, value):
        self._min_pending = value
        connection = self.connection
        if connection:
            connection.min_pending = value

    @property
    def waiting(self):
        connection = self.connection
        if connection:
            return getattr(connection, "waiting", False)
        return getattr(self, "_waiting", False)

    @waiting.setter
    def waiting(self, value):
        self._waiting = value
        connection = self.connection
        if connection:
            connection.waiting = value

    @property
    def busy(self):
        connection = self.connection
        if connection:
            return getattr(connection, "busy", 0)
        return getattr(self, "_busy", 0)

    @busy.setter
    def busy(self, value):
        self._busy = value
        connection = self.connection
        if connection:
            connection.busy = value

    @property
    def state(self):
        connection = self.connection
        if connection:
            return getattr(connection, "state", None)
        return getattr(self, "_state", None)

    @state.setter
    def state(self, value):
        self._state = value
        connection = self.connection
        if connection:
            connection.state = value

    @property
    def error_url(self):
        connection = self.connection
        if connection:
            return getattr(connection, "error_url", None)
        return getattr(self, "_error_url", None)

    @error_url.setter
    def error_url(self, value):
        self._error_url = value
        connection = self.connection
        if connection:
            connection.error_url = value
