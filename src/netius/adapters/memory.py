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

from . import base

class MemoryAdapter(base.BaseAdapter):

    def __init__(self):
        base.BaseAdapter.__init__(self)
        self.map = dict()
        self.owners = dict()

    def set(self, value, owner = "nobody"):
        map_o = self._ensure(owner)
        key = self.generate()
        item = dict(value = value, owner = owner)
        self.map[key] = item
        map_o[key] = item
        return key

    def get_file(self, key, mode = "rb"):
        if not key in self.map: netius.NetiusError("Key not found")
        item = self.map[key]
        value = item["value"]
        file = netius.legacy.StringIO(value)
        close = self._build_close(file, key)
        file._close = file.close
        file.close = close
        return file

    def delete(self, key, owner = "nobody"):
        item = self.map[key]
        owner = item["owner"]
        map_o = self._ensure(owner)
        del self.map[key]
        del map_o[key]

    def append(self, key, value):
        item = self.map[key]
        _value = item["value"]
        _value += value
        item["value"] = _value

    def truncate(self, key, count):
        item = self.map[key]
        _value = item["value"]
        offset = count * -1
        _value = _value[:offset]
        item["value"] = _value

    def size(self, key):
        item = self.map[key]
        _value = item["value"]
        return len(_value)

    def count(self, owner = None):
        map = self._ensure(owner) if owner else self.map
        return len(map)

    def list(self, owner = None):
        map = self._ensure(owner) if owner else self.map
        return map.keys()

    def _ensure(self, owner):
        map = self.owners.get(owner, {})
        self.owners[owner] = map
        return map

    def _build_close(self, file, key):

        def close():
            value = file.getvalue()
            item = self.map[key]
            item["value"] = value
            file._close()

        return close
