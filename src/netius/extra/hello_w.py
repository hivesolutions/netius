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

"""netius.extra.hello_w

Tiny WSGI application that returns a plain text greeting, used as the
canonical example of running a WSGI callable under the Netius WSGI
server. Demonstrates the start response plus iterable body contract
with a single fixed message. Useful as a baseline when benchmarking
or validating the WSGI server integration.

Example:
    python -m netius.extra.hello_w
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius.servers


def app(environ, start_response):
    status = "200 OK"
    contents = "Hello World"
    content_l = len(contents)
    headers = (
        ("Content-Length", content_l),
        ("Content-type", "text/plain"),
        ("Connection", "keep-alive"),
    )
    start_response(status, headers)
    yield contents


if __name__ == "__main__":
    server = netius.servers.WSGIServer(app=app)
    server.serve(env=True)
else:
    __path__ = []
