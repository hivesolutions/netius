#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import StringIO

import netius

import base

class MemoryAdapter(base.BaseAdapter):

    def __init__(self):
        base.BaseAdapter.__init__(self)
        self.map = dict()

    def set(self, value, owner = "nobody"):
        key = self.generate()
        self.map[key] = value
        return key

    def get_file(self, key, mode = "rb"):
        if not key in self.map: netius.NetiusError("Key not found")
        value = self.map[key]
        file = StringIO.StringIO(value)
        close = self._build_close(file, key)
        _close = file.close
        file._close = _close
        file.close = close
        return file

    def delete(self, key):
        del self.map[key]

    def append(self, key, value):
        _value = self.map[key]
        _value += value
        self.map[key] = _value

    def truncate(self, key, count):
        _value = self.map[key]
        offset = count * -1
        _value = _value[:offset]
        self.map[key] = _value

    def size(self, key):
        _value = self.map[key]
        return len(_value)

    def count(self):
        return len(self.map)

    def list(self):
        return self.map.keys()

    def _build_close(self, file, key):

        def close():
            value = file.getvalue()
            self.map[key] = value
            file._close()

        return close
