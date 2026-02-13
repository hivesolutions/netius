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
    methods through a ``connection`` property, allowing
    protocol and transport objects to be used transparently
    in code paths that still expect the older `Connection`
    interface (eg proxy servers, throttle callbacks).

    Host classes must provide a ``connection`` property
    that returns the underlying `Connection` instance
    (or ``None`` when unavailable).
    """

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
