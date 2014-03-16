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

import netius

DECIMAL_REGEX = re.compile(r"\d")
""" Simple regular expression that matched any
character and expression with decimal digits """

def bdecode(data):
    # converts the provide (string) data into a list
    # of chunks (characters) reversing it 
    chunks = list(data)
    chunks.reverse()
    root = dechunk(chunks)
    return root

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
        num = ""
        while not item == "e":
            num  += item
            item = chunks.pop()
        return int(num)

    elif DECIMAL_REGEX.search(item):
        num = ""
        while DECIMAL_REGEX.search(item):
            num += item
            item = chunks.pop()
        line = ""
        num = int(num)
        for _index in range(num):
            line += chunks.pop()
        return line

    raise netius.ParserError("Invalid input")
