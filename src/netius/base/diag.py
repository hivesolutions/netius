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
import logging

try:
    import appier
    loaded = True
except ImportError:
    import netius.mock
    appier = netius.mock.appier
    loaded = False

class DiagApp(appier.APIApp):

    def __init__(self, system, *args, **kwargs):
        appier.APIApp.__init__(
            self,
            name = "diag",
            *args, **kwargs
        )
        self.system = system

    @appier.route("/logger", "GET")
    def show_logger(self):
        level = self.system.logger.level
        level = logging.getLevelName(level)
        return dict(
            level = level
        )

    @appier.route("/logger/set", ("GET", "POST"))
    def set_logger(self):
        level = self.field("level", "DEBUG")
        self.system.level_logging(level)
        return self.show_logger()

    @appier.route("/environ", "GET")
    def show_environ(self):
        return self.json(dict(os.environ), sort_keys = True)

    @appier.route("/info", "GET")
    def system_info(self):
        full = self.field("full", True, cast = bool)
        info = self.system.info_dict(full = full)
        return self.json(info, sort_keys = True)

    @appier.route("/connections", "GET")
    def list_connections(self):
        full = self.field("full", True, cast = bool)
        info = self.system.connections_dict(full = full)
        return self.json(info, sort_keys = True)

    @appier.route("/connections/<str:id>", "GET")
    def show_connection(self, id):
        full = self.field("full", True, cast = bool)
        info = self.system.connection_dict(id, full = full)
        return self.json(info, sort_keys = True)
