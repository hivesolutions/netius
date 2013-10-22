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

class Poll(object):
    
    def poll(self):
        return []
    
    def sub_all(self, socket, owner = None):
        self.sub_read(socket, owner = owner)
        self.sub_write(socket, owner = owner)
        self.sub_error(socket, owner = owner)

    def unsub_all(self, socket, owner = None):
        self.unsub_read(socket, owner = owner)
        self.unsub_write(socket, owner = owner)
        self.unsub_error(socket, owner = owner)

    def sub_read(self, socket, owner = None):
        pass

    def sub_write(self, socket, owner = None):
        pass

    def sub_error(self, socket, owner = None):
        pass

    def unsub_read(self, socket, owner = None):
        pass

    def unsub_write(self, socket, owner = None):
        pass

    def unsub_error(self, socket, owner = None):
        pass

class SelectPoll(Poll):
    
    def __init__(self, *args, **kwargs):
        Poll.__init__(self, *args, **kwargs)
        self.read_l = []
        self.write_l = []
        self.error_l = []

    def sub_read(self, socket, owner = None):
        self.read_l.append(socket)

    def sub_write(self, socket, owner = None):
        self.write_l.append(socket)

    def sub_error(self, socket, owner = None):
        self.error_l.append(socket)

    def unsub_read(self, socket, owner = None):
        if not socket in self.read_l: return
        self.read_l.append(socket)

    def unsub_write(self, socket, owner = None):
        if not socket in self.write_l: return
        self.write_l.append(socket)

    def unsub_error(self, socket, owner = None):
        if not socket in self.error_l: return
        self.error_l.append(socket)
