#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

from . import observer

OPEN = 1
""" The open status value, meant to be used in situations
where the status of the entity is open (opposite of d) """

CLOSED = 2
""" Closed status value to be used in entities which have
no pending structured opened and operations are limited """

PENDING = 3
""" The pending status used for transient states (eg created)
connections under this state must be used carefully """

class Stream(observer.Observable):
    """
    Abstract stream class responsible for the representation of
    a "virtual" connection state for situation where multiplexing
    of single connection exists.

    Most of the interface for a stream should be "logically" similar
    to the one defined by a connection.
    """

    def __init__(self, owner = None):
        observer.Observable.__init__(self)
        self.status = PENDING
        self.owner = owner
        self.connection = owner.owner

    def reset(self):
        pass

    def open(self):
        if self.status == OPEN: return
        self.status = OPEN
        self.connection.owner.on_stream_c(self)

    def close(self):
        if self.status == CLOSED: return
        self.status = CLOSED
        self.connection.owner.on_stream_d(self)

    def info_dict(self, full = False):
        info = dict(
            status = self.status
        )
        return info

    def is_open(self):
        return self.status == OPEN

    def is_closed(self):
        return self.status == CLOSED

    def is_pending(self):
        return self.status == PENDING
