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

from . import desktop
from . import dhcp_s
from . import file
from . import filea
from . import hello_w
from . import hello
from . import proxy_d
from . import proxy_f
from . import proxy_r
from . import smtp_r

from .desktop import DesktopServer
from .dhcp_s import DHCPServerS
from .file import FileServer
from .filea import FileAsyncServer
from .hello import HelloServer
from .proxy_d import DockerProxyServer
from .proxy_f import ForwardProxyServer
from .proxy_r import ReverseProxyServer
from .smtp_r import RelaySMTPServer
