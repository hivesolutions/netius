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

import sys
import time
import datetime
import threading

import netius

from .base import Middleware

class AnnoyerMiddleware(Middleware):
    """
    Simple middleware that prints an "annoying" status message
    to the standard output (stdout) from time to time providing
    a simple diagnostics strategy.
    """

    def __init__(self, owner, period = 10.0):
        Middleware.__init__(self, owner)
        self.period = period
        self._initial = None
        self._thread = None
        self._running = False

    def start(self):
        Middleware.start(self)
        self.period = netius.conf("ANNOYER_PERIOD", self.period, cast = float)
        self._thread = threading.Thread(target = self._run)
        self._thread.start()

    def stop(self):
        Middleware.stop(self)
        if self._thread:
            self._running = False
            self._thread.join()
            self._thread = None

    def _run(self):
        self._initial = datetime.datetime.utcnow()
        self._running = True
        while self._running:
            delta = datetime.datetime.utcnow() - self._initial
            delta_s = self.owner._format_delta(delta)
            message = "Uptime => %s | Connections => %d\n" %\
                (delta_s, len(self.owner.connections))
            sys.stdout.write(message)
            sys.stdout.flush()
            time.sleep(self.period)
