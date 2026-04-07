# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

*

### Changed

*

### Fixed

* Strip `stacklevel` from `kwargs` in `Protocol` logging methods before forwarding to `Base` to prevent `TypeError: got multiple values for keyword argument 'stacklevel'`

## [1.38.0] - 2026-04-07

### Added

* Fallback module-level logger on `Protocol` logging methods for standalone client usage
* `_log_fallback()` helper on `Protocol` with `stacklevel` support for accurate caller file/line
* `setup_logging()` utility in `log` module for standalone script logging setup

### Fixed

* Guard `stacklevel` kwarg for Python < 3.8 in `log_python_3` and `Protocol._log_fallback`
* `proto=type` in `compat.py` passing wrong value to `create_connection`/`create_datagram_endpoint`
* `ssl=None` in `compat.py` wiping SSL flag for HTTPS connections and TLS servers

## [1.37.2] - 2026-04-07

### Fixed

* `KeyError` in proxy/SOCKS `_throttle` when delayed callback fires after connection removal - added `conn_map` guard before key lookup

## [1.37.1] - 2026-04-07

### Changed

* Consul proxy instance resolution logging downgraded from `info` to `debug` in `proxy_c.py`

## [1.37.0] - 2026-04-03

### Added

* TRACE log level and `patch_logging()` for fine-grained protocol-level debugging
* TRACE logging for HTTP client connection lifecycle, pooling, and reuse
* `trace()` method on `Protocol` and `Connection` base classes

## [1.36.2] - 2026-04-02

### Changed

* Resolve `min_version`, `max_version`, `protocol`, and `options` to human-readable names in SSL debug logging

## [1.36.1] - 2026-04-02

### Fixed

* Use `ssl.TLSVersion` enum values instead of `ssl.PROTOCOL_*` constants for `minimum_version`, fixing `ValueError` on PyPy
* Add `hasattr` guards for individual `ssl.TLSVersion` members to handle builds missing specific TLS version enums

## [1.36.0] - 2026-04-02

### Added

* Debug logging of SSL security options (SINGLE_DH_USE, SINGLE_ECDH_USE, CIPHER_SERVER_PREFERENCE, NO_COMPRESSION, NO_TICKET, NO_RENEGOTIATION, LEGACY_SERVER_CONNECT) in `_ssl_ctx_debug`
* Debug logging of SSL context at socket wrap time via stored `_ssl_secure` and `_ssl_context_options` attributes

### Changed

* Set `minimum_version` on SSL context based on `SSL_SECURE` level (secure>=2: TLSv1.2, secure>=1: TLSv1, secure>=0: SSLv3)

### Fixed

*

## [1.35.0] - 2026-04-02

### Added

* `ssl_verify` attribute stored on `Server` instance for runtime access to the SSL verification setting

### Changed

* Logging calls in `common.py` now use lazy `,` evaluation instead of `%` string formatting for deferred argument resolution
* Moved SSL debug logging from `_ssl_ctx_base` to `_ssl_ctx` and `_ssl_init` for complete post-setup context reporting
* Moved ALPN/NPN protocol debug logging from `_ssl_ctx_alpn`/`_ssl_ctx_npn` into `_ssl_ctx_debug`
* Clear `OP_NO_*` protocol flags when `SSL_SECURE` level is below threshold, allowing legacy TLS protocols on newer Python versions

### Fixed

* Added missing `OP_NO_TLSv1_3` check in `_ssl_ctx_debug` so TLSv1.3 is correctly reported as disabled

## [1.34.2] - 2026-04-01

### Added

* Debug logging of SSL verify flags and available X509 verification features (PARTIAL_CHAIN, STRICT, TRUSTED_FIRST) in `_ssl_certs`

## [1.34.1] - 2026-04-01

### Fixed

* `VERIFY_X509_PARTIAL_CHAIN` flag now added with `|=` instead of `=` to preserve existing SSL verify flags

## [1.34.0] - 2026-04-01

### Added

* Debug logging of OpenSSL version and SSL file paths (KEY, CER, CA, DH) at server startup
* `VERIFY_X509_PARTIAL_CHAIN` flag on SSL context when certificate verification is enabled, allowing validation of intermediate certificates without the full chain

## [1.33.1] - 2026-04-01

### Added

* Debug logging for SSL certificate configuration and SSL socket wrapping in `AbstractBase`, including verify mode, hostname checks, CA file paths, and context state

## [1.33.0] - 2026-04-01

### Added

* `address:<ips>` auth type in `proxy.auth-regex` consul tag for IP whitelist with CIDR support, multiple IPs separated by `+`
* Multiple auth types per rule via `|` separator in `proxy.auth-regex` (eg `simple:admin:pass|address:10.0.0.1`) evaluated with OR logic
* `_resolve_auth_type()` method in `ConsulProxyServer` extracting auth type parsing from `_resolve_auth_regex`

### Fixed

* `proxy.redirect-ssl` not being applied to suffix-expanded FQN aliases in `ConsulProxyServer` - redirect rules are now propagated inline during `_build_suffixes` so that eg `myapp.example.com` redirects to itself instead of the short name

## [1.32.0] - 2026-03-31

### Changed

* Logging methods (`debug`, `info`, `warning`, `error`, `critical`) in `Base`, `Connection`, and `Protocol` now accept `*args` for deferred `%`-formatting, avoiding string interpolation when the log level is disabled
* All log calls in `ConsulProxyServer` converted to use deferred formatting

### Fixed

* `_build_urls` in `ConsulProxyServer` now detects host network mode (service address matches node address) and derives ports from the `proxy.port` tag instead of using the unreliable consul-reported port

## [1.31.2] - 2026-03-31

### Fixed

* `_build_urls` in `ConsulProxyServer` skipping instances with host network mode (`Port: 0`) instead of expanding from the `proxy.port` tag filter

## [1.31.1] - 2026-03-31

### Added

* Debug logging for port filter resolution, URL building, and instance filtering in `ConsulProxyServer`

### Fixed

* `proxy.redirect-ssl` not being applied to `proxy.alias` domains or their suffix-expanded variants in `ConsulProxyServer`

## [1.31.0] - 2026-03-31

### Added

* `consul_skip_health` parameter (default `True`) in `ConsulProxyServer` to control whether unhealthy consul services are filtered out, configurable via `CONSUL_SKIP_HEALTH` env var

## [1.30.1] - 2026-03-31

### Added

* Unit tests for `proxy.alias` tag functionality in `ConsulProxyServerTest` covering registration, cleanup, suffix survival, and multi-tick rebuild persistence

### Fixed

* `proxy.alias` entries in `ConsulProxyServer` lost after each consul tick because `_build_suffixes` reset `_consul_aliases` - tag-based aliases are now tracked separately and preserved across rebuilds

## [1.30.0] - 2026-03-31

### Added

* `SSL_SILENT_REASONS` constant for SSL errors that should be silenced by reason string, starting with `WRONG_VERSION_NUMBER`
* `_debug_state()` method in `ConsulProxyServer` logging full proxy state (hosts, alias, auth, error_urls, redirect, regex, auth_regex, redirect_regex) after each consul tick
* Debug logging for `proxy.password`, `proxy.error-url`, and `proxy.redirect-ssl` tag registration in `ConsulProxyServer._apply_tags()`
* `proxy.alias` consul tag documented in `configuration.md`

### Changed

* SSL error handlers in `common.py`, `server.py`, and `client.py` now check `SSL_SILENT_REASONS` alongside `SSL_SILENT_ERRORS` for expected error classification

## [1.29.1] - 2026-03-31

### Added

* Debug logging for `proxy.password`, `proxy.error-url`, and `proxy.redirect-ssl` tag registration in `ConsulProxyServer._apply_tags()`

## [1.29.0] - 2026-03-31

### Added

* `proxy.alias` consul tag in `ConsulProxyServer` for declaring domain aliases (comma-separated) that route to the same backend service

### Fixed

* `ConsulProxyServer` tick scheduling now wrapped in try/finally so the discovery loop continues even if `_build_consul` or `trigger("tick")` raises an exception

## [1.28.4] - 2026-03-30

### Fixed

* Connection leak in `ReverseProxyServer` when the HTTP client returns a different connection than the one provided for reuse - the stale connection is now explicitly closed

## [1.28.3] - 2026-03-30

### Fixed

* `tick` event in `ConsulProxyServer` firing before async consul fetch completes - moved trigger inside `_apply()` callback so tick handlers see the updated host configuration

## [1.28.2] - 2026-03-30

### Changed

* Extracted `_debug_auth_regex()` helper method in `ConsulProxyServer` to improve readability of auth regex debug logging
* Added debug logging throughout `ConsulProxyServer` consul fetch lifecycle - no healthy instances, no valid URLs, instance/URL counts, fetch completion summary, and `None` responses from catalog/health endpoints
* Include exception details in consul HTTP error log messages

## [1.28.1] - 2026-03-09

### Added

* Debug logging of registered auth regex entries in `ConsulProxyServer._apply_tags()` showing pattern, domain and auth type

## [1.28.0] - 2026-03-09

### Added

* `proxy.auth-regex` consul tag for declarative regex-based auth rules with `none`, `password` and `simple:<user>:<pass>` auth types

## [1.27.0] - 2026-03-09

### Added

* `proxy.address` consul tag to override the default instance address resolution when building backend URLs
* Debug logging of fetched entries in `ConsulProxyServer._build_consul()`

## [1.26.0] - 2026-03-09

### Added

* Support for port range syntax (e.g. `8080-8085`) in `proxy.port` and `proxy.ports` consul tags

## [1.25.1] - 2026-03-06

### Added

* Docstring for `base_connection` method in `AbstractBase` explaining the `_base` flag semantics

### Fixed

* PROXY protocol middleware now skips base (`_base`) and explicitly excluded (`_skip_proxy`) connections, preventing outbound client connections from being validated for PROXY headers

## [1.25.0] - 2026-03-06

### Added

* `REMOTE_PORT` variable in WSGI environ dictionary, exposing the client's source port as a string
* `tick` event trigger in `ConsulProxyServer` tick loop for external monitoring of the consul discovery process

### Changed

*

### Fixed

* Consul proxy polling stops permanently if `_consul_fetch()` raises an unexpected exception - tick loop now catches errors, logs them, and always reschedules the next poll

## [1.24.0] - 2026-02-14

### Added

* `ConnectionCompat` mixin in `mixin.py` extracting backward-compatible `Connection` delegation methods (`socket`, `renable`, `is_restored()`, `enable_read()`, etc.) from `StreamProtocol`
* `ConnectionCompat` applied to `TransportStream` so it exposes `is_restored()` and other throttle-related methods
* Throttle unit tests for proxy server covering both Connection and TransportStream paths

### Changed

* `StreamProtocol` now inherits from `ConnectionCompat` mixin instead of defining delegation methods inline
* `_throttle()` in `ProxyServer` and `SocksServer` resolves `TransportStream` to its `_protocol` for `conn_map` key lookup

### Fixed

* `AttributeError: 'TransportStream' object has no attribute 'is_restored'` in proxy throttle callbacks when using protocol-based architecture

## [1.23.2] - 2026-02-13

### Added

* POST, PUT and DELETE integration tests for `ReverseProxyIntegrationTest` verifying request body forwarding through the proxy

### Fixed

* Proxy POST/PUT body data silently dropped when backend connection not yet established - `StreamProtocol.send()` now buffers data via `_delay_send()` instead of returning 0 when transport is None
* `HTTPClientProtocol.connection_made()` now flushes buffered data after sending request headers, ensuring proxy-forwarded body chunks reach the backend
* `DatagramProtocol.send_to()` aligned with `StreamProtocol.send()` guards - added `is_closed_or_closing()` and missing transport checks for consistency

## [1.23.1] - 2026-02-13

### Fixed

* `ImportError: No module named http` on Python 2.7/PyPy - `http.client` import now uses conditional fallback with skip guard for integration tests

## [1.23.0] - 2026-02-13

### Added

* `address` property on `StreamProtocol` delegating to underlying `Connection` for backward compatibility with proxy code that accesses `protocol.address`
* End-to-end integration tests for `ReverseProxyServer` exercising the full proxy data flow through a real server with httpbin backend
* Reverse proxy example (`examples/proxy/proxy_reverse.py`) showing minimal setup for forwarding requests to a backend

## [1.22.1] - 2026-02-13

### Fixed

* Protocol close event not firing when `_loop` is None - `delay(finish)` ran synchronously inside `close_c()`, calling `destroy()` → `unbind_all()` before `trigger("close")` could fire, leaving stale `conn_map` entries in the proxy
* `NoneType` attribute error on `StreamProtocol.send()` when transport is already closed - added guard for `_transport` being None

## [1.22.0] - 2026-02-13

### Added

* Base-compatible stub methods on `Agent` so that `Container` works with both old (`Base`) and new (`Agent`/`Protocol`) architectures without defensive guards
* `ClientAgent.connect()` method with `_container_loop` support for protocol-based connections to join the container's shared poll
* Event relay system in `ClientAgent._relay_protocol_events()` bridging protocol events to client-level observers
* Container tests (`netius.test.base.container`) covering setup, event bindings, lifecycle, and cleanup
* Data flow tests for `ReverseProxyServer` covering request routing, response relay, error handling, and lifecycle management

### Changed

* `Container.apply_base()` now sets `_container_loop` on non-`Base` objects to enable dual architecture multiplexing
* `HTTPClient.method()` uses `_container_loop` as default loop when available for container integration
* Proxy throttle methods use `self.reads()` / `self.writes()` since connections are owned by the proxy server

### Fixed

* `AttributeError` when running `ConsulProxyServer` due to `Agent` subclasses missing `load`, `unload`, `ticks`, and other `Base`-expected methods

## [1.21.0] - 2026-02-07

### Added

* `conf_override` context manager for temporarily overriding configuration values
* `ConsulProxyServer` for Consul-based service discovery in the reverse proxy

### Fixed

* SSLError propagation in `on_write` breaking the main loop during SSL handshake failures

## [1.20.7] - 2025-09-30

### Fixed

* Binary check for empty string

## [1.20.6] - 2025-09-30

### Changed

* Added additional validation to the nameserver file

## [1.20.5] - 2025-03-15

### Fixed

* CONTENT_LENGTH issue in HTTP client where it was being passed as integer and not string

## [1.20.4] - 2025-02-17

### Fixed

* Reduces race conditions on message flushing for Logstash handler

## [1.20.3] - 2025-02-17

### Fixed

* Issue with Logstash handler on flush detection

## [1.20.2] - 2025-02-17

### Fixed

* Prevents multi level logging, effectively avoiding infinite recursion

## [1.20.1] - 2025-02-17

### Fixed

* Issue with the `LogstashHandler` when context calling raises issues

## [1.20.0] - 2024-05-30

### Added

* Support for HTTP client handling of plain HTTP message with no content length defined - finished at connection closed

### Changed

* Code structure to make it compliant with `black`

## [1.19.14] - 2024-04-25

### Added

* Support for selective logging of stacktrace in `LogstashHandler`

## [1.19.13] - 2024-04-23

### Fixed

* SMTP logging issue

## [1.19.12] - 2024-04-23

### Changed

* Much richer logging context support

## [1.19.11] - 2024-04-23

### Fixed

* Race condition when re-using loggers

## [1.19.10] - 2024-04-23

### Changed

* Flexible logger flush timeout using `LOGGER_FLUSH_TIMEOUT` env variable

## [1.19.9] - 2024-04-23

### Changed

* Support for logger flush timeout

## [1.19.8] - 2024-04-23

### Changed

* Moved flush operation up in the chain

## [1.19.7] - 2024-04-23

### Changed

* Flush of loggers before on logger unloading

## [1.19.6] - 2024-04-23

### Changed

* Optional `raise_e` support in `LogstashHandler`

## [1.19.5] - 2024-04-23

### Fixed

* Support for multiple messages for same SMTP session - [#40](https://github.com/hivesolutions/netius/issues/40)

## [1.19.4] - 2024-04-22

### Added

* Support for `.env` file loading
* LogstashHandler support using `LOGGING_LOGSTASH` and `LOGSTASH_BASE_URL`

## [1.19.3] - 2024-01-18

### Changed

* Improved the structure of the Postmaster message

### Fixed

* Context information `tos` in the Postmaster email handling
* Critical issue with the SMTP client when connecting with SMTP servers with older versions of OpenSSL

## [1.19.2] - 2024-01-17

### Added

* Support for Postmaster email in SMTP relay using the `POSTMASTER` configuration value
* Support for the `exception` event in the `Connection` triggered when a exception is raised in the connection domain

## [1.19.1] - 2022-10-15

### Added

* Support for `allowed_froms` in SMTP relay

### Changed

* Improved support in the `legacy.py` module

## [1.19.0] - 2022-05-02

### Added

* Support for `SSL_CONTEXT_OPTIONS` to netius SSL context creation

## [1.18.4] - 2022-04-26

### Added

* Better debug support for connection address

### Fixed

* Custom listing using both `apache` and `legacy` for `LIST_ENGINE`

## [1.18.3] - 2021-11-01

### Added

* Better debug support for connection address

## [1.18.2] - 2021-05-01

### Added

* Support for `redirect_regex` in `proxy_r`
