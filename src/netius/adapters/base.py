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

import os
import uuid
import hashlib
import StringIO

class BaseAdapter(object):
    """
    Top level abstract representation of a netius adapter.
    The adapter is responsible for the storage/retrieval
    of key based values, and may be used as the storage
    engine back-end for a series or purposes (eg: email
    storage, torrent hash table storage, sessions, etc.)
    """

    def set(self, value, owner = "nobody"):
        pass

    def get(self, key):
        file = self.get_file(key)
        if not file: return file
        try: value = file.read()
        finally: file.close()
        return value

    def get_file(self, key, mode = "rb"):
        return StringIO.StringIO()

    def delete(self, key, owner = "nobody"):
        pass

    def append(self, key, value):
        file = self.get_file(key, mode = "ab")
        try: file.write(value)
        finally: file.close()

    def truncate(self, key, count):
        file = self.get_file(key, mode = "r+")
        try:
            offset = count * -1
            file.seek(offset, os.SEEK_END)
            file.truncate()
        finally:
            file.close()

    def size(self, key):
        return 0

    def sizes(self, owner = None):
        list = self.list(owner = owner)
        sizes = [self.size(key) for key in list]
        return sizes

    def total(self, owner = None):
        total = 0
        list = self.list(owner = owner)
        for key in list: total += self.size(key)
        return total

    def reserve(self, owner = "nobody"):
        return self.set("", owner = owner)

    def count(self, owner = None):
        return 0

    def list(self, owner = None):
        return ()

    def generate(self):
        identifier = str(uuid.uuid4())
        hash = hashlib.sha256(identifier)
        key = hash.hexdigest()
        return key
