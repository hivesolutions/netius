# Configuration

#### General

| Name           | Type   | Default     | Description                                                                                                                                                                                                                                                                  |
| -------------- | ------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HOST**       | `str`  | `127.0.0.1` | The listening address of the server (eg: `127.0.0.1` or `0.0.0.0`).                                                                                                                                                                                                          |
| **PORT**       | `int`  | `9090`      | The port the server will listen at (eg: `8080`).                                                                                                                                                                                                                             |
| **IPV6**       | `bool` | `False`     | If IPv6 should be enabled for the server/client, by default the created socket is either IPV4 or IPv6 only, note that under Linux dual stack is provided for "free" for IPv6 stacks.                                                                                         |
| **SSL**        | `bool` | `False`     | If the server is going to use SSL/TLS (Secure Sockets Layer).                                                                                                                                                                                                                |
| **UNIX_PATH**  | `str`  | `$PORT`     | The path to the file that is going to be used for Unix domain sockets, note that under the hood the port variable is used as the path for the socket.                                                                                                                        |
| **BACKLOG**    | `int`  | `SOMAXCONN` | The number of connections to be hold waiting in queue while pending accept operation.                                                                                                                                                                                        |
| **ALLOWED**    | `list` | `[]`        | Sequence of IP or Subnet addresses (eg: 172.16.0.0/16) that are considered to be allowed as clients for a given server, any client connection with an IP address not contained in the list will be dropped.                                                                  |
| **CHILDREN**   | `int`  | `0`         | Number of child processes that are meant to be created upon launch using a pre-fork approach.                                                                                                                                                                                |
| **CHILD**      | `int`  | `0`         | Same as `CHILDREN`.                                                                                                                                                                                                                                                          |
| **MIDDLEWARE** | `list` | `[]`        | The middleware as a set of strings (eg: proxy) that is going to be loaded into the instance, the notation used to define the modules to be loaded should be underscore based (notice that loading extra middleware into an instance may impact the performance of the same). |
| **SECURE**     | `bool` | `True`      | Control if a secure production environment should be ensured by hiding some critical information (eg: version).                                                                                                                                                              |

#### Logging

| Name                     | Type    | Default | Description                                                                        |
| ------------------------ | ------- | ------- | ---------------------------------------------------------------------------------- |
| **LOGGER_FLUSH_TIMEOUT** | `float` | `60.0`  | The amount of time in seconds in between flush operations on the logging handlers. |

#### Internal

| Name                   | Type    | Default | Description                                                                                                                                                                                                                                           |
| ---------------------- | ------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ASYNCIO**            | `bool`  | `False` | If the asyncio mode should be used, meaning that the loop retrieval method to be used is the one provided by the asyncio module, in case no asyncio support exists the flag is ignored.                                                               |
| **COMPAT**             | `bool`  | `False` | If the "heavyweight" compatibility mode should be ensured so that some operations will use an `asyncio` compatible way of performing execution, using this mode has performance implications.                                                         |
| **POLL**               | `str`   | auto    | The name of the polling system to be used for the controlling of the main event loop, inferred from the capabilities of the current system (eg: `epoll`, `kqueue`, `poll` or `select`).                                                               |
| **POLL_TIMEOUT**       | `float` | `0.25`  | The timeout in seconds for each of the iteration of the event loop, this value should be carefully chosen as it controls the minimum resolution of a delayed execution.                                                                               |
| **KEEPALIVE_TIMEOUT**  | `int`   | `300`   | The amount of time in seconds that a connection is set as idle until a new refresh token is sent to it to make sure that it's still online and not disconnected, make sure that this value is high enough that it does not consume to much bandwidth. |
| **KEEPALIVE_INTERVAL** | `int`   | `30`    | The time between the retrying of "ping" packets, this value does not need to be too large and should not be considered too important (may be calculated automatically).                                                                               |
| **KEEPALIVE_COUNT**    | `int`   | `3`     | The amount of times the "ping" packet is re-sent until the connection is considered to be offline and is dropped.                                                                                                                                     |

#### Diagnostics

| Name            | Type   | Default     | Description                                                                                                                                                 |
| --------------- | ------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DIAG**        | `bool` | `False`     | If the diagnostics system should be launched for the current system, if launched the system will be running as an HTTP server on localhost under port 5050. |
| **DIAG_SERVER** | `str`  | `netius`    | The server that is going to be used for serving the diagnostics system infrastructure.                                                                      |
| **DIAG_HOST**   | `str`  | `127.0.0.1` | The hostname that is going to be used when launching the diagnostics system.                                                                                |
| **DIAG_PORT**   | `int`  | `5050`      | The TCP port that is going to be used when launching the diagnostics system.                                                                                |

#### SSL

| Name                    | Type   | Default    | Description                                                                                                                                                                                            |
| ----------------------- | ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **CER_FILE**            | `str`  | `None`     | The path to the certificate file to be used for SSL (PEM format).                                                                                                                                      |
| **KEY_FILE**            | `str`  | `None`     | The path to the private key file to be used for SSL (PEM format).                                                                                                                                      |
| **CA_FILE**             | `str`  | `None`     | The path to the CA (certificate authority) file to be used for SSL (PEM format).                                                                                                                       |
| **CA_ROOT**             | `bool` | `True`     | If the default CA file/files should be loaded from the current environment.                                                                                                                            |
| **SSL_VERIFY**          | `bool` | `False`    | If the standard SSL verification process (CA) should be performed for the connection, if the current instance is a client the host verification will also be performed for the server side host.       |
| **SSL_HOST**            | `str`  | `None`     | The hostname that is going to be used in for domain verification, this value is only user in server to be able to verify client certificates against an expected host.                                 |
| **SSL_FINGERPRINT**     | `str`  | `None`     | The fingerprint (SHA1 digest of certificate) that is going to be used to verify the integrity of a peer/client certificate against the expected one.                                                   |
| **SSL_DUMP**            | `bool` | `False`    | If the certificate information should be dumped to the directory specified by the `SSL_PATH` configuration value.                                                                                      |
| **SSL_PATH**            | `str`  | `/tmp/ssl` | Path to the directory where the SSL dump information is going to be placed, in case the directory does not exist it's created.                                                                         |
| **SSL_SECURE**          | `int`  | `1`        | The level of security to be used for the suite of SSL (eg: some protocols removed).                                                                                                                    |
| **SSL_CONTEXT_OPTIONS** | `list` | `[]`       | List of strings that defined the options to be used in the SSL context creation (eg: `OP_NO_SSLv2`) for more information check [ssl module documentation](https://docs.python.org/3/library/ssl.html). |
| **SSL_CONTEXTS**        | `dict` | `{}`       | The dictionary that associates the various domains that may be served with different context values (certificate, key, etc) for such domain.                                                           |
| **CER_DATA**            | `str`  | `None`     | Equivalent to `CER_FILE` but with explicit (data) contents of the file (`\n` escaped).                                                                                                                 |
| **KEY_DATA**            | `str`  | `None`     | Equivalent to `KEY_FILE` but with explicit (data) contents of the file (`\n` escaped).                                                                                                                 |
| **CA_DATA**             | `str`  | `None`     | Equivalent to `CA_FILE` but with explicit (data) contents of the file (`\n` escaped).                                                                                                                  |

#### File Serving

| Name            | Type   | Default | Description                                                                                                                                                                          |
| --------------- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **BASE_PATH**   | `str`  | `""`    | The base directory path to be used for the file serving, if not defined the current directory is used instead.                                                                       |
| **STYLE_URLS**  | `list` | `[]`    | The list of URLs that are going to be used to include stylesheets at directory listing.                                                                                              |
| **INDEX_FILES** | `list` | `[]`    | List of file names that should be considered for eligible for index operation (eg: `index.html`).                                                                                    |
| **PATH_REGEX**  | `list` | `[]`    | The list of regex to path values (separated by the `:` character) that provide a simple way of URL re-writing like behaviour under the file serving extension (eg: `.*:index.html`). |
| **LIST_DIRS**   | `bool` | `True`  | If directory listing is enabled (may pose a security issue).                                                                                                                         |
| **LIST_ENGINE** | `str`  | `base`  | The name of the HTML generation engine to be used while listing files (eg: base, apache, legacy, etc.).                                                                              |

#### HTTP

| Name           | Type   | Default | Description                                                                                                                                               |
| -------------- | ------ | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SAFE**       | `bool` | `False` | If safe execution should be enforced, (eg: avoiding HTTP2 execution).                                                                                     |
| **COMMON_LOG** | `str`  | `None`  | The path to the file to log the HTTP request in "Common Log Format".                                                                                      |
| **ENCODING**   | `str`  | `plain` | The encoding to be applied to the responses, one of `plain`, `chunked`, `gzip`, `deflate` or `auto`, check the `Compression` section for the `auto` mode. |

#### Limits

| Name               | Type  | Default | Description                                                                                                                             |
| ------------------ | ----- | ------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **LINE_LIMIT**     | `int` | `8192`  | The maximum size (in bytes) of the initial line of a request, a larger one is rejected with a `414` status code.                        |
| **HEADERS_LIMIT**  | `int` | `65536` | The maximum size (in bytes) of the headers section of a request, a larger one is rejected with a `431` status code.                     |
| **HEADERS_COUNT**  | `int` | `128`   | The maximum number of header lines of a request, a larger number is rejected with a `431` status code.                                  |
| **REQUESTS_LIMIT** | `int` | `1000`  | The maximum number of requests served by a single connection before it stops being a persistent one, set it to `0` to remove the bound. |

#### Compression

| Name                   | Type   | Default               | Description                                                                                                                                                               |
| ---------------------- | ------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **COMPRESS_MIN**       | `int`  | `1024`                | The minimum size (in bytes) of a payload for the compression of it to be considered, smaller payloads would grow in size once the framing overhead is taken into account. |
| **COMPRESS_MAX**       | `int`  | `5242880`             | The maximum size (in bytes) of a payload for the compression of it to be considered, keeps the cost of the (synchronous) compression bounded.                             |
| **COMPRESSED_LIMIT**   | `int`  | `5242880`             | Alias of `COMPRESS_MAX`, kept for backwards compatibility.                                                                                                                |
| **COMPRESS_TYPES**     | `list` | built-in allowlist    | The media types considered to be compressible, a value ending with a slash is matched as a prefix (eg: `text/`) and one starting with a plus as a suffix (eg: `+json`).   |
| **COMPRESS_ENCODINGS** | `list` | `["gzip", "deflate"]` | The content codings to be used in the compression, defined in descending order of preference (the first one also accepted by the client is the one used).                 |
| **COMPRESS_LEVEL**     | `int`  | `6`                   | The zlib compression level to be used, provides a balance between the compression ratio and the processor usage.                                                          |
| **COMPRESS_FLUSH**     | `int`  | `16384`               | The amount of payload accumulated in the compressor before a partial flush, set it to `0` to flush every chunk (see the note below on latency sensitive streams).         |
| **COMPRESS_VARY**      | `bool` | `True`                | If the `Vary: Accept-Encoding` header should be announced for the responses that were eligible for compression, required for correct behaviour behind a shared cache.     |

Accumulating the payload before each flush improves the compression ratio of a chunked response considerably, but it also means that a response is only delivered in blocks of roughly `COMPRESS_FLUSH` bytes. That is a bad trade for a latency sensitive stream (server sent events, long polling, progress output), so `text/event-stream` is never compressed and any deployment that serves such a stream under an explicit `ENCODING=gzip` or `ENCODING=deflate` should set `COMPRESS_FLUSH` to `0`.

#### Proxy

| Name                        | Type    | Default | Description                                                                                                                                                                                                                |
| --------------------------- | ------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DYNAMIC**                 | `bool`  | `True`  | In case this value is active dynamic connection encoding is applied, meaning that extra heuristics will be applied on a response basis to determine the proper encoding of the response (eg: plain, chunked, gzip, etc.).  |
| **THROTTLE**                | `bool`  | `True`  | If throttling of the connection stream should be applied on both ways to avoid starvation of the producer consumer relation.                                                                                               |
| **TRUST_ORIGIN**            | `bool`  | `False` | If the origin connection (eg: http client, proxy client, etc.) is meant to be trusted meaning that its information is considered reliable, this value is especially important for proxy to proxy relations.                |
| **COMPRESS_FORWARD_ACCEPT** | `bool`  | `False` | If the `Accept-Encoding` of the client should be forwarded to the back-end instead of asking it for the `identity` coding, use it when the back-end does better than the proxy.                                            |
| **COMPRESS_BUFFER**         | `bool`  | `True`  | If the encoding decision should be deferred for the back-ends that stream a payload with no declared length, holding the response until the minimum size is crossed, when disabled such responses are forwarded untouched. |
| **COMPRESS_TIMEOUT**        | `float` | `1.0`   | The maximum amount of time (in seconds) that a response may be held while waiting for enough payload to decide on the compression.                                                                                         |

##### Compression at the proxy (`ENCODING=auto`)

The `auto` encoding makes the proxy the compression authority for the edge, negotiating the coding of every response with the client instead of applying a server wide one. The interaction with `DYNAMIC` is the following:

| `ENCODING`          | `DYNAMIC`     | Behaviour                                                                          |
| ------------------- | ------------- | ---------------------------------------------------------------------------------- |
| `plain` / `chunked` | `1` (default) | Pass-through, the payload of the back-end is forwarded byte-identical.             |
| `gzip` / `deflate`  | `0`           | The payload of the back-end is decoded and re-encoded unconditionally.             |
| `auto`              | ignored       | Negotiated, size and content type aware compression, resolved on a response basis. |

Under `auto` only the payloads that arrive from the back-end under the `identity` coding are compressed, so an already encoded response is always forwarded byte-identical and never decoded. A response is compressed only when the client accepts one of the configured codings, the status code carries a payload, no `Cache-Control: no-transform` or `Content-Range` is present, the media type is in `COMPRESS_TYPES` and the size is between `COMPRESS_MIN` and `COMPRESS_MAX` (when the back-end declares it). The `CONNECT` and WebSocket tunnels bypass the encoding layer and are therefore never affected. Note that a client rejecting the identity coding with `identity;q=0` still receives an uncompressed response whenever none of the configured codings is acceptable to it, as no `406` is produced.

Two notes worth keeping in mind when enabling it:

- Compressing a response that mixes a secret with attacker influenced content is the pre-condition of the BREACH attack, and a proxy applies it across every back-end at once. `COMPRESS_TYPES` and the support for `Cache-Control: no-transform` are the levers available to exclude the affected responses.
- Compression runs synchronously in the event loop thread, which at a proxy is shared by every back-end. `COMPRESS_MAX` together with the identity only rule (no decoding leg) is what keeps that cost bounded. Note that a back-end that streams without declaring a length cannot be measured upfront, so `COMPRESS_MAX` does not apply to it, set `COMPRESS_BUFFER` to `0` to leave those responses untouched.

#### Proxy Reverse

| Name                  | Type    | Default | Description                                                                                                                                                 |
| --------------------- | ------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **STS**               | `int`   | `0`     | Defines the strict transport security header value (in seconds) for the reverse proxy, in case the value is zero the strict transport security is disabled. |
| **ECHO**              | `bool`  | `False` | If enabled allows for more verbose output of the rules associated with the reverse proxy.                                                                   |
| **RESOLVE**           | `bool`  | `True`  | If the DNS based resolution of the hosts should be enabled meaning that from time to time the hostname associated with the target URLs is resolved.         |
| **RESOLVE_TIMEOUT**   | `float` | `120.0` | The amount of seconds between DNS resolution queries.                                                                                                       |
| **HOST_FORWARD**      | `bool`  | `False` | If the `Host` header for HTTP back-end connections should be resolved from rules, avoiding `Host` header populated with the IP address.                     |
| **REUSE**             | `bool`  | `True`  | If HTTP connections/rules should be re-used from a proxy point of view, this options may pose a problem when different suffixes are used for the same host. |
| **STRATEGY**          | `str`   | `robin` | The load balancing strategy that is going to be used for multiple back-end connections.                                                                     |
| **X_FORWARDED_PORT**  | `str`   | `None`  | If defined allow "forcing" the `X-Forwarded-Port` HTTP header.                                                                                              |
| **X_FORWARDED_PROTO** | `str`   | `None`  | If defined allow "forcing" the `X-Forwarded-Proto` HTTP header.                                                                                             |

#### Consul Proxy

| Name                     | Type    | Default                 | Description                                                                                                                                                               |
| ------------------------ | ------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CONSUL_URL**           | `str`   | `http://localhost:8500` | The base URL of the Consul HTTP API used for service discovery.                                                                                                           |
| **CONSUL_TOKEN**         | `str`   | `None`                  | The ACL token to be sent in the `X-Consul-Token` header for authenticated Consul API requests.                                                                            |
| **CONSUL_TAG**           | `str`   | `proxy.enable=true`     | The tag that a Consul service must have to be eligible for reverse proxying, only services containing this exact tag in their tag list are registered.                    |
| **CONSUL_POLL_INTERVAL** | `float` | `30.0`                  | The interval in seconds between Consul API polling cycles for service discovery, set to `0` to disable periodic polling and only discover services at startup.            |
| **CONSUL_SKIP_HEALTH**   | `bool`  | `True`                  | If `True` the `?passing=true` filter is omitted from Consul health queries so services in any health state are included; set to `False` to only include passing services. |
| **HOST_SUFFIXES**        | `list`  | `[]`                    | List of domain suffixes to register as aliases for each discovered service (eg: `example.com` would register `myapp.example.com` as an alias for the `myapp` service).    |

Services may also use the following Consul tags to control routing behavior:

| Tag                            | Description                                                                                                                                                     |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **proxy.name=\<name\>**        | Overrides the subdomain name used for host-based routing instead of the service/job name (eg: `proxy.name=webapp` routes `webapp` instead of the service name). |
| **proxy.domain=\<domain\>**    | Alias for `proxy.name` with lower priority, overrides the domain name used for routing.                                                                         |
| **proxy.password=\<secret\>**  | Sets password protection for the service using simple authentication, requires a valid password to access the proxied service.                                  |
| **proxy.error-url=\<url\>**    | Configures a custom error page URL to redirect users when the proxied service returns an error response.                                                        |
| **proxy.address=\<address\>**  | Overrides the instance address used when building backend URLs, bypassing the default Consul service/node address resolution.                                   |
| **proxy.protocol=\<scheme\>**  | Selects the upstream scheme used when building backend URLs, accepts `http` or `https`, defaults to `http` when unset or invalid.                               |
| **proxy.port=\<ports\>**       | Comma-separated list of allowed ports or port ranges for the service (eg: `proxy.port=8080,9090` or `proxy.port=8080-8085,9090`).                               |
| **proxy.ports=\<ports\>**      | Alias for `proxy.port` with the same behavior including port range support, first match wins when both are present.                                             |
| **proxy.alias=\<domains\>**    | Comma-separated list of domain aliases that should route to the same backend service (eg: `proxy.alias=api,api-v2` registers both as aliases for the service).  |
| **proxy.auth-regex=\<rules\>** | Comma-separated regex auth rules as `<pattern>;<type>` with types `none`, `password`, `simple:<user>:<pass>`, `address:<ip+cidr>`, `\|` for OR.                 |
| **proxy.redirect-ssl=true**    | Enables automatic HTTP to HTTPS redirection for the service, all HTTP requests are redirected to the equivalent HTTPS URL.                                      |

#### DNS Client

| Name                | Type   | Default | Description                                                                |
| ------------------- | ------ | ------- | -------------------------------------------------------------------------- |
| **NAMESERVERS**     | `list` | `[]`    | The sequence of DNS servers to be used for forward of resolution requests. |
| **NAMESERVERS_IP4** | `list` | `[]`    | Same as `NAMESERVERS` but just for IPv4 resolution.                        |
| **NAMESERVERS_IP6** | `list` | `[]`    | Same as `NAMESERVERS` but just for IPv6 resolution.                        |

#### SMTP Relay

| Name                        | Type   | Default  | Description                                                                                                                                                                         |
| --------------------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SMTP_HOST**               | `str`  | auto     | The hostname used for SMTP EHLO identification and Message-ID generation.                                                                                                           |
| **SMTP_ADAPTER**            | `str`  | `memory` | The storage adapter used for local message delivery (eg: `memory`, `fs`, `mongo`).                                                                                                  |
| **SMTP_AUTH**               | `str`  | `dummy`  | The authentication handler used for SMTP relay authorization (eg: `dummy`, `memory`).                                                                                               |
| **POSTMASTER**              | `str`  | `None`   | The email address used as sender for Delivery Status Notification (DSN) error emails sent on relay failure.                                                                         |
| **DKIM**                    | `dict` | `{}`     | Dictionary mapping domains to DKIM signing configuration with `key`/`key_b64`, `selector` and `domain` fields.                                                                      |
| **SMTP_CAPTURE_TRANSCRIPT** | `bool` | `False`  | If enabled, captures the full SMTP command/response conversation (excluding DATA payload) for each relay session, stored as a `transcript` list in the session deliverability data. |

#### SMTP Activity Tracking

| Name                     | Type  | Default | Description                                                                                                                                 |
| ------------------------ | ----- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **SMTP_ACTIVITY_URL**    | `str` | `None`  | The webhook URL to POST delivery activity events to (eg: `http://localhost:8080/api/activity`). Activity tracking is disabled when not set. |
| **SMTP_ACTIVITY_SECRET** | `str` | `None`  | The shared secret sent as `X-Activity-Secret` header on each webhook POST for authentication.                                               |

#### Blacklist Middleware

| Name          | Type   | Default | Description                                                                                                         |
| ------------- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------- |
| **BLACKLIST** | `list` | `[]`    | List of IP addresses of the connections that should be dropped immediately, use `*` to drop all of the connections. |
| **WHITELIST** | `list` | `[]`    | Sequence of IP addresses that should be allowed explicitly, use `*` to allow all of the connection to be accepted.  |

#### Flood (Mitigation) Middleware

| Name              | Type   | Default | Description                                                                                                                       |
| ----------------- | ------ | ------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **CONNS_PER_MIN** | `int`  | `600`   | The maximum number of connections per minute allowed per a certain IP before it becomes black listed and connections are dropped. |
| **WHITELIST**     | `list` | `[]`    | Sequence of IP addresses that should be allowed explicitly, use `*` to allow all of the connection to be accepted.                |

#### PROXY Middleware

| Name              | Type  | Default | Description                                                 |
| ----------------- | ----- | ------- | ----------------------------------------------------------- |
| **PROXY_VERSION** | `int` | `1`     | The version of the PROXY protocol that is going to be used. |

#### Annoyer Middleware

| Name               | Type    | Default | Description                                                                                                                       |
| ------------------ | ------- | ------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **ANNOYER_PERIOD** | `float` | `10.0`  | The period (in seconds) to wait in between the printing of the "annoying" diagnostics message, this is opposite of the frequency. |
