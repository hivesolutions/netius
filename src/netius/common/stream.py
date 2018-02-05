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

import netius

class Stream(object):

    def open(self, mode = "r+b"):
        raise netius.NotImplemented("Missing implementation")

    def close(self):
        raise netius.NotImplemented("Missing implementation")

    def seek(self, offset):
        raise netius.NotImplemented("Missing implementation")

    def read(self, size):
        raise netius.NotImplemented("Missing implementation")

    def write(self, data):
        raise netius.NotImplemented("Missing implementation")

    def flish(self):
        raise netius.NotImplemented("Missing implementation")

class FileStream(Stream):

    def __init__(self, path, size):
        Stream.__init__(self)
        self.path = path
        self.size = size
        self.file = None

    def open(self, mode = "w+b", allocate = True):
        self.file = open(self.path, mode)
        if not allocate: return
        self.file.seek(self.size - 1)
        self.file.write(b"\0")
        self.file.flush()

    def close(self):
        if not self.file: return
        self.file.close()
        self.file = None

    def seek(self, offset):
        self.file.seek(offset)

    def read(self, size):
        return self.file.read(size)

    def write(self, data):
        self.file.write(data)

    def flush(self):
        self.file.flush()

class FilesStream(Stream):

    def __init__(self, dir_path, size, files_m):
        Stream.__init__(self)
        self.dir_path = dir_path
        self.size = size
        self.files_m = files_m
        self.files = []
        self._offset = 0

    def open(self, mode = "w+b", allocate = True):
        for file_m in self.files_m:
            file_path = file_m["path"]
            file_size = file_m["length"]
            file_path = os.path.join(self.dir_path, *file_path)
            file = open(file_path, mode)
            file_t = (file, file_m)
            self.files.append(file_t)
            if not allocate: continue
            file.seek(file_size - 1)
            file.write(b"\0")
            file.flush()

    def close(self):
        if not self.files: return
        for file_t in self.files:
            file, _file_m = file_t
            file.close()
        del self.files[:]

    def seek(self, offset):
        self._offset = offset

    def read(self, size):
        # starts a series of local variables that are going to
        # be used to control the offsets for multiple file stream
        # operations, these values have local meaning
        file_offset = 0
        offset = self._offset
        pending = size
        data_l = []

        # iterates over the complete set of file to read the
        # partial contents from each of the corresponding files
        # note that a data chunk may span multiple files
        for file_t in self.files:
            # unpacks the file tuple into the file stream and
            # the meta information map, and uses it to retrieve
            # the total size in bytes for the current file
            file, file_m = file_t
            file_size = file_m["length"]

            # calculates the possible start offset of the data
            # chunk and verifies that it's valid, less that the
            # size of the current file, otherwise skips the current
            # iteration, must go further
            start = offset - file_offset
            file_offset += file_size
            if start >= file_size: continue

            # calculates the end internal offset value as the
            # minimum value between the file size and the start
            # offset plus pending number of bytes, then uses
            # this end offset value to calculate the total number
            # of bytes to be read from the current file
            end = min(file_size, start + pending)
            count = end - start

            # seeks the current file to the internal start offset
            # value and reads the partial data from the stream,
            # adding then the chunk to the data (chunks) lists
            file.seek(start)
            chunk = file.read(count)
            data_l.append(chunk)

            # updates the pending (bytes) and offset values to the
            # new values so that the new iteration is coherent
            pending -= count
            offset += count

            # verifies if there's no more data pending and if
            # that's the case break the current loop as no more
            # files are going to be affected
            if pending == 0: break

        # updates the current offset of the (virtual) file stream
        # with length of the data that has been read, then avoids
        # overflows by truncating the value to the size
        self._offset += size
        self._offset = min(self.size, self._offset)

        # joins the complete set of data chunks in the data list
        # and returns the (final) buffer to the caller method
        return b"".join(data_l)

    def write(self, data):
        # starts a series of local variables that are going to
        # be used to control the offsets for multiple file stream
        # operations, these values have local meaning
        file_offset = 0
        offset = self._offset
        data_l = len(data)
        pending = data_l

        # iterates over the complete set of file to write the
        # partial contents to each of the corresponding files
        # note that a data chunk may span multiple files
        for file_t in self.files:
            # unpacks the file tuple into the file stream and
            # the meta information map, and uses it to retrieve
            # the total size in bytes for the current file
            file, file_m = file_t
            file_size = file_m["length"]

            # calculates the possible start offset of the data
            # chunk and verifies that it's valid, less that the
            # size of the current file, otherwise skips the current
            # iteration, must go further
            start = offset - file_offset
            file_offset += file_size
            if start >= file_size: continue

            # calculates the end internal offset value as the
            # minimum value between the file size and the start
            # offset plus pending number of bytes, then uses
            # this end offset value to calculate the total number
            # of bytes to be written to the current file
            end = min(file_size, start + pending)
            count = end - start

            # seeks the current file to the internal start offset
            # value and writes the partial data to the stream,
            # flushing then the file (avoiding corruption)
            file.seek(start)
            file.write(data[:count])
            file.flush()

            # updates the data chunk with the remaining data
            # taking into account the written amount of bytes
            # and updates the pending (bytes) and offset values
            data = data[count:]
            pending -= count
            offset += count

            # verifies if there's no more data pending and if
            # that's the case break the current loop as no more
            # files are going to be affected
            if pending == 0: break

        # updates the current offset of the (virtual) file stream
        # with length of the data that has just been written, then
        # avoids overflows by truncating the value to the size
        self._offset += data_l
        self._offset = min(self.size, self._offset)

    def flush(self):
        for file_t in self.files:
            file, _file_m = file_t
            file.flush()
