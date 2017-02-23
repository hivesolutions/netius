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

import asyncio

import urllib.parse

import netius

@asyncio.coroutine
def print_http_headers(url, encoding = "utf-8"):
    url = urllib.parse.urlsplit(url)
    if url.scheme == "https":
        connect = asyncio.open_connection(url.hostname, 443, ssl = True)
    else:
        connect = asyncio.open_connection(url.hostname, 80)
    reader, writer = yield from connect
    query = "HEAD {path} HTTP/1.0\r\n" + "Host: {hostname}\r\n" + "\r\n"
    query = query.format(path = url.path or "/", hostname = url.hostname)
    writer.write(query.encode(encoding))

    while True:
        line = yield from reader.readline()
        if not line: break
        line = line.decode(encoding).rstrip()
        if line: print("HTTP header> %s" % line)

    writer.close()

loop = netius.get_loop()
task = asyncio.ensure_future(print_http_headers("https://www.flickr.com/"))
loop.run_until_complete(task)
loop.close()
