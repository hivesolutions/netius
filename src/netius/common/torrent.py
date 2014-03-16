#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import re
import types

import netius

DECIMAL_REGEX = re.compile(r"\d")
""" Simple regular expression that matched any
character and expression with decimal digits """

def bencode(root):
    # joins the complete set of values created by
    # generator that has been returned from the chunk
    # function using the provided root value
    data = "".join([value for value in chunk(root)])
    return data

def bdecode(data):
    # converts the provide (string) data into a list
    # of chunks (characters) reversing it so that the
    # proper pop/push operations may be performed, as
    # pop is done from the back of the list
    chunks = list(data)
    chunks.reverse()

    # runs the dechunking operation in the created list
    # of chunks obtaining a dictionary base structure
    # as the result of the bencoding operation
    root = dechunk(chunks)
    return root

def chunk(item):
    chunk_t = type(item)

    if chunk_t == types.DictType:
        for key, value in item.iteritems():
            for part in chunk(key): yield part
            for part in chunk(value): yield part

    elif chunk_t == types.ListType:
        yield "l"
        for value in item:
            for part in chunk(value): yield part
        yield "e"

    elif chunk_t == types.IntType:
        yield "i%de" % item

    elif chunk_t in types.StringTypes:
        yield "%d:%s" % (len(item), item)

    else:
        raise netius.ParserError("Not possible to encode")

def dechunk(chunks):
    item = chunks.pop()

    if item == "d":
        item = chunks.pop()
        hash = {}

        while not item == "e":
            chunks.append(item)
            key = dechunk(chunks)
            hash[key] = dechunk(chunks)
            item = chunks.pop()

        return hash

    elif item == "l":
        item = chunks.pop()
        list = []

        while not item == "e":
            chunks.append(item)
            list.append(dechunk(chunks))
            item = chunks.pop()

        return list

    elif item == "i":
        item = chunks.pop()
        number = ""

        while not item == "e":
            number  += item
            item = chunks.pop()

        return int(number)

    elif DECIMAL_REGEX.search(item):
        number = ""

        while DECIMAL_REGEX.search(item):
            number += item
            item = chunks.pop()

        line = ""
        number = int(number)
        for _index in range(number):
            line += chunks.pop()

        return line

    raise netius.ParserError("Invalid input")
