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

*

## [1.53.13] - 2026-04-28

### Fixed

* Protocol re-usage in proxy reverse

## [1.53.12] - 2026-04-27

### Fixed

* Version bumping number

## [1.53.11] - 2026-04-27

### Changed

* New verbose flag on upload

## [1.53.10] - 2026-04-27

### Fixed

* Issue with deploy script

## [1.53.9] - 2026-04-27

### Changed

* Updated the deploy infrastructure

## [1.53.8] - 2026-04-27

### Added

* Additional HTTP status codes to `CODE_STRINGS`: 226 (IM Used), 308 (Permanent Redirect), 418 (I'm a teapot), 422 (Unprocessable Entity) and 451 (Unavailable For Legal Reasons)
* Module-level `GZIP_LEVEL` and `EMPTY_CODES` constants in `netius.servers.http` replacing previously inlined magic numbers

### Fixed

* Reverse proxy `Connection` response header now matches the actual front-end socket lifecycle (logical AND of the client request and upstream response keep-alive flags), preventing the HTTP/1.0 client case where the proxy advertised `keep-alive` but immediately closed the socket

## [1.53.7] - 2026-04-17

### Changed

* Add `PEER_DID_NOT_RETURN_A_CERTIFICATE`, `NO_SUITABLE_SIGNATURE_ALGORITHM` and `TLSV1_ALERT_UNKNOWN_CA` to `SSL_SILENT_REASONS`
* Sort `SSL_SILENT_REASONS` tuple alphabetically

### Fixed

* Guard against `None` connection in `ProxyServer` throttle callbacks when the transport is already closed

## [1.53.6] - 2026-04-15

### Changed

* Added more ignore SSL errors

## [1.53.5] - 2026-04-15

### Changed

* Add `UNKNOWN_PROTOCOL`, `VERSION_TOO_LOW` and `BAD_KEY_SHARE` to `SSL_SILENT_REASONS`

## [1.53.4] - 2026-04-15

### Changed

* Move `bytes` serialization handling from `Parser.info_dict()` to DIAG endpoints using a custom `DiagEncoder` JSON encoder

## [1.53.3] - 2026-04-15

### Fixed

* Fix `TypeError: Object of type bytes is not JSON serializable` in DIAG `/connections` endpoint by excluding raw `bytes` fields from `Parser.info_dict()`

## [1.53.2] - 2026-04-15

### Changed

* Replace `diag_owner` container flag with process-level `_DIAG_INSTANCE` singleton guard in `AbstractBase` to prevent duplicate diag server binding

## [1.53.1] - 2026-04-15

### Fixed

* Disable diagnostics on the `Container` itself when `diag_owner` is set to avoid duplicate port binding

## [1.53.0] - 2026-04-15

### Added

* `diag_owner` flag in `Container` to restrict diagnostics to the owner base, avoiding port binding conflicts in multi-base setups

### Changed

* Add docstrings to `Container.add_base()`, `remove_base()` and `start_base()`
* Pass `diag_owner=True` in `ProxyServer` container to prevent child clients from binding to the diag port

## [1.52.3] - 2026-04-15

### Changed

* Move `unload_diag()` to the top of `cleanup()` so the diagnostics app is stopped before other resources are torn down
* Log a warning with exception details when `unload_diag()` fails instead of silently swallowing the error

## [1.52.2] - 2026-04-14

### Changed

* Remove redundant frontend connection state check in `ProxyServer._on_prx_close()`
* Use `hasattr` guard for `is_closed()` check in `_connect_stream_native` to support non-Netius protocol instances

## [1.52.1] - 2026-04-14

### Added

* Test suite for `ConnectionCompat` mixin covering all delegation properties, setters, defaults, and no-connection fallbacks (42 tests)

### Changed

* Propagate `waiting`, `busy`, `state`, and `error_url` pending values in `StreamProtocol.connection_made()` to the underlying connection

### Fixed

* Guard against orphan connections in `_connect_stream_native` by checking if the protocol is already closed before wrapping the connection

## [1.52.0] - 2026-04-14

### Added

* `id`, `status`, `waiting`, `busy`, `state`, and `error_url` delegation properties in `ConnectionCompat` mixin for full Protocol/Connection compatibility

### Changed

* Revert `getattr` safety guards in `ProxyServer._on_prx_close()` and `_on_prx_error()` to direct attribute access now that `ConnectionCompat` provides the delegated properties

## [1.51.0] - 2026-04-14

### Added

* `info_dict()` override in `HTTPClient` exposing `auto_release`, `available_count`, and `available_keys` (full mode) for DIAG connection pool visibility

### Changed

* Use safe `getattr` for attribute access on `_connection` in `ProxyServer._on_prx_close()` since it may be a Connection or HTTPProtocol

### Fixed

* Fix `AttributeError` in `ProxyServer._on_prx_close()` when logging unmapped backend connection close (`connection.id` on `None`)

## [1.50.0] - 2026-04-14

### Added

* `conn_map_size` field in `ProxyServer.info_dict()` for monitoring the connection mapping table size in DIAG
* Warning log in `ReverseProxyServer` when a proxy connection is reassigned while the old connection is still waiting for a response
* Debug/warning logging in `ProxyServer._on_prx_close()` for unmapped backend close callbacks and stale frontend connections

## [1.49.0] - 2026-04-14

### Added

* `owner` field in `info_dict()` exposing the connection owner's name in the DIAG `/connections` endpoint

### Changed

* Enhance `CompatLoop.connect_stream()` logging with owner name, full connection ID, and info-level output

## [1.48.2] - 2026-04-14

### Changed

* Add debug logging to `CompatLoop.connect_stream()` for connection success and error events
* Elevate duplicate protocol pool replacement log in `HTTPClient` from debug to warning level

## [1.48.1] - 2026-04-14

### Fixed

* Explicitly close stale protocols in `HTTPClient` before discarding them to avoid leaking connections
* Close previous pooled protocol in `HTTPClient` when a new protocol is stored under the same key to prevent connection leaks

## [1.48.0] - 2026-04-13

### Added

* `last_recv_ts` and `last_send_ts` timestamps in `DiagConnection` exposed via `info_dict()` and the DIAG `/connections` endpoint

### Fixed

* Ensure `info_dict()` returns JSON-safe values on PyPy by converting bytes address components to strings and extracting `.value` from socket enum attributes

## [1.47.1] - 2026-04-13

### Fixed

* Capture SMTP session data before `callback_error` fires so that deliverability info (greeting, transcript, TLS details, etc.) is available in `context["sessions"]` on error

## [1.47.0] - 2026-04-13

### Added

* `mx_dedup` parameter in `SMTPClient.message()` to control whether domains sharing the same MX host are grouped into a single connection, defaults to `False` to avoid `451 4.3.0` rejections from servers that refuse multi-domain transactions

## [1.46.1] - 2026-04-13

### Changed

* Added `SSLV3_ALERT_CERTIFICATE_UNKNOWN` to `SSL_SILENT_REASONS` so that certificate unknown alerts are silenced

## [1.46.0] - 2026-04-13

### Added

* Sequential MX session mode for SMTP client (`sequential` parameter in `message()`), establishes one connection at a time per MX host to reduce pressure on remote servers that drop concurrent connections from the same source

### Changed

* Extract `initiate_mx()` from `on_mx_resolved()` in SMTP client for clearer separation of DNS collection and connection initiation phases

## [1.45.1] - 2026-04-13

### Changed

* Added `NO_SHARED_CIPHER` to `SSL_SILENT_REASONS` so that no shared cipher errors are silenced

### Fixed

* Report MX lookup failures as errors instead of silently dropping recipients, invoke `callback_error` per failed domain and fire `callback` when all domains fail
* Normalize MX host dedup key with `.rstrip(".").lower()` to avoid case/trailing-dot mismatches splitting identical hosts into separate connections

## [1.45.0] - 2026-04-12

### Added

* SMTP session transcript capture gated by `SMTP_CAPTURE_TRANSCRIPT` environment variable, records the full command/response conversation (excluding DATA payload) with timestamps per entry, capped at 50 entries per session
* SMTP Relay and SMTP Activity Tracking sections in `doc/configuration.md`

## [1.44.1] - 2026-04-12

### Fixed

* Decode `mx_host` bytes to string via `legacy.str` in SMTP session deliverability data

## [1.44.0] - 2026-04-12

### Changed

* Skip SSL error reason normalization for `SSL_VALID_ERRORS` (`WANT_READ`/`WANT_WRITE`) to avoid unnecessary string operations on the hot path

### Fixed

* Capture TLS version and cipher in `quit_t` before socket close instead of in `on_close` where the socket is already closed
* Derive `starttls` from actual TLS negotiation state instead of the initial `stls` parameter
* Add `_ssl_reason` fallback that parses `str(error)` when `error.reason` is `None` (eg: OpenSSL 3 error codes not mapped in the runtime's SSL data tables)

## [1.43.1] - 2026-04-12

### Fixed

* Normalize SSL error reason in `server.py` and `client.py` for PyPy compatibility (9 additional sites missed in 1.41.1)

## [1.43.0] - 2026-04-12

### Added

* `server_agent` field in activity webhook payload using `netius.IDENTIFIER`
* `contents_size` field in activity webhook payload

## [1.42.0] - 2026-04-12

### Added

* TLS session info (`tls_version`, `tls_cipher`, `starttls`) in SMTP client session deliverability data
* EHLO `capabilities` list in session deliverability data
* MX hostname (`mx_host`) from DNS resolution in session deliverability data
* Per-session `error` field capturing exceptions from failed SMTP sessions
* Message `message_size` in session deliverability data

## [1.41.1] - 2026-04-12

### Fixed

* Normalize SSL error reason string for PyPy compatibility so that `SSL_SILENT_REASONS` matching works on both CPython and PyPy runtimes

## [1.41.0] - 2026-04-12

### Added

* RFC 2047 encoded word subject decoding in `ActivityRelaySMTPServer` so that MIME-encoded subjects are posted as clean unicode strings
* Per-domain SMTP session deliverability info (`sessions` list) in the activity webhook payload including remote host, port, greeting, queue response, duration and recipients
* `greeting`, `queue_response` and `start_time` attributes on `SMTPConnection` (client) to capture remote server identification and delivery confirmation
* `context` parameter passed to `callback` in `SMTPClient.message()` containing session deliverability data

### Changed

* Reordered `on_relay_smtp` and `on_relay_error_smtp` arguments to lead with `connection`, `context` (and `exception` for error) for consistency

## [1.40.0] - 2026-04-11

### Added

* `ActivityRelaySMTPServer` middleware in `extra/smtp_a.py` that posts delivery status (delivered/failed) to an external HTTP endpoint after each relay operation, configurable via `SMTP_ACTIVITY_URL` and `SMTP_ACTIVITY_SECRET` environment variables
* `_ssl_reload()` method on the base server to reload SSL contexts from disk when certificate files have changed, without requiring a process restart
* `reload(domains)` and `_mtime(domain)` methods on `TLSContextDict` for mtime-based certificate change detection
* `datagram`, `socket_family`, and `socket_type` fields to connection `info_dict` for socket-level diagnostics

### Changed

* Added `RECORD_LAYER_FAILURE` to `SSL_SILENT_REASONS` so that record layer failures are treated as expected (silent) SSL errors

## [1.39.6] - 2026-04-10

### Fixed

* Fix DNS client tests failing on Python 2 due to unbound method on class attribute callback storage

## [1.39.5] - 2026-04-10

### Fixed

* Close datagram protocol after DNS query callback in `DNSClient.query_s()` to prevent connection leak

## [1.39.4] - 2026-04-10

### Added

* Stack trace logging for connections created with `None` address to help diagnose origin of address-less connections

## [1.39.3] - 2026-04-10

### Added

* `cls` and `is_base` fields to connection `info_dict` for class and protocol-mode diagnostics

## [1.39.2] - 2026-04-10

### Added

* `has_starter`, `starters_count`, `socket_fileno`, and `proxy_pending` fields to connection `info_dict` for richer diagnostics

## [1.39.1] - 2026-04-10

### Changed

* Logging calls across the codebase now use lazy `,` evaluation instead of `%` string formatting for deferred argument resolution

## [1.39.0] - 2026-04-10

### Added

* Handshake timeout for the PROXY protocol middleware to close zombie connections that never complete the handshake (default 30s, configurable via `PROXY_HANDSHAKE_TIMEOUT`)
* Trace logging for PROXY handshake EOF and blocked read events

## [1.38.11] - 2026-04-10

### Added

* Documentation page for the built-in diagnostics server (`doc/diag.md`)

### Fixed

* Guard against `None` address in `DiagConnection._resolve()` to prevent `TypeError` on the `/connections` diag endpoint

## [1.38.10] - 2026-04-10

### Fixed

* Use byte literals for UTF-8 test strings in DKIM tests for Python 2 compatibility

## [1.38.9] - 2026-04-10

### Fixed

* Fix `dkim_body` simple canonicalization producing incorrect body hash on Python 3 due to `re.sub` zero-length match behavior with `*` quantifier

## [1.38.8] - 2026-04-09

### Changed

* Refactored `dkim_fold` and `dkim_fold_b` to use list buffer with join for better performance

## [1.38.7] - 2026-04-09

### Fixed

* DKIM `b=` field is now placed on its own continuation line to prevent `dkim_fold` from splitting the tag across lines
* `dkim_fold` no longer mangles header values when no space is found within the fold length

## [1.38.6] - 2026-04-09

### Changed

* DKIM signing now uses relaxed/simple header canonicalization for better compatibility with strict verifiers (Microsoft, Yahoo)
* DKIM signature `b=` value is now folded to comply with RFC 5322 line length limits

### Fixed

* `Headers.pop()` now normalizes keys so that string keys correctly match byte keys from `rfc822_parse`

## [1.38.5] - 2026-04-09

### Added

* Warning log when `HTTPClient` synchronous call is made on an already running event loop

### Changed

* `LOGGING_LOGSTASH` config now also checks `NETIUS_LOGGING_LOGSTASH` with fallback to the original key

## [1.38.4] - 2026-04-09

### Changed

* Include thread ID in `TRACE_FORMAT` log output for easier multi-threaded debugging
* Set default `stacklevel=2` in `_trace` log method on Python 3.8+ for accurate caller file/line
* Add trace logging calls in `HTTPClient` synchronous request flow

## [1.38.3] - 2026-04-08

### Fixed

* Guard against None parsed URL in HTTPProtocol.send_request when connection closes during SSL handshake

## [1.38.2] - 2026-04-08

### Fixed

* Correct `stacklevel` propagation through `Protocol` → `Base` logging chain for accurate `%(pathname)s:%(lineno)d` in `TRACE_FORMAT`
* Adjust `stacklevel` in `_log_fallback` to compensate for shorter call chain vs `Base` path

## [1.38.1] - 2026-04-07

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
