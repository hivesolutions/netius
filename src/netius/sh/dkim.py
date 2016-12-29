#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import netius.common

from . import base

def generate(domain, suffix = None, number_bits = 1024):
    number_bits = int(number_bits)
    result = netius.common.dkim_generate(domain, suffix = suffix, number_bits = number_bits)
    print(result["dns_txt"])
    print(result["private_pem"])

def sign(email_path, key_path, selector, domain):
    file = open(email_path, "rb")
    try: contents = file.read()
    finally: file.close()

    contents = contents.lstrip()
    private_key = netius.common.open_private_key(key_path)
    signature = netius.common.dkim_sign(contents, selector, domain, private_key)

    file = open(email_path, "wb")
    try: file.write(signature); file.write(contents)
    finally: file.close()

if __name__ == "__main__":
    base.sh_call(globals(), locals())
else:
    __path__ = []
