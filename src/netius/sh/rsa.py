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

"""netius.sh.rsa

Command line tools for inspecting and converting RSA keys. Provides
sub commands to pretty print the contents of a private or public key
file and to derive a public key from an existing private key, writing
it to disk. Builds on the common RSA helpers shipped with Netius.
Handy for quick key inspection during development.

Example:
    python -m netius.sh.rsa read_private private.key
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import pprint

import netius.common

from . import base


def read_private(path):
    private_key = netius.common.open_private_key(path)
    pprint.pprint(private_key)


def read_public(path):
    public_key = netius.common.open_public_key(path)
    pprint.pprint(public_key)


def private_to_public(private_path, public_path):
    private_key = netius.common.open_private_key(private_path)
    public_key = netius.common.private_to_public(private_key)
    netius.common.write_public_key(public_path, public_key)


if __name__ == "__main__":
    base.sh_call(globals(), locals())
else:
    __path__ = []
