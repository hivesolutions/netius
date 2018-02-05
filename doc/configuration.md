# Configuration

#### General

* `HOST` (`str`) - The listening address of the server (eg: `127.0.0.1` or `0.0.0.0`)
* `PORT` (`int`) - The port the server will listen at (eg: `8080`)
* `IPV6` (`bool`) - If IPv6 should be enabled for the server/client, by default the created socket is either IPV4
or IPv6 only, note that under Linux dual stack is provided for "free" for IPv6 stacks (defaults to `False`)
* `SSL` (`bool`) - If the server is going to use SSL/TLS (Secure Sockets Layer)
* `UNIX_PATH` (`str`) - The path to the file that is going to be used for Unix domain sockets (defaults to `$PORT`),
note that under the hood the port variable is used as the path for the socket
* `BACKLOG` (`int`) - The number of connections to be hold waiting in queue while pending accept operation
* `ALLOWED` (`list`) - Sequence of IP or Subnet addresses (eg: 172.16.0.0/16) that are considered to be allowed as clients
for a given server, any client connection with an IP address not contained in the list will be dropped (defaults to `[]`)
* `TRUST_ORIGIN` (`bool`) - If the origin connection (eg: http client, proxy client, etc.) is meant to be trusted meaning that
its information is considered reliable, this value is especially important for proxy to proxy relations (defaults to `False`)
* `CHILDREN` (`int`) - Number of child processes that are meant to be created upon launch using a pre-fork approach. (defaults to `0`)
* `CHILD` (`int`) - Same as `CHILDREN`
* `MIDDLEWARE` (`list`) - The middleware as a set of strings (eg: proxy) that is going to be loaded into the instance, the notation
used to define the modules to be loaded should be underscore based (notice that loading extra middleware into an instance may impact the
performance of the same)

#### Internal

* `ASYNCIO` (`bool`) - If the asyncio mode should be used, meaning that the loop retrieval method to
be used is the one provided by the asyncio module, in case no asyncio support exists the flag is ignored
(defaults to `False`)
* `COMPAT` (`bool`) - If the "heavyweight" compatibility mode should be ensured so that some operations will
use an `asyncio` compatible way of performing execution, using this mode has performance implications
(defaults to `False`)
* `POLL` (`str`) - The name of the polling system to be used for the controlling of the main event loop
by default this values is infered automatically based on the current system capabilities
* `DIAG` (`bool`) - If the diagnostics system should be launched for the current system, if launched the
system will be running as an HTTP server on localhost under port 5050
* `POLL_TIMEOUT` (`float`) - The timeout in seconds for each of the iteration of the event loop, this value
should be carefully chosen as it controls the minimum resolution of a delayed execution
* `KEEPALIVE_TIMEOUT` (`int`) - The amount of time in seconds that a connection is set as idle until a
new refresh token is sent to it to make sure that it's still online and not disconnected, make sure that this
value is high enough that it does not consume to much bandwidth
* `KEEPALIVE_INTERVAL` (`int`) - The time between the retrying of "ping" packets, this value does not
need to be too large and should not be considered too important (may be calculated automatically)
* `KEEPALIVE_COUNT` (`int`) - The amount of times the "ping" packet is re-sent until the connection is
considered to be offline and is dropped

#### SSL

* `CER_FILE` (`str`) - The path to the certificate file to be used for SSL (PEM format)
* `KEY_FILE` (`str`) - The path to the private key file to be used for SSL (PEM format)
* `CA_FILE` (`str`) - The path to the CA (certificate authority) file to be used for SSL (PEM format)
* `CA_ROOT` (`bool`) - If the default CA file/files should be loaded from the current environment (defaults to `True`)
* `SSL_VERIFY` (`bool`) - If the standard SSL verification process (CA) should be performed for the connection,
if the current instance is a client the host verification will also be performed for the server side host
* `SSL_HOST` (`str`) - The hostname that is going to be used in for domain verification, this value is only
user in server to be able to verify client certificates  against an expected host
* `SSL_FINGERPRINT` (`str`) - The fingerprint (SHA1 digest of certificate) that is going to be used to verify the
integrity of a peer/client certificate against the expected one
* `SSL_DUMP` (`bool`) - If the certificate information should be dumped to the directory specified by the
`SSL_PATH` configuration value (defaults to `False`)
* `SSL_PATH` (`str`) - Path to the directory where the SSL dump information is going to be placed, in case
the directory does not exist it's created (defaults to `/tmp/ssl`)
* `SSL_SECURE` (`bool`) - If a secure suite of SSL should be ensured (some protocols removed) (defaults to `True`)
* `SSL_CONTEXTS` (`dict`) - The dictionary that associates the various domains that may be served with different
context values (certificate, key, etc) for such domain
* `CER_DATA` (`str`) - Equivalent to `CER_FILE` but with explicit (data) contents of the file (`\n` escaped)
* `KEY_DATA` (`str`) - Equivalent to `KEY_FILE` but with explicit (data) contents of the file (`\n` escaped)
* `CA_DATA` (`str`) - Equivalent to `CA_FILE` but with explicit (data) contents of the file (`\n` escaped)

#### File Serving

* `BASE_PATH` (`str`) - The base directory path to be used for the file serving, if not defined the current directory
is used instead (defaults to `None`)
* `INDEX_FILES` (`list`) - List of file names that should be considered for eligible for index operation (eg: `index.html`)
* `LIST_DIRS` (`bool`) - If directory listing is enabled (may pose a security issue) (defaults to `True`)
* `LIST_ENGINE` (`str`) - The name of the HTML generation engine to be used while listing files (eg: base, apache, legacy, etc.) (defaults to `base`)

#### HTTP

* `SAFE` (`bool`) - If safe execution should be enforced, (eg: avoiding HTTP2 execution) (defaults to `False`)
* `COMMON_LOG` (`str`) - The path to the file to log the HTTP request in "Common Log Format (defaults to `None`)

#### Proxy

* `DYNAMIC` (`bool`) - In case this value is active dynamic connection encoding is applied, meaning that extra
heuristics will be applied on a response basis to determine the proper encoding of the response (eg: plain, chunked, gzip, etc.)
* `THROTTLE` (`bool`) - If throttling of the connection stream should be applied on both ways to avoid starvation
of the producer consumer relation
* `STRATEGY` (`str`) - The load balancing strategy that is going to be used for multiple back-end connections (defaults to `smart`)
* `RESOLVE` (`bool`) - If the DNS based resolution of the hosts should be enabled meaning that from time to time the hostname
associated with the target URLs is resolved (defaults to `True`)
* `RESOLVE_TIMEOUT` (`float`) - The amount of seconds between DNS resolution queries (defaults to `120`)
* `REUSE` (`bool`) - If HTTP connections/rules should be re-used from a proxy point of view, this options may pose a problem when
different suffixes are used for the same host (defaults to `True`)

#### Proxy Reverse

* `STS` (`int`) - Defines the strict transport security header value (in seconds) for the reverse proxy, in case
the value is zero the strict transport security is disabled (defaults to `0`)
