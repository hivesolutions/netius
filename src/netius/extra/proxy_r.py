#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import re

import netius.servers

class ReverseProxyServer(netius.servers.ProxyServer):

    def __init__(self, config = "proxy.json", regex = {}, hosts = {}, *args, **kwargs):
        netius.servers.ProxyServer.__init__(self, *args, **kwargs)
        if type(regex) == dict: regex = regex.items()
        if not type(hosts) == dict: hosts = dict(hosts)
        self.load_config(path = config, regex = regex, hosts = hosts)

    def on_data_http(self, connection, parser):
        netius.servers.ProxyServer.on_data_http(self, connection, parser)

        method = parser.method.upper()
        path = parser.path_s
        headers = parser.headers
        version_s = parser.version_s
        is_secure = connection.ssl
        host = headers.get("host", None)
        protocol = "https" if is_secure else "http"

        # constructs the url that is going to be used by the rule engine and
        # then "forwards" both the url and the parser object to the rule engine
        # in order to obtain the possible prefix value for url reconstruction
        url = "%s://%s%s" % (protocol, host, path)
        prefix = self.rules(url, parser)

        # in case no prefix is defined at this stage there's no matching
        # against the currently defined rules and so an error must be raised
        # and propagated to the client connection (end user notification)
        if not prefix:
            self.debug("No valid proxy endpoint found")
            connection.send_response(
                data = "No valid proxy endpoint found",
                headers = dict(
                    connection = "close"
                ),
                version = version_s,
                code = 404,
                code_s = "Not Found",
                apply = True,
                callback = self._prx_close
            )
            return

        # re-calculates the url for the reverse connection based on the
        # prefix value that has just been "resolved" using the rule engine
        # this value should be constructed based on the original path
        url = prefix + path

        # updates the various headers that are relates with the reverse
        # proxy operation this is required so that the request gets
        # properly handled by the reverse server, otherwise some problems
        # would occur in the operation of handling the request
        headers["x-forwarded-proto"] = protocol

        # verifies if the current connection contains already contains
        # a proxy connection if that's the case that must be unset from the
        # connection and from the connection map internal structures at
        # least until the http client returns from the method call
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        proxy_c = proxy_c or None
        connection.proxy_c = None
        if proxy_c in self.conn_map: del self.conn_map[proxy_c]

        # calls the proper (http) method in the client this should acquire
        # a new connection and starts the process of sending the request
        # to the associated http server (request handling)
        _connection = self.http_client.method(
            method,
            url,
            headers = headers,
            data = parser.get_message(),
            version = version_s,
            connection = proxy_c
        )

        # prints a debug message about the connection becoming a waiting
        # connection meaning that the connection with the client host has
        # not been yet established (no data has been  received)
        self.debug("Setting connection as waiting, proxy connection loading ...")

        # sets the current http back-end client connection as waiting and then
        # maps it as the proxy connection in the connection and also creates
        # the reverse mapping using the connection map of the current server
        _connection.waiting = True
        connection.proxy_c = _connection
        self.conn_map[_connection] = connection

    def rules(self, url, parser):
        prefix = self.rules_regex(url, parser)
        if prefix: return prefix
        prefix = self.rules_host(url, parser)
        if prefix: return prefix
        return None

    def rules_regex(self, url, parser):
        # sets the prefix value initialy for the invalid/unset value, this
        # value is going to be populated once a valid match is found
        prefix = None

        # iterates over the complete set of defined regex values to try
        # to find a valid match and apply the groups value for format
        # if the complete chain of regex is processed but there's no
        # valid match the prefix value is considered to be unset
        for regex, _prefix in self.regex:
            match = regex.match(url)
            if not match: continue
            groups = match.groups()
            if groups: _prefix = _prefix.format(*groups)
            prefix = _prefix
            break

        # returns the prefix value that has just been resolved through
        # regex based validation, this value may be unset for mismatch
        return prefix

    def rules_host(self, url, parser):
        # retrieves the reference to the headers map from the parser so
        # that it may be used to retrieve the current host value and try
        # to match it against any of the currently defined rules
        headers = parser.headers

        # retrieves the host header from the received set of headers
        # and then verifies the complete set of defined hosts in order to
        # check for the presence of such rule, in case there's a match
        # the defined url prefix is going to be used instead
        host = headers.get("host", None)
        prefix = self.hosts.get(host, None)

        # returns the final "resolved" prefix value (in case there's any)
        # to the caller method, this should be used for url reconstruction
        return prefix

if __name__ == "__main__":
    import logging
    regex = (
        (re.compile(r"https://host\.com"), "http://localhost"),
        (re.compile(r"https://([a-zA-Z]*)\.host\.com"), "http://localhost/{0}")
    )
    hosts = {
        "host.com" : "http://localhost"
    }
    server = ReverseProxyServer(
        regex = regex,
        hosts = hosts,
        level = logging.INFO
    )
    server.serve(env = True)
