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

import os

import netius


class TLSContextDict(dict):
    """
    Dictionary subclass that maps domain hostnames to their
    SSL context and certificate values. Designed to be assigned
    directly to `_ssl_contexts` on a server, so the SNI callback
    (`_ssl_callback`) can resolve per-host contexts at handshake
    time without any special handling.

    Subclasses must implement `cer_path` and `key_path` to
    define the on-disk layout for a given domain. At construction
    the dictionary is populated by scanning all provided domains
    and building an SSL context for each one that has both a
    certificate and a key file present.

    Supports live reload via `reload(domains)` which re-scans
    certificate files and only rebuilds contexts for domains
    whose files have changed on disk, using file modification
    times as the change signal. This is intentionally coarse
    (`os.path.getmtime` precision) to avoid unnecessary context
    rebuilds on every tick while still picking up renewed or
    newly issued certificates within a single poll cycle.

    Note that `reload` will not remove domains that have been
    deleted from disk - it only adds or updates. This is safe
    because a stale context simply keeps serving the previous
    certificate until the process is restarted.
    """

    def __init__(self, owner, domains, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.owner = owner
        self.mtimes = {}
        self.load(domains)

    def load(self, domains):
        secure = self.owner.get_env("SSL_SECURE", 1, cast=int)
        for domain in domains:
            if not self.has_definition(domain):
                continue
            cer_path = self.cer_path(domain)
            key_path = self.key_path(domain)
            values = dict(cer_file=cer_path, key_file=key_path)
            context = self.owner._ssl_ctx(values, secure=secure)
            self[domain] = (context, values)
            self.mtimes[domain] = self._mtime(domain)

    def reload(self, domains):
        # re-scans the certificate directory for new or updated
        # domains, only rebuilding contexts for domains whose
        # certificate files have changed on disk
        secure = self.owner.get_env("SSL_SECURE", 1, cast=int)
        changed = False
        for domain in domains:
            if not self.has_definition(domain):
                continue
            mtime = self._mtime(domain)
            if domain in self and self.mtimes.get(domain) == mtime:
                continue
            cer_path = self.cer_path(domain)
            key_path = self.key_path(domain)
            values = dict(cer_file=cer_path, key_file=key_path)
            context = self.owner._ssl_ctx(values, secure=secure)
            self[domain] = (context, values)
            self.mtimes[domain] = mtime
            changed = True
        return changed

    def has_definition(self, domain):
        cer_path = self.cer_path(domain)
        key_path = self.key_path(domain)
        if not os.path.exists(cer_path):
            return False
        if not os.path.exists(key_path):
            return False
        return True

    def cer_path(self, domain):
        raise netius.NotImplemented("Missing implementation")

    def key_path(self, domain):
        raise netius.NotImplemented("Missing implementation")

    def _mtime(self, domain):
        cer_path = self.cer_path(domain)
        key_path = self.key_path(domain)
        cer_mtime = os.path.getmtime(cer_path)
        key_mtime = os.path.getmtime(key_path)
        return max(cer_mtime, key_mtime)


class LetsEncryptDict(TLSContextDict):
    """
    TLS context dictionary that follows the Let's Encrypt
    `certbot` directory convention for certificate storage.

    Certificates are expected under `<letse_path>/<domain>/`
    with `fullchain.pem` and `privkey.pem` as the file names,
    which is the default layout produced by `certbot certonly`
    with the webroot or standalone plugins.

    The base path defaults to `/data/letsencrypt/etc/live` and
    can be overridden via the `letse_path` keyword argument.
    Note that `letse_path` must be set before calling the
    parent constructor, as `load` is invoked during `__init__`
    and relies on `cer_path` / `key_path` which read from it.

    When used with `_ssl_reload` on a periodic tick (eg: the
    proxy's `dns_tick`), newly issued certificates are picked
    up automatically without requiring a process restart.
    """

    def __init__(self, owner, domains, *args, **kwargs):
        self.letse_path = kwargs.get("letse_path", "/data/letsencrypt/etc/live")
        TLSContextDict.__init__(self, owner, domains, *args, **kwargs)

    def cer_path(self, domain):
        domain_path = os.path.join(self.letse_path, domain)
        return os.path.join(domain_path, "fullchain.pem")

    def key_path(self, domain):
        domain_path = os.path.join(self.letse_path, domain)
        return os.path.join(domain_path, "privkey.pem")
