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

import inspect

import logging.handlers

SILENT = logging.CRITICAL + 1
""" The "artificial" silent level used to silent a logger
or an handler, this is used as an utility for debugging
purposes more that a real feature for production systems """

def rotating_handler(
    path = "netius.log",
    max_bytes = 1048576,
    max_log = 5,
    encoding = None,
    delay = False
):
    return logging.handlers.RotatingFileHandler(
        path,
        maxBytes = max_bytes,
        backupCount = max_log,
        encoding = encoding,
        delay = delay
    )

def smtp_handler(
    host = "localhost",
    port = 25,
    sender = "no-reply@netius.com",
    receivers = [],
    subject = "Netius logging",
    username = None,
    password = None,
    stls = False
):
    address = (host, port)
    if username and password: credentials = (username, password)
    else: credentials = None
    has_secure = in_signature(logging.handlers.SMTPHandler.__init__, "secure")
    if has_secure: kwargs = dict(secure = () if stls else None)
    else: kwargs = dict()
    return logging.handlers.SMTPHandler(
        address,
        sender,
        receivers,
        subject,
        credentials = credentials,
        **kwargs
    )

def in_signature(callable, name):
    has_full = hasattr(inspect, "getfullargspec")
    if has_full: spec = inspect.getfullargspec(callable)
    else: spec = inspect.getargspec(callable)
    args, _varargs, kwargs = spec[:3]
    return (args and name in args) or (kwargs and "secure" in kwargs)
