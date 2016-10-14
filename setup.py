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

import os
import sys
import setuptools

BASE_PATH = os.path.realpath(__file__)
BASE_DIR = os.path.dirname(BASE_PATH)
SRC_DIR = os.path.join(BASE_DIR, "src")
NETIUS_DIR = os.path.join(SRC_DIR, "netius")
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, NETIUS_DIR)

import netius.common

netius.common.ensure_setup()
setuptools.setup(
    name = "netius",
    version = "1.10.10",
    author = "Hive Solutions Lda.",
    author_email = "development@hive.pt",
    description = "Netius System",
    license = "Apache License, Version 2.0",
    keywords = "netius net infrastructure wsgi",
    url = "http://netius.hive.pt",
    zip_safe = False,
    packages = [
        "netius",
        "netius.adapters",
        "netius.auth",
        "netius.base",
        "netius.clients",
        "netius.common",
        "netius.examples",
        "netius.extra",
        "netius.mock",
        "netius.pool",
        "netius.servers",
        "netius.sh",
        "netius.test"
    ],
    test_suite = "netius.test",
    package_dir = {
        "" : os.path.normpath("src")
    },
    package_data = {
        "netius" : ["base/extras/*", "extra/extras/*", "servers/extras/*"]
    },
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5"
    ]
)
