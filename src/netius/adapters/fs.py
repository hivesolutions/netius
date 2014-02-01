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
import ctypes

import base

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
        file_path = os.path.join(self.base_path, key)
        file = open(file_path, "wb")
        try: file.write(value)
        finally: file.close()
        return key

    def get_file(self, key, mode = "rb"):
        file_path = os.path.join(self.base_path, key)
        file = open(file_path, mode)
        return file

    def delete(self, key):
        file_path = os.path.join(self.base_path, key)
        os.remove(file_path)

    def size(self, key):
        file_path = os.path.join(self.base_path, key)
        return os.path.getsize(file_path)

    def count(self):
        files = os.listdir(self.base_path)
        return len(files)

    def list(self):
        files = os.listdir(self.base_path)
        return files

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
