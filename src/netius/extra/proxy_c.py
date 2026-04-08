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

import re
import json

import netius
import netius.clients

from . import proxy_r


class ConsulProxyServer(proxy_r.ReverseProxyServer):
    """
    Specialized reverse proxy server that uses the Consul service
    discovery HTTP API to automatically discover and register
    backend services for reverse proxying.

    Services are discovered by polling Consul's catalog and health
    endpoints. Only services tagged with a configurable tag (by
    default `proxy.enable=true`) are registered. Multiple healthy
    instances of the same service are registered as a tuple for
    load balancing using the existing robin/smart strategies.

    An optional `proxy.name=<custom>` tag can be used to override
    the subdomain name (instead of the job/service name). The
    `proxy.domain=<custom>` tag is also supported as an alias
    with lower priority than `proxy.name`.

    Additional per-service tags are supported for password
    protection (`proxy.password=<secret>`), custom error pages
    (`proxy.error-url=<url>`), automatic HTTPS redirection
    (`proxy.redirect-ssl=true`), port filtering
    (`proxy.port=<port1,port2,...>` or alias `proxy.ports`),
    address override (`proxy.address=<address>`), domain aliasing
    (`proxy.alias=<domain1>,<domain2>,...`), and regex-based auth
    rules (`proxy.auth-regex=<pattern>;<type>,...`).
    """

    def __init__(
        self,
        consul_url="http://localhost:8500",
        consul_token=None,
        consul_tag="proxy.enable=true",
        consul_poll_interval=60.0,
        consul_skip_health=True,
        host_suffixes=[],
        *args,
        **kwargs
    ):
        proxy_r.ReverseProxyServer.__init__(self, *args, **kwargs)
        self.load_config(
            consul_url=consul_url,
            consul_token=consul_token,
            consul_tag=consul_tag,
            consul_poll_interval=consul_poll_interval,
            consul_skip_health=consul_skip_health,
            host_suffixes=host_suffixes,
        )
        self._consul_hosts = set()
        self._consul_aliases = set()
        self._consul_tag_aliases = set()
        self._consul_auth_regex = []

    def on_serve(self):
        proxy_r.ReverseProxyServer.on_serve(self)
        if self.env:
            self.consul_url = self.get_env("CONSUL_URL", self.consul_url)
        if self.env:
            self.consul_token = self.get_env("CONSUL_TOKEN", self.consul_token)
        if self.env:
            self.consul_tag = self.get_env("CONSUL_TAG", self.consul_tag)
        if self.env:
            self.consul_poll_interval = self.get_env(
                "CONSUL_POLL_INTERVAL", self.consul_poll_interval, cast=float
            )
        if self.env:
            self.consul_skip_health = self.get_env(
                "CONSUL_SKIP_HEALTH", self.consul_skip_health, cast=bool
            )
        if self.env:
            self.host_suffixes = self.get_env(
                "HOST_SUFFIXES", self.host_suffixes, cast=list
            )
        self.info("Using Consul at %s for service discovery", self.consul_url)
        self.info("Consul poll interval set to %.2fs", self.consul_poll_interval)
        self._consul_tick(timeout=self.consul_poll_interval)

    def _build_consul(self, entries):
        self._debug_entries(entries)
        self._build_hosts(entries)
        self._build_suffixes()
        self._debug_state()

    def _build_hosts(self, entries):
        # removes any previously registered consul-managed hosts,
        # auth, error URLs, redirects and auth regex entries to
        # ensure a clean state before rebuilding the complete set
        for host in self._consul_hosts:
            self.hosts.pop(host, None)
            self.auth.pop(host, None)
            self.error_urls.pop(host, None)
            self.redirect.pop(host, None)
        for entry in self._consul_auth_regex:
            try:
                self.auth_regex.remove(entry)
            except ValueError:
                pass
        self._consul_hosts = set()
        self._consul_tag_aliases = set()
        self._consul_auth_regex = []

        # iterates over the fetched entries registering each one
        # in the hosts map and applying per-service configuration
        for service, domain, urls, tags in entries:
            # registers the service in the hosts map, using a
            # tuple for multiple instances (load balancing) or
            # a plain string for a single instance
            if len(urls) == 1:
                self.hosts[domain] = urls[0]
            else:
                self.hosts[domain] = tuple(urls)

            # applies extra per-service configuration from consul
            # tags (password, error URL, SSL redirect)
            self._apply_tags(domain, tags)

            # tracks the consul-managed host key so it can be
            # cleaned up on the next rebuild cycle
            self._consul_hosts.add(domain)

            self.debug(
                "Registered Consul service '%s' as '%s' with %d instance(s)",
                service,
                domain,
                len(urls),
            )

    def _build_suffixes(self, alias=True, redirect=True):
        # removes any previously registered consul-managed suffix aliases
        # and hosts to ensure a clean state before rebuilding, preserving
        # tag-based aliases (e.g. proxy.alias) that were set in `_apply_tags``
        suffix_aliases = self._consul_aliases - self._consul_tag_aliases
        for fqn in suffix_aliases:
            self.alias.pop(fqn, None)
            self.hosts.pop(fqn, None)
        self._consul_aliases = set(self._consul_tag_aliases)

        for host_suffix in self.host_suffixes:
            self.info("Registering %s host suffix", host_suffix)
            for _alias, value in netius.legacy.items(self.alias):
                fqn = _alias + "." + str(host_suffix)
                self.alias[fqn] = value
                self._consul_aliases.add(fqn)

                # propagates redirect rules to the FQN so that eg
                # myapp.example.com redirects to itself, not to myapp
                if redirect and _alias in self.redirect:
                    _redirect = self.redirect[_alias]
                    self.redirect[fqn] = (
                        (fqn, _redirect[1])
                        if isinstance(_redirect, tuple)
                        else _redirect
                    )
            for name, value in netius.legacy.items(self.hosts):
                fqn = name + "." + str(host_suffix)
                if alias:
                    self.alias[fqn] = name
                else:
                    self.hosts[fqn] = value
                self._consul_aliases.add(fqn)

                # propagates redirect rules to the FQN so that eg
                # myapp.example.com redirects to itself, not to myapp
                if redirect and name in self.redirect:
                    _redirect = self.redirect[name]
                    self.redirect[fqn] = (
                        (fqn, _redirect[1])
                        if isinstance(_redirect, tuple)
                        else _redirect
                    )

    def _consul_fetch(self):
        # fetches all eligible service data from the consul catalog
        # and health endpoints (I/O bound, safe to run in a thread)
        entries = []
        services = self._consul_services()
        for service, tags in netius.legacy.iteritems(services):
            # verifies that the current service contains the required
            # proxy tag, skipping it in case it does not
            if not self.consul_tag in tags:
                continue

            # determines the domain name for the service, using
            # the proxy.name or proxy.domain tag if available or
            # falling back to the service name itself (lowercased)
            domain = self._resolve_domain(service, tags)

            # retrieves the set of healthy instances for the
            # current service from the consul health endpoint
            instances = self._consul_health(service)
            if not instances:
                self.debug(
                    "Consul service '%s' (%s): no healthy instances, skipping",
                    service,
                    domain,
                )
                continue

            # resolves the optional address override from the
            # consul tags, bypassing the default resolution
            address = self._resolve_address(tags)

            # resolves the optional port filter from the consul
            # tags, limiting which ports are considered valid
            ports = self._resolve_ports(tags)
            if ports:
                self.debug(
                    "Consul service '%s' (%s): port filter %s", service, domain, ports
                )

            # builds the complete set of backend URLs from the
            # healthy instances, filtering out any invalid ones
            urls = self._build_urls(instances, address=address, ports=ports)
            if not urls:
                self.debug(
                    "Consul service '%s' (%s): %d instance(s) but no valid URLs, skipping",
                    service,
                    domain,
                    len(instances),
                )
                continue

            self.debug(
                "Consul service '%s' (%s): %d healthy instance(s), %d URL(s)",
                service,
                domain,
                len(instances),
                len(urls),
            )

            # adds the resolved entry to the list of entries to
            # be applied later if necessary
            entries.append((service, domain, urls, tags))

        self.debug("Consul fetch complete: %d service(s) resolved", len(entries))
        return entries

    def _consul_tick(self, timeout=30.0):
        # offloads the consul discovery I/O to a background thread
        # to avoid blocking the main event loop during HTTP requests,
        # the results are then applied back on the main loop via delay_s
        def _fetch():
            try:
                entries = self._consul_fetch()
            except Exception as exception:
                self.info("Consul fetch failed: %s", exception)
                entries = None

            # builds the consul structures using the fetched entries,
            # then schedules the next tick after the configured, this
            # function is meant to run in the main event loop, so it
            # can safely modify the proxy configuration without any
            # kind of locking concerns
            def _apply():
                try:
                    # applies the new consul configuration if any entries were
                    # successfully fetched, otherwise keeps the existing one
                    # considered to be the safer approach
                    if entries:
                        self._build_consul(entries)

                    # triggers a tick event to allow external monitoring of the
                    # consul discovery process, this is done after `_build_consul`
                    # so that tick handlers see the updated host configuration
                    self.trigger("tick", self)
                finally:
                    # schedules the next tick after the configured interval, this is
                    # done inside a finally block to ensure it happens even if there
                    # were errors during the fetch or apply phases, preventing the
                    # discovery process from halting due to transient issues
                    if timeout > 0:
                        self.delay(
                            lambda: self._consul_tick(timeout=timeout), timeout=timeout
                        )

            self.delay_s(_apply)

        self.ensure(_fetch, thread=True)

    def _consul_services(self):
        url = self.consul_url + "/v1/catalog/services"
        result = self._consul_get(url)
        if result == None:
            self.debug("Consul catalog/services returned None")
            return dict()
        return result

    def _consul_health(self, service):
        url = self.consul_url + "/v1/health/service/" + netius.legacy.quote(service)
        if not self.consul_skip_health:
            url += "?passing=true"
        result = self._consul_get(url)
        if result == None:
            self.debug("Consul health query for '%s' returned None", service)
            return []
        return result

    def _consul_get(self, url):
        headers = dict()
        if self.consul_token:
            headers["X-Consul-Token"] = self.consul_token
        try:
            result = netius.clients.HTTPClient.get_s(
                url, headers=headers, asynchronous=False, timeout=10
            )
            if result.get("error"):
                self.info("Consul request error for %s: %s", url, result.get("message"))
                return None
            if not result["code"] == 200:
                self.info("Consul returned %d for %s", result["code"], url)
                return None
            data = result.get("data", b"")
            return json.loads(data)
        except Exception as exception:
            self.info("Failed to retrieve Consul data from %s: %s", url, exception)
            return None

    def _resolve_domain(self, service, tags):
        name = None
        domain = None
        for tag in tags:
            if tag.startswith("proxy.name=") and name == None:
                name = tag[len("proxy.name=") :]
            elif tag.startswith("proxy.domain=") and domain == None:
                domain = tag[len("proxy.domain=") :]
        if name:
            return str(name)
        if domain:
            return str(domain)
        return str(service.lower())

    def _resolve_address(self, tags):
        for tag in tags:
            if not tag.startswith("proxy.address="):
                continue
            value = tag[len("proxy.address=") :]
            if not value:
                continue
            return str(value)
        return None

    def _resolve_ports(self, tags):
        value = None
        for tag in tags:
            if tag.startswith("proxy.port=") and value == None:
                value = tag[len("proxy.port=") :]
            elif tag.startswith("proxy.ports=") and value == None:
                value = tag[len("proxy.ports=") :]
        if not value:
            return None
        self.debug("Parsing port filter value '%s'", value)
        ports = set()
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                bounds = part.split("-", 1)
                try:
                    start = int(bounds[0].strip())
                    end = int(bounds[1].strip())
                except ValueError:
                    self.warning("Invalid port range '%s', skipping", part)
                    continue
                for port in range(start, end + 1):
                    ports.add(port)
            else:
                try:
                    ports.add(int(part))
                except ValueError:
                    self.warning("Invalid port value '%s', skipping", part)
                    continue
        return ports if ports else None

    def _resolve_auth_regex(self, tags):
        value = None
        for tag in tags:
            if tag.startswith("proxy.auth-regex=") and value == None:
                value = tag[len("proxy.auth-regex=") :]
        if not value:
            return None
        result = []
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if ";" not in part:
                continue
            pattern, auth_spec = part.split(";", 1)
            pattern = pattern.strip()
            if not pattern:
                continue
            regex = re.compile(pattern)
            # splits the auth spec by the pipe character to support
            # multiple auth methods per rule (evaluated with OR logic)
            auths = []
            for auth_part in auth_spec.split("|"):
                auth = self._resolve_auth_type(auth_part.strip(), tags)
                if auth == False:
                    continue
                auths.append(auth)
            if not auths:
                continue
            if len(auths) == 1:
                result.append((regex, auths[0]))
            else:
                result.append((regex, tuple(auths)))
        return result if result else None

    def _resolve_auth_type(self, auth_type, tags):
        if auth_type == "none":
            return None
        elif auth_type == "password":
            password = self._resolve_tag(tags, "proxy.password=")
            if password:
                return netius.SimpleAuth(password=password)
            return False
        elif auth_type.startswith("simple:"):
            credentials = auth_type[len("simple:") :]
            parts = credentials.split(":", 1)
            username = parts[0] if len(parts) > 0 else None
            password = parts[1] if len(parts) > 1 else None
            return netius.SimpleAuth(username=username, password=password)
        elif auth_type.startswith("address:"):
            addresses = auth_type[len("address:") :]
            allowed = []
            for address in addresses.split("+"):
                address = address.strip()
                if address:
                    allowed.append(address)
            if allowed:
                return netius.AddressAuth(allowed=allowed)
            return False
        return False

    def _resolve_tag(self, tags, prefix):
        for tag in tags:
            if not tag.startswith(prefix):
                continue
            value = tag[len(prefix) :]
            if not value:
                continue
            return str(value)
        return None

    def _apply_tags(self, domain, tags):
        for tag in tags:
            if tag.startswith("proxy.password="):
                password = tag[len("proxy.password=") :]
                if password:
                    simple_auth = netius.SimpleAuth(password=password)
                    self.auth[domain] = simple_auth
                    self.debug("Registered proxy.password for '%s'", domain)
            elif tag.startswith("proxy.error-url="):
                error_url = tag[len("proxy.error-url=") :]
                if error_url:
                    self.error_urls[domain] = str(error_url)
                    self.debug(
                        "Registered proxy.error-url '%s' for '%s'", error_url, domain
                    )
            elif tag.startswith("proxy.alias="):
                aliases = tag[len("proxy.alias=") :]
                for alias in aliases.split(","):
                    alias = alias.strip()
                    if alias:
                        self.alias[alias] = domain
                        self._consul_aliases.add(alias)
                        self._consul_tag_aliases.add(alias)
                        self.debug("Registered proxy.alias '%s' -> '%s'", alias, domain)
            elif tag == "proxy.redirect-ssl=true":
                self.redirect[domain] = (domain, "https")
                self.debug("Registered proxy.redirect-ssl for '%s'", domain)

        # in case the domain itself is registered for SSL redirection, also
        # registers the same redirection for any aliases of the domain to
        # ensure consistent behavior across all related hostnames
        if domain in self.redirect:
            for alias in self._consul_tag_aliases:
                if not self.alias.get(alias) == domain:
                    continue
                self.redirect[alias] = (alias, "https")
                self.debug("Registered proxy.redirect-ssl for alias '%s'", alias)

        auth_regex = self._resolve_auth_regex(tags)
        if auth_regex:
            self.auth_regex = list(self.auth_regex) + auth_regex
            self._consul_auth_regex.extend(auth_regex)
            self._debug_auth_regex(domain, auth_regex)

    def _build_urls(self, instances, address=None, ports=None):
        urls = []
        for instance in instances:
            # resolves the address and port for the instance, using
            # the tag-defined address override if available or the
            # default resolution from consul
            service = instance.get("Service", dict())
            node = instance.get("Node", dict())
            _address = address or service.get("Address", None)
            if not _address:
                _address = node.get("Address", None)
            port = service.get("Port", 0)

            # detects host network mode by checking if the service
            # address matches the node address (no separate network),
            # in which case the port from consul is unreliable and
            # should be derived from the proxy.port tag instead
            node_address = node.get("Address", None)
            if _address == node_address and ports:
                self.debug(
                    "Instance %s detected as host network mode, ignoring port %d",
                    _address,
                    port,
                )
                port = 0

            # skips instance if no address could be resolved
            # from either the service or the node
            if not _address:
                self.debug("Skipping instance, missing address")
                continue

            # when a port range is defined via proxy.ports, expands
            # the instance to all ports in the range for load balancing
            # across multiple worker threads
            if ports and len(ports) > 1:
                self.debug("Instance %s expanding from port filter %s", _address, ports)
                for _port in sorted(ports):
                    url = str("http://%s:%d" % (_address, _port))
                    urls.append(url)
                continue

            # skips instance if port is missing and no port
            # filter is available to fall back on
            if not port and not ports:
                self.debug("Skipping instance %s, missing port", _address)
                continue

            # skips instance if its port is not within the
            # allowed set defined by the proxy.port tag
            if ports and not port in ports:
                self.debug(
                    "Skipping instance %s:%d, port not in allowed %s",
                    _address,
                    port,
                    ports,
                )
                continue

            # addresses the instance as a valid backend URL for
            # the service, using the tag-defined address override
            # if available or the default address resolution from consul
            url = str("http://%s:%d" % (_address, port))
            urls.append(url)
        return urls

    def _debug_entries(self, entries):
        self.debug(
            "Building consul proxy from %d entr%s",
            len(entries),
            "y" if len(entries) == 1 else "ies",
        )
        for service, domain, urls, tags in entries:
            self.debug(
                "  %s => %s (%d URL%s, %d tag%s)",
                service,
                domain,
                len(urls),
                "" if len(urls) == 1 else "s",
                len(tags),
                "" if len(tags) == 1 else "s",
            )

    def _debug_state(self):
        self.debug("Proxy state:")
        self.debug("  hosts (%d):", len(self.hosts))
        for name, value in netius.legacy.items(self.hosts):
            if isinstance(value, tuple):
                self.debug("    %s => %s (%d)", name, value[0], len(value))
            else:
                self.debug("    %s => %s", name, value)
        self.debug("  alias (%d):", len(self.alias))
        for name, value in netius.legacy.items(self.alias):
            self.debug("    %s => %s", name, value)
        self.debug("  auth (%d):", len(self.auth))
        for name, value in netius.legacy.items(self.auth):
            self.debug("    %s => %s", name, value.__class__.__name__)
        self.debug("  error_urls (%d):", len(self.error_urls))
        for name, value in netius.legacy.items(self.error_urls):
            self.debug("    %s => %s", name, value)
        self.debug("  redirect (%d):", len(self.redirect))
        for name, value in netius.legacy.items(self.redirect):
            self.debug("    %s => %s", name, str(value))
        self.debug("  regex (%d):", len(self.regex))
        for regex, value in self.regex:
            self.debug("    %s => %s", regex.pattern, value)
        self.debug("  auth_regex (%d):", len(self.auth_regex))
        for regex, value in self.auth_regex:
            auth_s = value.__class__.__name__ if value else "none"
            self.debug("    %s => %s", regex.pattern, auth_s)
        self.debug("  redirect_regex (%d):", len(self.redirect_regex))
        for regex, value in self.redirect_regex:
            self.debug("    %s => %s", regex.pattern, str(value))

    def _debug_auth_regex(self, domain, auth_regex):
        for regex, auth in auth_regex:
            auth_s = auth.__class__.__name__ if auth else "none"
            self.debug(
                "Registered auth regex '%s' for '%s' with auth type '%s'",
                regex.pattern,
                domain,
                auth_s,
            )


if __name__ == "__main__":
    server = ConsulProxyServer()
    server.serve(env=True)
else:
    __path__ = []
