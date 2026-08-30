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

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius
import netius.extra


class DockerProxyServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.names = []
        self.servers = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for name in self.names:
            netius.config.conf_r(name)
        for server in self.servers:
            server.cleanup()

    def test_init(self):
        self._conf(NETIUS_D_PORT="tcp://first:80", NETIUS_D_NAME="/netius_d")

        server = self._make_server()

        # the building of the configuration is run by the constructor, so
        # the linked container is already registered by then
        self.assertEqual(server.hosts["netius_d"], "http://first:80")
        self.assertEqual(server.host_suffixes, [])

    def test_init_suffixes(self):
        server = self._make_server(host_suffixes=["local"])

        self.assertEqual(server.host_suffixes, ["local"])

    def test_on_serve(self):
        self._conf(NETIUS_D_REDIRECT_SSL="1")

        server = self._make_server(host_suffixes=["local"])
        server.env = False
        server.alias = dict(other="netius_d")
        server.redirect = {}

        server.on_serve()

        # the serving registers the suffixed names and the redirections
        # towards the secure scheme, which the constructor cannot know
        self.assertEqual(server.alias["other.local"], "netius_d")
        self.assertEqual(server.redirect["netius_d"], ("netius_d", "https"))

    def test_on_serve_env(self):
        self._conf(HOST_SUFFIXES="first;second")

        server = self._make_server()
        server.env = True
        server.alias = dict(other="netius_d")

        server.on_serve()

        # with the environment in use the suffixes are taken from it,
        # replacing the ones that the constructor was given
        self.assertEqual(server.host_suffixes, ["first", "second"])
        self.assertEqual(server.alias["other.first"], "netius_d")
        self.assertEqual(server.alias["other.second"], "netius_d")

    def test__build_regex(self):
        server = self._make_server()
        server.regex = []

        self._conf(
            NETIUS_D_REGEX="^/first.*$http://first:80",
            NETIUS_D_BROKEN_REGEX="no-token-at-all",
            NETIUS_D_INVALID_REGEX="^/second.*$not-a-url",
        )

        server._build_regex()

        # only the value that carries both a rule and a valid target is
        # registered, the other two being dropped
        self.assertEqual(len(server.regex), 1)
        self.assertEqual(server.regex[0][0].pattern, "^/first.*")
        self.assertEqual(server.regex[0][1], "http://first:80")

    def test__build_regex_sort(self):
        server = self._make_server()
        server.regex = []

        self._conf(
            NETIUS_D_SECOND_REGEX="^/second$http://second:80",
            NETIUS_D_FIRST_REGEX="^/first$http://first:80",
        )

        server._build_regex()

        # the names are walked in order, so that the rules are registered
        # in a way that does not depend on the order of the configuration
        targets = [target for _regex, target in server.regex]
        self.assertEqual(
            targets.index("http://first:80") < targets.index("http://second:80"), True
        )

        server.regex = []
        server._build_regex(sort=False)

        # without the sorting the rules are still every one of them, only
        # the order in which they are walked is no longer settled
        self.assertEqual(len(server.regex), 2)

    def test__build_hosts(self):
        server = self._make_server()

        self._conf(NETIUS_D_PORT="tcp://first:80", NETIUS_D_NAME="/netius_d")

        server.hosts = {}
        server._build_hosts()

        # the scheme of the link is replaced by an HTTP one, as that is
        # the protocol that the proxy speaks with the container
        self.assertEqual(server.hosts["netius_d"], "http://first:80")

        # the name of the link has an underscore, so a dashed alias of it
        # is registered together with the host
        self.assertEqual(server.alias["netius-d"], "netius_d")

    def test__build_hosts_alias(self):
        server = self._make_server()

        self._conf(NETIUS_D_PORT="tcp://first:80", NETIUS_D_NAME="/netius_d")

        server.hosts = {}
        server.alias = {}
        server._build_hosts(alias=False)

        # with the alias turned off the dashed version becomes a host of
        # its own, instead of pointing at the underscored one
        self.assertEqual(server.hosts["netius-d"], "http://first:80")
        self.assertEqual("netius-d" in server.alias, False)

    def test__build_hosts_invalid(self):
        server = self._make_server()

        self._conf(
            NETIUS_DA_PORT="tcp://first:80",
            NETIUS_DB_PORT="tcp://second:80",
            NETIUS_DB_NAME="/netius_db",
            NETIUS_DC_ENV_PORT="tcp://third:80",
            NETIUS_DC_ENV_NAME="/netius_dc_env",
            NETIUS_DD_ENV_EXTRA_PORT="tcp://fourth:80",
            NETIUS_DD_ENV_EXTRA_NAME="/netius_dd_env_extra",
            NETIUS_DE_PORT="not-a-url",
            NETIUS_DE_NAME="/netius_de",
        )

        server.hosts = {}
        server._build_hosts()

        # a link with no name of its own is not a service, the ones that
        # carry the environment marker are not either
        self.assertEqual("netius_da" in server.hosts, False)
        self.assertEqual("netius_dc_env" in server.hosts, False)
        self.assertEqual("netius_dd_env_extra" in server.hosts, False)

        # a value that is not a URL names nothing that may be reached, so
        # it is dropped as well
        self.assertEqual("netius_de" in server.hosts, False)

        self.assertEqual(server.hosts["netius_db"], "http://second:80")

    def test__build_hosts_plain(self):
        server = self._make_server()

        self._conf(NETIUSD_PORT="tcp://first:80", NETIUSD_NAME="/netiusd")

        server.hosts = {}
        server.alias = {}
        server._build_hosts()

        # a name that carries no underscore has no dashed version of its
        # own, so there is no alias to be registered for it
        self.assertEqual(server.hosts["netiusd"], "http://first:80")
        self.assertEqual(server.alias, {})

    def test__build_hosts_digit(self):
        server = self._make_server()

        self._conf(NETIUS_D1_PORT="tcp://first:80", NETIUS_D1_NAME="/netius_d1")

        server.hosts = {}
        server._build_hosts()

        # a numbered link whose name is numbered as well is one of the
        # replicas of a service and not the service itself
        self.assertEqual("netius_d1" in server.hosts, False)

    def test__build_alias(self):
        server = self._make_server()

        self._conf(NETIUS_D_ALIAS="netius.com")

        server.alias = {}
        server._build_alias()

        # both the underscored name and the dashed version of it point at
        # the very same host, so that either may be used
        self.assertEqual(server.alias["netius_d"], "netius.com")
        self.assertEqual(server.alias["netius-d"], "netius.com")

    def test__build_passwords(self):
        server = self._make_server()

        self._conf(NETIUS_D_PASSWORD="secret")

        server.auth = {}
        server._build_passwords()

        # the two names share the very same authentication handler, which
        # is a simple one built around the password
        self.assertEqual(isinstance(server.auth["netius_d"], netius.SimpleAuth), True)
        self.assertEqual(server.auth["netius_d"], server.auth["netius-d"])
        self.assertEqual(server.auth["netius_d"].auth_i(None, "secret"), True)
        self.assertEqual(server.auth["netius_d"].auth_i(None, "other"), False)

    def test__build_redirect(self):
        server = self._make_server()

        self._conf(NETIUS_D_REDIRECT="netius.com")

        server.redirect = {}
        server._build_redirect()

        self.assertEqual(server.redirect["netius_d"], "netius.com")
        self.assertEqual(server.redirect["netius-d"], "netius.com")

    def test__build_error_urls(self):
        server = self._make_server()

        self._conf(NETIUS_D_ERROR_URL="http://netius.com/error")

        server.error_urls = {}
        server._build_error_urls()

        self.assertEqual(server.error_urls["netius_d"], "http://netius.com/error")
        self.assertEqual(server.error_urls["netius-d"], "http://netius.com/error")

    def test__build_redirect_ssl(self):
        server = self._make_server()

        self._conf(NETIUS_D_REDIRECT_SSL="1")

        server.redirect = {}
        server.alias = dict(other="netius_d")
        server._build_redirect_ssl()

        # the redirection is towards the very same name under the secure
        # scheme, which is what the tuple carries
        self.assertEqual(server.redirect["netius_d"], ("netius_d", "https"))
        self.assertEqual(server.redirect["netius-d"], ("netius-d", "https"))

        # the alias that points at the name is redirected as well, so that
        # it is not left behind on the insecure scheme
        self.assertEqual(server.redirect["other"], ("other", "https"))

    def test__build_redirect_ssl_alias(self):
        server = self._make_server()

        self._conf(NETIUS_D_REDIRECT_SSL="1")

        server.redirect = {}
        server.alias = dict(other="netius_d", unrelated="another")
        server._build_redirect_ssl(alias=False)

        # with the alias turned off only the name itself is redirected,
        # the ones that point at it being left as they are
        self.assertEqual(server.redirect["netius_d"], ("netius_d", "https"))
        self.assertEqual("other" in server.redirect, False)

        server.redirect = {}
        server._build_redirect_ssl()

        # an alias that points elsewhere is never redirected, whatever
        # the value of the flag
        self.assertEqual("unrelated" in server.redirect, False)

    def test__build_suffixes(self):
        server = self._make_server(host_suffixes=["local"])

        server.alias = dict(other="netius_d")
        server.hosts = dict(netius_d="http://first:80")
        server._build_suffixes()

        # every name gains a fully qualified version of itself under the
        # suffix, the one of a host pointing back at it
        self.assertEqual(server.alias["other.local"], "netius_d")
        self.assertEqual(server.alias["netius_d.local"], "netius_d")
        self.assertEqual("netius_d.local" in server.hosts, False)

    def test__build_suffixes_alias(self):
        server = self._make_server(host_suffixes=["local"])

        server.alias = dict(other="netius_d")
        server.hosts = dict(netius_d="http://first:80")
        server._build_suffixes(alias=False)

        # with the alias turned off the qualified name of a host is a
        # host of its own, which the aliases that exist must not change
        self.assertEqual(server.hosts["netius_d.local"], "http://first:80")
        self.assertEqual("netius_d.local" in server.alias, False)
        self.assertEqual(server.alias["other.local"], "netius_d")

    def test__valid_url(self):
        server = self._make_server()

        self.assertEqual(server._valid_url("http://netius.com"), True)
        self.assertEqual(server._valid_url("tcp://first:80"), True)

        # a value that carries no scheme or no host names nothing that
        # may be reached, so neither of them qualifies
        self.assertEqual(server._valid_url("netius.com"), False)
        self.assertEqual(server._valid_url("http://"), False)

        # the value is turned into a string before being parsed, so one
        # that is not a string is refused instead of raising
        self.assertEqual(server._valid_url(1), False)

    def _make_server(self, **kwargs):
        server = netius.extra.DockerProxyServer(**kwargs)
        self.servers.append(server)
        return server

    def _conf(self, **kwargs):
        for name, value in netius.legacy.iteritems(kwargs):
            netius.conf_s(name, value)
            self.names.append(name)
