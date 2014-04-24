#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import netius

from netius.auth import base

class MemoryAuth(base.Auth):

    @classmethod
    def auth(cls, username, password, *args, **kwargs):
        registry = cls.get_registry()
        register = registry.get(username, None)
        if not register: return False
        _password = register.get("password")
        return cls.verify(_password, password)

    @classmethod
    def get_registry(cls):
        if hasattr(cls, "registry"): return cls.registry
        cls.registry = cls.load_registry()
        return cls.registry

    @classmethod
    def load_registry(cls):
        return netius.conf("REGISTRY", {})
