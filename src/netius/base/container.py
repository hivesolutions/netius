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

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

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

from common import * #@UnusedWildImport

class Container(Base):

    def __init__(self, *args, **kwargs):
        Base.__init__(self, *args, **kwargs)
        self.bases = []

        self.bind("start", self.on_start)

    def cleanup(self):
        Base.cleanup(self)
        for base in self.bases: base.cleanup()

    def loop(self):
        # iterates continuously while the running flag
        # is set, once it becomes unset the loop breaks
        # at the next execution cycle
        while self._running:
            # calls the base tick int handler indicating that a new
            # tick loop iteration is going to be started, all the
            # "in between loop" operation should be performed in this
            # callback as this is the "space" they have for execution
            self.ticks()

            # updates the current state to poll to indicate
            # that the base service is selecting the connections
            self.set_state(STATE_POLL)

            # runs the "owner" based version of the poll operation
            # so that the poll results are indexed by their owner
            # reference to be easily routed to the base services
            result = self.poll.poll_owner()
            for base, values in result.iteritems():
                reads, writes, errors = values
                base.reads(reads)
                base.writes(writes)
                base.errors(errors)

    def ticks(self):
        self.set_state(STATE_TICK)
        self._lid = (self._lid + 1) % 2147483647
        for base in self.bases: base.ticks()

    def on_start(self, service):
        self.apply_all()

    def add_base(self, base):
        self.apply_base(base)
        self.bases.append(base)

    def apply_all(self):
        for base in self.bases: self.apply_base(base)

    def apply_base(self, base):
        base.tid = self.tid
        base.poll = self.poll
