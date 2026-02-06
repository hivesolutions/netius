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
    (`proxy.redirect-ssl=true`), and port filtering
    (`proxy.port=<port1,port2,...>` or alias `proxy.ports`).
    """

    def __init__(
        self,
        consul_url="http://localhost:8500",
        consul_token=None,
        consul_tag="proxy.enable=true",
        consul_poll_interval=60.0,
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
            host_suffixes=host_suffixes,
        )
        self._consul_hosts = set()
        self._consul_aliases = set()

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
            self.host_suffixes = self.get_env(
                "HOST_SUFFIXES", self.host_suffixes, cast=list
            )
        self.info("Using Consul at %s for service discovery" % self.consul_url)
        self.info("Consul poll interval set to %.2fs" % self.consul_poll_interval)
        self._consul_tick(timeout=self.consul_poll_interval)

    def _build_consul(self, entries):
        self._build_hosts(entries)
        self._build_suffixes()

    def _build_hosts(self, entries):
        # removes any previously registered consul-managed hosts,
        # auth, error URLs and redirects to ensure a clean state
        # before rebuilding the complete set of entries
        for host in self._consul_hosts:
            self.hosts.pop(host, None)
            self.auth.pop(host, None)
            self.error_urls.pop(host, None)
            self.redirect.pop(host, None)
        self._consul_hosts = set()

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
                "Registered Consul service '%s' as '%s' with %d instance(s)"
                % (service, domain, len(urls))
            )

    def _build_suffixes(self, alias=True, redirect=True):
        # removes any previously registered consul-managed aliases
        # and hosts to ensure a clean state before rebuilding
        for fqn in self._consul_aliases:
            self.alias.pop(fqn, None)
            self.hosts.pop(fqn, None)
        self._consul_aliases = set()

        for host_suffix in self.host_suffixes:
            self.info("Registering %s host suffix" % host_suffix)
            for _alias, value in netius.legacy.items(self.alias):
                fqn = _alias + "." + str(host_suffix)
                self.alias[fqn] = value
                self._consul_aliases.add(fqn)
            for name, value in netius.legacy.items(self.hosts):
                fqn = name + "." + str(host_suffix)
                if alias:
                    self.alias[fqn] = name
                else:
                    self.hosts[fqn] = value
                self._consul_aliases.add(fqn)

    def _consul_fetch(self):
        # fetches all eligible service data from the consul catalog
        # and health endpoints (I/O bound, safe to run in a thread)
        entries = []
        services = self._consul_services()
        for service, tags in netius.legacy.iteritems(services):
            # verifies that the current service contains the required
            # proxy tag, skipping it in case it does not
            if self.consul_tag not in tags:
                continue

            # determines the domain name for the service, using
            # the proxy.name or proxy.domain tag if available or
            # falling back to the service name itself (lowercased)
            domain = self._resolve_domain(service, tags)

            # retrieves the set of healthy instances for the
            # current service from the consul health endpoint
            instances = self._consul_health(service)
            if not instances:
                continue

            # resolves the optional port filter from the consul
            # tags, limiting which ports are considered valid
            ports = self._resolve_ports(tags)

            # builds the complete set of backend URLs from the
            # healthy instances, filtering out any invalid ones
            urls = self._build_urls(instances, ports=ports)
            if not urls:
                continue

            # adds the resolved entry to the list of entries to
            # be applied later if necessary
            entries.append((service, domain, urls, tags))
        return entries

    def _consul_tick(self, timeout=30.0):
        # offloads the consul discovery I/O to a background thread
        # to avoid blocking the main event loop during HTTP requests,
        # the results are then applied back on the main loop via delay_s
        def _fetch():
            entries = self._consul_fetch()

            # builds the consult structures using the fetched entries,
            # then schedules the next tick after the configured, this
            # function is meant to run in the main event loop, so it
            # can safely modify the proxy configuration without any
            # kind of locking concerns
            def _apply():
                self._build_consul(entries)
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
            return dict()
        return result

    def _consul_health(self, service):
        url = (
            self.consul_url
            + "/v1/health/service/"
            + netius.legacy.quote(service)
            + "?passing=true"
        )
        result = self._consul_get(url)
        if result == None:
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
                self.info(
                    "Consul request error for %s: %s" % (url, result.get("message"))
                )
                return None
            if result["code"] != 200:
                self.info("Consul returned %d for %s" % (result["code"], url))
                return None
            data = result.get("data", b"")
            return json.loads(data)
        except Exception:
            self.info("Failed to retrieve Consul data from %s" % url)
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

    def _resolve_ports(self, tags):
        value = None
        for tag in tags:
            if tag.startswith("proxy.port=") and value == None:
                value = tag[len("proxy.port=") :]
            elif tag.startswith("proxy.ports=") and value == None:
                value = tag[len("proxy.ports=") :]
        if not value:
            return None
        ports = set()
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ports.add(int(part))
            except ValueError:
                continue
        return ports if ports else None

    def _apply_tags(self, domain, tags):
        for tag in tags:
            if tag.startswith("proxy.password="):
                password = tag[len("proxy.password=") :]
                if password:
                    simple_auth = netius.SimpleAuth(password=password)
                    self.auth[domain] = simple_auth
            elif tag.startswith("proxy.error-url="):
                error_url = tag[len("proxy.error-url=") :]
                if error_url:
                    self.error_urls[domain] = str(error_url)
            elif tag == "proxy.redirect-ssl=true":
                self.redirect[domain] = (domain, "https")

    def _build_urls(self, instances, ports=None):
        urls = []
        for instance in instances:
            service = instance.get("Service", dict())
            node = instance.get("Node", dict())
            address = service.get("Address", None)
            if not address:
                address = node.get("Address", None)
            port = service.get("Port", 0)
            if not address or not port:
                continue
            if ports and port not in ports:
                continue
            url = str("http://%s:%d" % (address, port))
            urls.append(url)
        return urls


if __name__ == "__main__":
    server = ConsulProxyServer()
    server.serve(env=True)
else:
    __path__ = []
