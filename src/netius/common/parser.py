#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius

class Parser(netius.Observable):

    FIELDS = ("_pid",)

    def __init__(self, owner):
        netius.Observable.__init__(self)
        self.owner = owner
        self._pid = 0

    @classmethod
    def mock(cls, owner, state):
        mock = cls(owner)
        mock.set_state(state)
        return mock

    def build(self):
        netius.Observable.build(self)

    def destroy(self):
        netius.Observable.destroy(self)
        self.owner = None
        self._pid = 0

    def get_state(self):
        cls = self.__class__
        fields = cls.FIELDS
        state = dict()
        for field in fields:
            state[field] = getattr(self, field)
        return state

    def set_state(self, state):
        cls = self.__class__
        fields = cls.FIELDS
        for field in fields:
            value = state[field]
            setattr(self, field, value)

    def info_dict(self):
        info = self.get_state()
        return info

    def parse(self, data):
        self._pid = (self._pid + 1) % 2147483647
