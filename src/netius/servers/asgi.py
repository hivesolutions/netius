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

"""netius.servers.asgi

ASGI compliant server built on top of the Netius HTTP/2 server. Acts as
the single import point for the ASGI infra-structure, selecting the proper
implementation for the running interpreter, as the interface is built on
top of the async/await syntax that the older ones do not support.

The application to be served may be provided through the APP environment
variable using the module and attribute notation (eg: my_module:app),
otherwise a simple hello world one is used instead.

Example:
    python -m netius.servers.asgi
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os

import netius

from . import http2

UNSUPPORTED_MESSAGE = "ASGI requires an interpreter with async/await support"
""" The message of the error that is raised whenever the ASGI
infra-structure is used under an interpreter that is not able to
run the async/await based implementation of it """

# verifies if the current python interpreter version supports the
# async/await syntax and if that's the case runs the import of the
# symbols of the "real" implementation of the ASGI server
if netius.is_neo():
    from .asgi_neo import *  # @UnusedWildImport pylint: disable=W0614

# otherwise creates the stub versions of the public symbols, so that
# both the import of the servers package and the introspection of it
# remain possible under the older interpreters
else:

    class ASGIServer(http2.HTTP2Server):
        """
        Stub version of the ASGI server for the interpreters that are
        not able to run the async/await based implementation of it.
        """

        def __init__(self, *args, **kwargs):
            raise netius.NetiusError(UNSUPPORTED_MESSAGE)

    def hello_app(*args, **kwargs):
        raise netius.NetiusError(UNSUPPORTED_MESSAGE)

    def load_app(value):
        raise netius.NetiusError(UNSUPPORTED_MESSAGE)


if __name__ == "__main__":
    import logging

    # tries to retrieve the reference to the application to be served
    # from the environment, falling back to the demo one in case no
    # such reference is defined (typical usage scenario)
    app_s = os.environ.get("APP", None)
    app = load_app(app_s) if app_s else hello_app

    server = ASGIServer(app=app, level=logging.INFO)
    server.serve(env=True)
else:
    __path__ = []
