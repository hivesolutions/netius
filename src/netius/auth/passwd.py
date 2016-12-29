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

import os

from . import base

class PasswdAuth(base.Auth):

    def __init__(self, path = None, *args, **kwargs):
        base.Auth.__init__(self, *args, **kwargs)
        self.path = path

    @classmethod
    def auth(cls, username, password, path = "passwd", *args, **kwargs):
        passwd = cls.get_passwd(path)
        _password = passwd.get(username, None)
        if not _password: return False
        return cls.verify(_password, password)

    @classmethod
    def get_passwd(cls, path, cache = True):
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        path = os.path.normpath(path)

        if not hasattr(cls, "_pwcache"): cls._pwcache = dict()

        result = cls._pwcache.get(path, None) if hasattr(cls, "_pwcache") else None
        if cache and not result == None: return result

        htpasswd = dict()
        contents = cls.get_file(path, cache = cache, encoding = "utf-8")
        for line in contents.split("\n"):
            line = line.strip()
            if not line: continue
            username, password = line.split(":", 1)
            htpasswd[username] = password

        if cache: cls._pwcache[path] = htpasswd
        return htpasswd

    def auth_i(self, username, password, *args, **kwargs):
        return self.__class__.auth(
            username,
            password,
            path = self.path,
            *args,
            **kwargs
        )
