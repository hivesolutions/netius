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

import netius

class SSLContextDict(dict):

    def __init__(self, owner, domains, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.owner = owner
        self.load(domains)

    def load(self, domains):
        secure = self.owner.get_env("SSL_SECURE", True, cast = bool)
        for domain in domains:
            if not self.has_definition(domain): continue
            cer_path = self.cer_path(domain)
            key_path = self.key_path(domain)
            values = dict(cer_file = cer_path, key_file = key_path)
            context = self.owner._ssl_ctx(values, secure = secure)
            self[domain] = (context, values)

    def has_definition(self, domain):
        cer_path = self.cer_path(domain)
        key_path = self.key_path(domain)
        if not os.path.exists(cer_path): return False
        if not os.path.exists(key_path): return False
        return True

    def cer_path(self, domain):
        raise netius.NotImplemented("Missing implementation")

def LetsEncryptDict(SSLContextDict):

    def __init__(self, owner, domains, *args, **kwargs):
        dict.__init__(self, owner, domains, *args, **kwargs)
        self.letse_path = kwargs.get("letse_path", "/data/letsencrypt/etc/live")

    def cer_path(self, domain):
        domain_path = os.path.join(self.letse_path, domain)
        return os.path.join(domain_path, "fullchain.pem")

    def key_path(self, domain):
        domain_path = os.path.join(self.letse_path, domain)
        return os.path.join(domain_path, "privkey.pem")
