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

import netius.clients

CA_URL = "https://curl.haxx.se/ca/cacert.pem"

COMMON_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.join(COMMON_PATH, "..", "base")
EXTRAS_PATH = os.path.join(BASE_PATH, "extras")
SSL_CA_PATH = os.path.join(EXTRAS_PATH, "net.ca")

def ensure_setup():
    ensure_ca()

def ensure_ca(path = SSL_CA_PATH):
    if os.path.exists(path): return
    _download_ca(path = path)

def _download_ca(path = SSL_CA_PATH):
    result = netius.clients.HTTPClient.method_s(
        "GET",
        CA_URL,
        async = False
    )
    response = netius.clients.HTTPClient.to_response(result)
    contents = response.read()
    _store_contents(contents, path)

def _store_contents(contents, path):
    file = open(path, "wb")
    try: file.write(contents)
    finally: file.close()
    return path
