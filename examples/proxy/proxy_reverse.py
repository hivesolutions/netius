#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

"""
Simple reverse proxy that forwards all incoming HTTP requests
to httpbin.org and relays the responses back to the client,
run it from the repository root with::

    PYTHONPATH=src python examples/proxy/proxy_reverse.py

then try::

    curl -H "Host: httpbin.org" http://localhost:8080/get
    curl -H "Host: httpbin.org" http://localhost:8080/headers
    curl -H "Host: httpbin.org" http://localhost:8080/ip
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import logging

import netius.extra

server = netius.extra.ReverseProxyServer(
    hosts={"default": "http://httpbin.org"},
    level=logging.INFO,
)
server.serve(host="127.0.0.1", port=8080, env=True)
