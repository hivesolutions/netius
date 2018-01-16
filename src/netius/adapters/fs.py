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

import os
import ctypes

import netius

from . import base

class FsAdapter(base.BaseAdapter):

    def __init__(self, base_path = None):
        base.BaseAdapter.__init__(self)
        self.base_path = base_path or "fs.data"
        self.base_path = os.path.abspath(self.base_path)
        self.base_path = os.path.normpath(self.base_path)
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def set(self, value, owner = "nobody"):
        key = self.generate()
        owner_path = self._ensure(owner)
        file_path = os.path.join(self.base_path, key)
        link_path = os.path.join(owner_path, key)
        value = netius.legacy.bytes(value)
        file = open(file_path, "wb")
        try: file.write(value)
        finally: file.close()
        self._symlink(file_path, link_path)
        return key

    def get_file(self, key, mode = "rb"):
        file_path = os.path.join(self.base_path, key)
        file = open(file_path, mode)
        return file

    def delete(self, key, owner = "nobody"):
        owner_path = self._ensure(owner)
        file_path = os.path.join(self.base_path, key)
        link_path = os.path.join(owner_path, key)
        os.remove(file_path)
        os.remove(link_path)

    def size(self, key):
        file_path = os.path.join(self.base_path, key)
        return os.path.getsize(file_path)

    def count(self, owner = None):
        list = self.list(owner = owner)
        return len(list)

    def list(self, owner = None):
        path = self._path(owner = owner)
        exists = os.path.exists(path)
        files = os.listdir(path) if exists else []
        return files

    def _path(self, owner = None):
        if not owner: return self.base_path
        return os.path.join(self.base_path, owner)

    def _ensure(self, owner):
        owner_path = os.path.join(self.base_path, owner)
        if os.path.exists(owner_path): return owner_path
        os.makedirs(owner_path)
        return owner_path

    def _symlink(self, source, target):
        if os.name == "nt":
            symlink = ctypes.windll.kernel32.CreateSymbolicLinkW #@UndefinedVariable
            symlink.argtypes = (
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_uint32
            )
            symlink.restype = ctypes.c_ubyte
            flags = 1 if os.path.isdir(source) else 0
            result = symlink(target, source, flags)
            if result == 0: raise ctypes.WinError()
        else:
            os.symlink(source, target) #@UndefinedVariable
