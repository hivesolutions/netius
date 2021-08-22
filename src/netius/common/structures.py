#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import heapq

class PriorityDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._rebuild_heap()

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

        if len(self._heap) < len(self) * 2:
            heapq.heappush(self._heap, (val, key))
        else:
            self._rebuild_heap()

    def smallest(self):
        heap = self._heap
        v, k = heap[0]
        while not k in self or self[k] != v:
            heapq.heappop(heap)
            v, k = heap[0]
        return k

    def pop_smallest(self):
        heap = self._heap
        v, k = heapq.heappop(heap)
        while not k in self or self[k] != v:
            v, k = heapq.heappop(heap)
        del self[k]
        return k

    def setdefault(self, key, val):
        if not key in self:
            self[key] = val
            return val
        return self[key]

    def update(self, *args, **kwargs):
        dict.update(self, *args, **kwargs)
        self._rebuild_heap()

    def sorted_iter(self):
        while self: yield self.pop_smallest()

    def _rebuild_heap(self):
        self._heap = [(v, k) for k, v in self.items()]
        heapq.heapify(self._heap)

def file_iterator(file_object, chunk_size = 40960):
    file_object.seek(0, os.SEEK_END)
    size = file_object.tell()
    file_object.seek(0, os.SEEK_SET)
    yield size
    while True:
        data = file_object.read(chunk_size)
        if not data: break
        yield data
