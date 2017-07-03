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

BASE_STYLE = """<style>
@import \"https://fonts.googleapis.com/css?family=Open+Sans\";
body {
    color: #2d2d2d;
    font-family: -apple-system, \"BlinkMacSystemFont\", \"Segoe UI\", \"Roboto\", \"Open Sans\", \"Helvetica\", \"Arial\", sans-serif;
    font-size: 13px;
    line-height: 18px;
}
h1 {
    font-size: 22px;
    font-weight: 500;
    line-height: 26px;
    margin: 14px 0px 14px 0px;
}
a {
    color: #4769cc;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
hr {
    margin: 3px 0px 3px 0px;
}
table {
    font-size: 13px;
    line-height: 20px;
    max-width: 760px;
    table-layout: fixed;
    word-break: break-all;
}
table th {
    font-weight: 500;
}
table th > *, table td > * {
    vertical-align: middle;
}
table th > a {
    color: #2d2d2d;
}
table th > a.selected {
    font-weight: bold;
    text-decoration: underline;
}
table td > svg {
    color: #6d6d6d;
    fill: currentColor;
    margin-right: 6px;
}
.traceback {
    line-height: 26px;
    margin: 8px 0px 8px 0px;
}
@media screen and (max-width: 760px) {
    table th, table td {
        display: none;
    }
    table td:nth-child(1) {
        display: initial;
    }
}
</style>"""
