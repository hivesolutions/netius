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

import re
import time

import netius.common
import netius.clients
import netius.servers

class ReverseProxyServer(netius.servers.ProxyServer):
    """
    Reverse HTTP proxy implementation based on the more generalized
    infra-structure of proxy server.

    Supports multiple scheduling strategies, being the "smart" one
    the most efficient for most of the possible scenarios.

    Conditional re-usage of connections based on boolean flag is possible,
    but care should be taken when using re-usage so that no multiple
    rules are applied for the same connection (eg: https://host.com/hive,
    https://host.com/colony as different rules), this would pose serious
    problems if the back-end servers are different for each rule or if
    the way the final back-end url is created is different for each rule.
    """

    def __init__(
        self,
        config = "proxy.json",
        regex = {},
        hosts = {},
        alias = {},
        auth = {},
        auth_regex = {},
        redirect = {},
        strategy = "robin",
        reuse = True,
        sts = 0,
        resolve = True,
        resolve_t = 120.0,
        echo = False,
        *args,
        **kwargs
    ):
        netius.servers.ProxyServer.__init__(self, *args, **kwargs)
        if isinstance(regex, dict): regex = netius.legacy.items(regex)
        if not isinstance(hosts, dict): hosts = dict(hosts)
        self.load_config(
            path = config,
            regex = regex,
            hosts = hosts,
            alias = alias,
            auth = auth,
            auth_regex = auth_regex,
            redirect = redirect,
            strategy = strategy,
            reuse = reuse,
            sts = sts,
            resolve = resolve,
            resolve_t = resolve_t,
            echo = echo,
            robin = dict(),
            smart = netius.common.PriorityDict()
        )
        self.busy_conn = 0
        self._set_strategy()

    def info_dict(self, full = False):
        info = netius.servers.ProxyServer.info_dict(self, full = full)
        info.update(
            reuse = self.reuse,
            strategy = self.strategy,
            busy_conn = self.busy_conn
        )
        return info

    def on_start(self):
        netius.servers.ProxyServer.on_start(self)
        if self.resolve: self.dns_start(timeout = self.resolve_t)

    def on_serve(self):
        netius.servers.ProxyServer.on_serve(self)
        if self.env: self.sts = self.get_env("STS", self.sts, cast = int)
        if self.env: self.echo = self.get_env("ECHO", self.echo, cast = bool)
        if self.env: self.resolve = self.get_env("RESOLVE", self.resolve, cast = bool)
        if self.env: self.resolve_t = self.get_env("RESOLVE_TIMEOUT", self.resolve_t, cast = float)
        if self.env: self.reuse = self.get_env("REUSE", self.reuse, cast = bool)
        if self.env: self.strategy = self.get_env("STRATEGY", self.strategy)
        if self.env: self.x_forwarded_port = self.get_env("X_FORWARDED_PORT", None)
        if self.env: self.x_forwarded_proto = self.get_env("X_FORWARDED_PROTO", None)
        if self.sts: self.info("Strict transport security set to %d seconds" % self.sts)
        if self.resolve: self.info("DNS based resolution enabled in proxy with %.2fs timeout" % self.resolve_t)
        if self.strategy: self.info("Using '%s' as load balancing strategy" % self.strategy)
        if self.echo: self._echo()
        self._set_strategy()

    def on_headers(self, connection, parser):
        netius.servers.ProxyServer.on_headers(self, connection, parser)

        # retrieves the various parts/configuration values of the parser, that
        # are going to be used in the processing/routing of the proxy request,
        # note that some of these values need to be transformed to be used
        method = parser.method.upper()
        path = parser.path_s
        headers = parser.headers
        version_s = parser.version_s
        is_secure = connection.ssl
        host = headers.get("host", "127.0.0.1")
        host_p = host.rsplit(":", 1)
        host_s = host_p[0]
        host_o = host
        port_d = "443" if is_secure else "80"
        port_s = host_p[1] if len(host_p) > 1 else port_d
        host = self.alias.get(host_s, host)
        host = self.alias.get(host, host)

        # tries to discover the proper address representation of the current
        # connections, note that the forwarded for header is only used in case
        # the current "origin" is considered "trustable"
        address = connection.address[0]
        if self.trust_origin:
            address = headers.get("x-forwarded-for", address)
            address = headers.get("x-client-ip", address)
            address = headers.get("x-real-ip", address)
            address = address.split(",", 1)[0].strip()

        # tries to retrieve the string based port version taking into account
        # the port of the server bind port and the host based port and falling
        # back to the forwarded port in case the  "origin" is considered "trustable"
        port = port_s or str(self.port)
        if self.trust_origin: port = headers.get("x-forwarded-port", port)

        # tries to discover the protocol representation of the current
        # connections, note that the forwarded for header is only used in case
        # the current "origin" is considered "trustable"
        protocol = "https" if is_secure else "http"
        if self.trust_origin: protocol = headers.get("x-forwarded-proto", protocol)

        # tries to determine if a proper (client side) redirection should operation
        # should be applied to the current request, if that's the case (match) an
        # immediate response is returned with proper redirection instructions
        redirect = self.redirect.get(host, None)
        redirect = self.redirect.get(host_s, redirect)
        redirect = self.redirect.get(host_o, redirect)
        if redirect:
            # verifies if the redirect value is a sequence and if that's
            # not the case converts the value into a tuple value
            is_sequence = isinstance(redirect, (list, tuple))
            if not is_sequence: redirect = (redirect,)

            # converts the possible tuple value into a list so that it
            # may be changed (mutable sequence is required)
            redirect = list(redirect)

            # adds the proper trail values to the redirect sequence so that
            # both the protocol and the path are ensured to exist
            if len(redirect) == 1: redirect += [protocol, path]
            if len(redirect) == 2: redirect += [path]

            # unpacks the redirect sequence and builds the new location
            # value taking into account the proper values
            redirect_t, protocol_t, path_t = redirect
            location = "%s://%s%s" % (protocol_t, redirect_t, path_t)

            # verifies if the current request already matched the redirection
            # rule and if that't the case ignores the, note that the host value
            # is verified against all the possible combinations
            is_match = host_o == redirect_t or host_s == redirect_t or\
                host == redirect_t
            is_match &= protocol == protocol_t
            is_match &= path == path_t
            redirect = not is_match

            # sends the "final" response to the user agent, effectively
            # redirecting it into the target redirect location, but only
            # if the redirection is really required
            if redirect:
                return connection.send_response(
                    headers = dict(
                        location = location
                    ),
                    version = version_s,
                    code = 303,
                    code_s = "See Other",
                    apply = True
                )

        # tries to extract the various attributes of the current connection
        # that are going to be used for the routing operation, this attributes
        # should avoid a new rule setting operation (expensive) and provide
        # connection, prefix and state re-usage whenever possible, note that
        # under some situation the prefix may change for the same connection
        # and so the connection re-usage is not possible
        prefix = connection.prefix if hasattr(connection, "prefix") else None
        state = connection.state if hasattr(connection, "state") else None
        reusable = hasattr(connection, "proxy_c")

        # constructs the url that is going to be used by the rule engine and
        # then "forwards" both the url and the parser object to the rule engine
        # in order to obtain the possible prefix value for url reconstruction,
        # a state value is also retrieved, this value will be used latter for
        # the acquiring and releasing parts of the balancing strategy operation
        url = "%s://%s%s" % (protocol, host, path)
        if not self.reuse or not reusable: prefix, state = self.rules(url, parser)

        # in case no prefix is defined at this stage there's no matching
        # against the currently defined rules and so an error must be raised
        # and propagated to the client connection (end user notification)
        if not prefix:
            self.debug("No valid proxy endpoint found")
            return connection.send_response(
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

        # verifies if the current host requires come kind of special authorization
        # process using the default basic http authorization process
        auth = self.auth.get(host.rsplit(":", 1)[0], None)
        auth, _match = self._resolve_regex(url, self.auth_regex, default = auth)
        if auth:
            # determines if the provided authentication method is a sequence
            # and if that't not the case casts it as one (iterative validation)
            # then sets the initial/default (authentication) value as false (deny)
            auths = auth if type(auth) in (list, tuple) else (auth,)
            result = False

            # iterates over the complete set of authorization methods defined
            # trying to determine if at least one of them is valid for the current
            # situation/request, note that this is considered an or operation
            # and should be used carefully to avoid unexpected behavior
            for auth in auths:
                result = self.authorize(connection, parser, auth = auth)
                if result: break

            # in case the result of the authentication chain is not valid (none
            # of the authentication methods was successful) sends the invalid
            # response to the client meaning that the current request is invalid
            if not result:
                return connection.send_response(
                    data = "Not authorized",
                    headers = {
                        "connection" : "close",
                        "wWW-authenticate" : "Basic realm=\"default\""
                    },
                    version = version_s,
                    code = 401,
                    code_s = "Not Authorized",
                    apply = True,
                    callback = self._prx_close
                )

        # runs the acquire operation for the current state, this should
        # update the current scheduling algorithm internal structures so
        # that they properly handle the new handle operation, an inverse
        # release operation should be performed at the end of the handling
        self.acquirer(state)

        # re-calculates the url for the reverse connection based on the
        # prefix value that has just been "resolved" using the rule engine
        # this value should be constructed based on the original path
        url = prefix + path

        # updates the various headers that are related with the reverse
        # proxy operation this is required so that the request gets
        # properly handled by the reverse server, otherwise some problems
        # would occur in the operation of handling the request
        headers["x-real-ip"] = address
        headers["x-client-ip"] = address
        headers["x-forwarded-for"] = address
        headers["x-forwarded-proto"] = protocol
        headers["x-forwarded-port"] = port
        headers["x-forwarded-host"] = host_o

        # verifies if the current connection already contains a valid
        # a proxy connection if that's the case that must be unset from
        # the connection and from the connection map internal structures
        # at least until the http client returns from the method call
        proxy_c = hasattr(connection, "proxy_c") and connection.proxy_c
        proxy_c = proxy_c or None
        connection.proxy_c = None
        if proxy_c in self.conn_map: del self.conn_map[proxy_c]

        # tries to determine the transfer encoding of the received request
        # and by using that determines the proper encoding to be applied
        encoding = headers.get("transfer-encoding", None)
        is_chunked = encoding == "chunked"
        encoding = netius.common.CHUNKED_ENCODING if is_chunked else\
            netius.common.PLAIN_ENCODING

        # calls the proper (http) method in the client this should acquire
        # a new connection and start the process of sending the request
        # to the associated http server (request handling)
        _connection = self.http_client.method(
            method,
            url,
            headers = headers,
            encoding = encoding,
            encodings = None,
            safe = True,
            connection = proxy_c
        )

        # sets the state attribute in the connection so that it's possible
        # to retrieve it latter for tagging evaluation, this is required for
        # advanced load balancing techniques to be performed
        _connection.state = state

        # sets the current connection as busy, as it's waiting for a message
        # to be returned from the the back-end side, then increments the number
        # of currently busy connections (as expected)
        _connection.busy = _connection.busy if hasattr(_connection, "busy") else 0
        _connection.busy += 1
        self.busy_conn += 1

        # prints a debug message about the connection becoming a waiting
        # connection meaning that the connection with the client host has
        # not been yet established (no data has been  received)
        self.debug("Setting connection as waiting, proxy connection loading ...")

        # sets the current http back-end client connection as waiting and then
        # maps it as the proxy connection in the connection and also creates
        # the reverse mapping using the connection map of the current server
        _connection.waiting = True
        _connection.max_pending = self.max_pending
        _connection.min_pending = self.min_pending
        connection.proxy_c = _connection
        connection.prefix = prefix
        connection.state = state
        self.conn_map[_connection] = connection

    def rules(self, url, parser):
        resolved = self.rules_regex(url, parser)
        if resolved[0]: return resolved
        resolved = self.rules_host(url, parser)
        if resolved[0]: return resolved
        return None, None

    def rules_regex(self, url, parser):
        # sets the prefix and state values initially for the invalid/unset value,
        # these values are going to be populated once a valid match is found
        prefix = None
        state = None

        # runs the regex resolution process for the url and the defined
        # sequence of regex values, this is an iterative process in case
        # there's no match the default value is returned immediately
        _prefix, match = self._resolve_regex(url, self.regex)
        if not _prefix: return prefix, state

        # prints a debug message about the matching that has just occurred
        # so that proper debugging may take place if required
        self.debug("Found regex prefix '%s' for '%s'" % (_prefix, url))

        # uses the resolved prefix value in the balancer to obtain the
        # proper final prefix and its associated state
        _prefix, _state = self.balancer(_prefix)
        groups = match.groups()
        if groups: _prefix = _prefix.format(*groups)
        prefix = _prefix
        state = _state

        # prints more debug information to be used for possible runtime debug
        # this should represent the final resolution process
        self.debug("Resolved regex prefix '%s' for '%s'" % (prefix, url))

        # returns the prefix and state values that have just been resolved
        # through regex based validation, this value may be unset for a mismatch
        return prefix, state

    def rules_host(self, url, parser):
        # retrieves the reference to the headers map from the parser so
        # that it may be used to retrieve the current host value and try
        # to match it against any of the currently defined rules
        headers = parser.headers

        # retrieves the host header from the received set of headers,
        # removing the port definition part of the host and then verifies
        # the complete set of defined hosts in order to check for the
        # presence of such rule, in case there's a match the defined
        # url prefix is going to be used instead, the balancer operation
        # is then used to "resolve" the final prefix value from sequence
        host = headers.get("host", None)
        host_s = host.rsplit(":", 1)[0] if host else host
        host = self.alias.get(host_s, host)
        host = self.alias.get(host, host)
        prefix = self.hosts.get(host_s, None)
        prefix = self.hosts.get(host, prefix)
        resolved = self.balancer(prefix)

        # prints more debug information to be used for possible runtime debug
        # this should represent the final resolution process
        self.debug("Resolved host prefix '%s' for '%s'" % (prefix, url))

        # returns the final "resolved" prefix value (in case there's any)
        # to the caller method, this should be used for url reconstruction
        # note that the state value is also returned and should be store in
        # the current handling connection so that it may latter be used
        return resolved

    def balancer(self, values):
        is_sequence = isinstance(values, (list, tuple))
        if not is_sequence: return values, None
        return self.balancer_m(values)

    def balancer_robin(self, values):
        index = self.robin.get(values, 0)
        prefix = values[index]
        next = 0 if index + 1 >= len(values) else index + 1
        self.robin[values] = next
        return prefix, None

    def balancer_smart(self, values):
        queue = self.smart.get(values, None)
        if not queue:
            queue = netius.common.PriorityDict()
            for value in values: queue[value] = [0, 0]
            self.smart[values] = queue

        prefix = queue.smallest()

        return prefix, (prefix, queue)

    def acquirer(self, state):
        self.acquirer_m(state)

    def acquirer_robin(self, state):
        pass

    def acquirer_smart(self, state):
        if not state: return
        prefix, queue = state
        sorter = queue[prefix]
        sorter[0] += 1
        queue[prefix] = sorter

    def releaser(self, state):
        self.releaser_m(state)

    def releaser_robin(self, state):
        pass

    def releaser_smart(self, state):
        if not state: return
        prefix, queue = state
        sorter = queue[prefix]
        sorter[0] -= 1
        if sorter[0] == 0: sorter[1] = time.time() * -1
        queue[prefix] = sorter

    def dns_start(self, timeout = 120.0):
        # creates the dictionary that is going to hold the original
        # values for the hosts, this is going to be required for later
        # computation of the resolved values
        self.hosts_o = dict()

        # iterates over the complete set of hosts to normalize their
        # values and then store them in the original and legacy maps
        for host, values in netius.legacy.items(self.hosts):
            is_sequence = isinstance(values, (list, tuple))
            if not is_sequence: values = (values,)
            resolved = [[value] for value in values]
            self.hosts[host] = tuple(values)
            self.hosts_o[host] = (values, resolved)

        # runs the initial tick for the dns execution, this should start
        # the dns resolution process
        self.dns_tick(timeout = timeout)

    def dns_tick(self, timeout = 120.0):
        # iterates over the complete set of original hosts to run the tick
        # operation, this should perform dns queries for all values using
        # the default netius dns client
        for host, composition in netius.legacy.items(self.hosts_o):
            # unpacks the original hosts value composition into the (url)
            # values and the resolved list of lists
            values, resolved = composition
            values_l = len(values)

            # iterates over the complete set of urls associated with the
            # original host value
            for index in netius.legacy.xrange(values_l):

                # retrieves the current value (url) in iteration and then
                # parses it using the legacy infra-structure
                value = values[index]
                parsed = netius.legacy.urlparse(value)
                hostname = parsed.hostname

                # validates that the parsed hostname is valid and ready
                # to be queried as dns value, if that's not the case
                # continues the loop skipping current iteration
                if not hostname: continue

                # creates the callback function that is going to be called
                # after the dns resolution for proper hosts setting
                callback = self.dns_callback(
                    host,
                    value,
                    parsed,
                    index = index,
                    resolved = resolved
                )

                # runs the dns query execution for the hostname associated
                # with the current load balancing url, the callback of this
                # call should handle the addition of the value to hosts
                netius.clients.DNSClient.query_s(
                    hostname,
                    type = "a",
                    callback = callback
                )

        # verifies if the requested timeout is zero and if that's the
        # case only one execution of the dns tick is pretended, returns
        # the control flow back to caller immediately
        if timeout == 0: return

        # schedules a delayed execution taking into account the timeout
        # that has been provided, this is going to update the various
        # servers that are defined for the registered domains
        tick = lambda: self.dns_tick(timeout = timeout)
        self.delay(tick, timeout = timeout)

    def dns_callback(
        self,
        host,
        hostname,
        parsed,
        index = 0,
        resolved = []
    ):
        # constructs both the port string based value and extracts
        # the path of the base url that gave origin to this resolution
        port_s = ":" + str(parsed.port) if parsed.port else ""
        path = parsed.path

        def callback(response):
            # in case there's no valid dns response there's nothing to be
            # done, control flow is returned immediately
            if not response: return
            if not response.answers: return

            # creates the list that is going to be used t store the complete
            # set of resolved url for the current host value in resolution
            target = []

            # iterates over the complete set of dns answers to re-build
            # the target url value taking into account the resolved value
            # this (ip based) url is going to be added to the list of target
            # values to be added to the resolved list on proper index
            for answer in response.answers:
                address = answer[4]
                url = "%s://%s%s%s" % (parsed.scheme, address, port_s, path)
                target.append(url)

            # sets the target list of url for the proper index in the resolved
            # list and then "re-join" the complete set of lists to obtain a
            # plain sequence of urls for the current host
            resolved[index] = target
            values = [_value for value in resolved for _value in value]
            self.hosts[host] = tuple(values)

        # returns the callback (clojure) function that has just been created and
        # that is going to be called upon dns resolution
        return callback

    def _on_prx_message(self, client, parser, message):
        _connection = parser.owner
        busy = _connection.busy if hasattr(_connection, "busy") else 0
        state = _connection.state if hasattr(_connection, "state") else None
        if busy: self.busy_conn -= 1; _connection.busy -= 1
        if state: self.releaser(state); _connection.state = None
        netius.servers.ProxyServer._on_prx_message(self, client, parser, message)

    def _on_prx_close(self, client, _connection):
        busy = _connection.busy if hasattr(_connection, "busy") else 0
        state = _connection.state if hasattr(_connection, "state") else None
        if busy: self.busy_conn -= busy; _connection.busy -= busy
        if state: self.releaser(state); _connection.state = None
        netius.servers.ProxyServer._on_prx_close(self, client, _connection)

    def _apply_all(
        self,
        parser,
        connection,
        headers,
        upper = True,
        normalize = False,
        replace = False
    ):
        netius.servers.ProxyServer._apply_all(
            self,
            parser,
            connection,
            headers,
            upper = upper,
            normalize = normalize,
            replace = replace
        )

        # in case a strict transport security value (number) is defined it
        # is going to be used as the max age value to be applied for such
        # behavior, note that this is considered dangerous at it may corrupt
        # the serving of assets through non secure (no SSL) connections
        if self.sts: headers["Strict-Transport-Security"] = "max-age=%d" % self.sts

    def _apply_headers(self, parser, connection, parser_prx, headers, upper = True):
        netius.servers.ProxyServer._apply_headers(
            self,
            parser,
            connection,
            parser_prx,
            headers,
            upper = upper
        )

        # in case a strict transport security value (number) is defined it
        # is going to be used as the max age value to be applied for such
        # behavior, note that this is considered dangerous at it may corrupt
        # the serving of assets through non secure (no SSL) connections
        if self.sts: headers["Strict-Transport-Security"] = "max-age=%d" % self.sts

        # in case the parser has determined that the current connection is
        # meant to be kept alive the connection header is forced to be keep
        # alive this avoids issues where in HTTP 1.1 the connection header
        # is omitted and an ambiguous situation may be created raising the
        # level of incompatibility with user agents
        if parser_prx.keep_alive: parser_prx.headers["Connection"] = "keep-alive"

    def _set_strategy(self):
        self.balancer_m = getattr(self, "balancer_" + self.strategy)
        self.acquirer_m = getattr(self, "acquirer_" + self.strategy)
        self.releaser_m = getattr(self, "releaser_" + self.strategy)

    def _resolve_regex(self, value, regexes, default = None):
        for regex, result in regexes:
            match = regex.match(value)
            if not match: continue
            return result, match
        return default, None

    def _echo(self, sort = True):
        self._echo_regex(sort = sort)
        self._echo_hosts(sort = sort)
        self._echo_alias(sort = sort)
        self._echo_redirect(sort = sort)

    def _echo_regex(self, sort = True):
        self.info("Regex registration information")
        for key, value in self.regex: self.info("%s => %s" % (key, value))

    def _echo_hosts(self, sort = True):
        keys = netius.legacy.keys(self.hosts)
        if sort: keys.sort()
        self.info("Host registration information")
        for key in keys: self.info("%s => %s" % (key, self.hosts[key]))

    def _echo_alias(self, sort = True):
        keys = netius.legacy.keys(self.alias)
        if sort: keys.sort()
        self.info("Alias registration information")
        for key in keys: self.info("%s => %s" % (key, self.alias[key]))

    def _echo_redirect(self, sort = True):
        keys = netius.legacy.keys(self.redirect)
        if sort: keys.sort()
        self.info("Redirect registration information")
        for key in keys: self.info("%s => %s" % (key, self.redirect[key]))

if __name__ == "__main__":
    import logging
    regex = (
        (re.compile(r"https://host\.com"), "http://localhost"),
        (re.compile(r"https://([a-zA-Z]*)\.host\.com"), "http://localhost/{0}")
    )
    hosts = {
        "host.com" : "http://host.com"
    }
    alias = {
        "alias.host.com" : "host.com"
    }
    auth = {
        "host.com" : netius.SimpleAuth("root", "root")
    }
    auth_regex = (
        (
            re.compile(r"https://host\.com:9090"),
            (
                netius.SimpleAuth("root", "root"),
                netius.AddressAuth(["127.0.0.1"])
            )
        ),
    )
    redirect = {
        "host.com" : "other.host.com"
    }
    server = ReverseProxyServer(
        regex = regex,
        hosts = hosts,
        alias = alias,
        auth = auth,
        auth_regex = auth_regex,
        redirect = redirect,
        level = logging.INFO
    )
    server.serve(env = True)
else:
    __path__ = []
