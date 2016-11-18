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

import netius

from . import proxy_r

class DockerProxyServer(proxy_r.ReverseProxyServer):

    def __init__(self, host_suffixes = [], *args, **kwargs):
        proxy_r.ReverseProxyServer.__init__(self, *args, **kwargs)
        self.load_config(host_suffixes = host_suffixes)
        self._build_docker()

    def on_serve(self):
        proxy_r.ReverseProxyServer.on_serve(self)
        if self.env: self.host_suffixes = self.get_env(
            "HOST_SUFFIXES",
            self.host_suffixes,
            cast = list
        )
        self._build_suffixes()

    def _build_docker(self):
        self._build_hosts()
        self._build_alias()
        self._build_passwords()

    def _build_hosts(self, alias = True):
        # tries to retrieve the complete set of configuration
        # values associated with the port suffix, this represents
        # the possible linked container addresses
        linked = netius.conf_suffix("_PORT")

        # iterates over the linked values, validating them and adding
        # them to the list of registered hosts
        for name, host in netius.legacy.iteritems(linked):
            # retrieves the name part of the configuration name
            # and converts it into lower cased value, note that
            # an extra dashed version is created, so that a proper
            # alias may be created for such naming
            base = name[:-5].lower()
            base_dash = base.replace("_", "-")

            # "builds" the name reference of the service and tries
            # to retrieve it from the configuration, it should exist
            # in case this port value represent a service
            name_ref = base.upper() + "_NAME"
            name_value = netius.conf(name_ref, None)

            # runs a series of validation on both the base and name
            # value to make sure that this value represents a valid
            # linked service/container
            if name.endswith("_ENV_PORT"): continue
            if base[-1].isdigit(): continue
            if not name_value: continue

            # replaces the prefix of the reference (assumes HTTP) and
            # then adds the base value to the registered hosts
            host = host.replace("tcp://", "http://")
            host = str(host)
            self.hosts[base] = host

            # validates that the dashed version of the name is not the
            # same as the base one (at least one underscore) and if that's
            # not the case skips the current iteration
            if base == base_dash: continue

            # checks if the alias based registration is enabled and adds
            # the dashed version as an alias for such case or as an host
            # otherwise (static registration)
            if alias: self.alias[base_dash] = base
            else: self.hosts[base_dash] = host

    def _build_alias(self):
        linked = netius.conf_suffix("_ALIAS")
        for name, host in netius.legacy.iteritems(linked):
            base = name[:-6].lower()
            base_dash = base.replace("_", "-")
            self.alias[base] = host
            self.alias[base_dash] = host

    def _build_passwords(self):
        linked = netius.conf_suffix("_PASSWORD")
        for name, password in netius.legacy.iteritems(linked):
            base = name[:-9].lower()
            base_dash = base.replace("_", "-")
            simple_auth = netius.SimpleAuth(password = password)
            self.auth[base] = simple_auth
            self.auth[base_dash] = simple_auth

    def _build_suffixes(self, alias = True):
        for host_suffix in self.host_suffixes:
            self.info("Registering %s host suffix" % host_suffix)
            for name, value in netius.legacy.items(self.hosts):
                fqn = name + "." + str(host_suffix)
                if alias: self.alias[fqn] = name
                else: self.hosts[fqn] = value
            for alias, value in netius.legacy.items(self.alias):
                fqn = alias + "." + str(host_suffix)
                self.alias[fqn] = value

if __name__ == "__main__":
    server = DockerProxyServer()
    server.serve(env = True)