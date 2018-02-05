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

import netius

from . import common

TASK_WORK = 10

class TaskThread(common.Thread):

    def execute(self, work):
        type = work[0]
        if not type == TASK_WORK: netius.NotImplemented(
            "Cannot execute type '%d'" % type
        )

        callable, args, kwargs, callback = work[1:]
        result = callable(*args, **kwargs)
        if callback: callback(result)

class TaskPool(common.EventPool):

    def __init__(self, base = TaskThread, count = 10):
        common.EventPool.__init__(self, base = base, count = count)

    def execute(self, callable, args = [], kwargs = {}, callback = None):
        work = (TASK_WORK, callable, args, kwargs, callback)
        self.push(work)
