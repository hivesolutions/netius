#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

from .base import Middleware

class ProxyMiddleware(Middleware):
    """
    Middleware that implements the PROXY protocol on creation
    of a new connection enabling the passing of information
    from the front-end server to a back-end server using a normal
    TCP connection. This protocol has been development originally
    for the integration of an HAProxy server with back-end servers.

    :see: http://www.haproxy.org/download/1.5/doc/proxy-protocol.txt
    """

    def on_connection_c(self, connection):
        # @todo: must register the proper intention to perform a pending
        # operation in the socket
        print("received" + str(connection))

    def _proxy_handshake(self, socket):
        #@todo reads the data until the wanted values are found, then returns
        # some data to the buffer, if not properly read connnection.return(data)
        # then the recv() call in the connection would return that value naturally
        data = socket.recv()
