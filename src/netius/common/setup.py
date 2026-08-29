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

"""netius.common.setup

First-run setup helpers for the Netius package, mostly focused on
ensuring the bundled certificate authority (CA) bundle is present.
Downloads the CA file from a remote source when missing, following
any HTTP redirects, and stores it under the base extras directory.
Used to guarantee TLS verification has a trust store available.
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os

CA_URL = "https://curl.se/ca/cacert.pem"

COMMON_PATH = os.path.dirname(__file__)
BASE_PATH = os.path.join(COMMON_PATH, "..", "base")
EXTRAS_PATH = os.path.join(BASE_PATH, "extras")
SSL_CA_PATH = os.path.join(EXTRAS_PATH, "net.ca")


def ensure_setup():
    # the setup of the package must not be broken by a download that fails,
    # as the CA file is an optional resource, the infra-structure falls back
    # to the trust store of the system whenever it's not present
    ensure_ca(raise_e=False)


def ensure_ca(path=SSL_CA_PATH, raise_e=True):
    if os.path.exists(path):
        return
    _download_ca(path=path, raise_e=raise_e)


def _download_ca(path=SSL_CA_PATH, raise_e=True):
    import netius.clients

    ca_url = CA_URL
    while True:
        result = netius.clients.HTTPClient.method_s("GET", ca_url, asynchronous=False)
        if not result["code"] in (301, 302, 303):
            break
        headers = result.get("headers", {})
        location = headers.get("Location", None)
        if not location:
            break
        ca_url = location
    if not result["code"] == 200:
        if not raise_e:
            return

        # a request that never reached a response carries no status code, so
        # the reason for the failure is the one that has to be reported
        message = result.get("message", None)
        raise Exception(
            "Error while downloading CA file from '%s' (code: %s, message: %s)"
            % (CA_URL, result["code"], message)
        )
    response = netius.clients.HTTPClient.to_response(result)
    contents = response.read()
    _store_contents(contents, path)


def _store_contents(contents, path):
    file = open(path, "wb")
    try:
        file.write(contents)
    finally:
        file.close()
    return path
