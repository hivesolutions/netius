#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

FILE_WORK = 10

OPEN_ACTION = 1
READ_ACTION = 2
WRITE_ACTION = 3

import netius
import ctypes

from netius.pool import common

class FileThread(common.Thread):

    def execute(self, work):
        type = work[0]
        if not type == FILE_WORK: netius.NotImplemented(
            "Cannot execute type '%d'" % type
        )

        action = work[1]
        if type == OPEN_ACTION: self.open(*work[2:])
        elif type == READ_ACTION: self.read(*work[2:])
        elif type == WRITE_ACTION: self.read(*work[2:])
        else: netius.NotImplemented("Undefined file action '%d'" % action)

    def open(self, path, mode, callback):
        file = open(path)
        callback(file)

    def read(self, file, count, callback):
        result = file.read(count)
        callback(result)

    def write(self, file, buffer, callback):
        file.write(buffer)
        callback()

class FilePool(common.ThreadPool):

    def __init__(self, base = FileThread, count = 10):
        common.ThreadPool.__init__(self, base = base, count = count)

    def open(self, path, mode = "r", callback = None):
        work = (FILE_WORK, OPEN_ACTION, path, mode, callback)
        self.push(work)

    def read(self, file, count = -1, callback = None):
        work = (FILE_WORK, READ_ACTION, file, count, callback)
        self.push(work)

    def write(self, file, buffer, callback = None):
        work = (FILE_WORK, WRITE_ACTION, file, buffer, callback)
        self.push(work)

    def eventfd(self, init_val = 0, flags = 0):
        try: self.libc = self.libc or ctypes.cdll.LoadLibrary("libc.so.6")
        except: return None
        return self.libc.eventfd(init_val, flags)
