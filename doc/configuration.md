# Configuration

#### General

* `HOST` (`str`) - The listening address of the server (eg: `127.0.0.1` or `0.0.0.0`)
* `PORT` (`int`) - The port the server will listen at (eg: `8080`)
* `SSL` (`bool`) - If the server is going to use SSL/TLS (Secure Sockets Layer)
* `IPV6` (`bool`) - If IPv6 should be enabled for the server/client, by default the created socket is either IPV4
or IPv6 only, note that under Linux dual stack is provided for "free" for IPv6 stacks (defaults to `False`)
* `ALLOWED` (`list`) - Sequence of IP or Subnet addresses (eg: 172.16.0.0/16) that are considered to be allowed as clients
for a given server, any client connection with an IP address not contained in the list will be dropped (defaults to `[]`)
* `TRUST_ORIGIN` (`bool`) - If the origin connection (eg: http client, proxy client, etc.) is meant to be trusted meaning that
its information is considered reliable, this value is especially important for proxy to proxy relations (defaults to `False`)
* `CHILDREN` (`int`) - Number of child processes that are meant to be created upon launch using a pre-fork approach. (defaults to `0`)
* `CHILD` (`int`) - Same as `CHILDREN`

#### Internal

* `POLL` (`str`) - The name of the polling system to be used for the controlling of the main event loop
by default this values is infered automatically based on the current system capabilities
* `DIAG` (`bool`) - If the diagnostics system should be launched for the current system, if launched the
system will be running as an HTTP server on localhost under port 5050
* `POLL_TIMEOUT` (`float`) - The timeout in seconds for each of the iteration of the event loop, this value
should be carefully chosed as it controls the minimum resolution of a delayed execution

#### SSL

* `CER_FILE` (`str`) - The path to the certificate file to be used for SSL (PEM format)
* `KEY_FILE` (`str`) - The path to the private key file to be used for SSL (PEM format)
* `CA_FILE` (`str`) - The path to the CA (certificate authority) file to be used for SSL (PEM format)
* `CA_ROOT` (`bool`) - If the default CA file/files should be loaded from the current environment (defaults to `True`)
* `SSL_VERIFY` (`bool`) - If the standard SSL verification process (CA) should be performed for the connection,
if the current instance is a client the host verification will also be performed for the server side host
* `SSL_HOST` (`str`) - The hostname that is going to be used in for domain verification, this value is only
user in server to be able to verify client certificates  against an expected host
* `SSL_SECURE` (`bool`) - If a secure suit of SSL should be provided (some protocol removed) (defaults to `True`)
* `SSL_CONTEXTS` (`dict`) - The dictionary that associates the various domains that may be served with different
context values (certificate, key, etc) for such domain
* `CER_DATA` (`str`) - Equivalent to `CER_FILE` but with explicit (data) contents of the file (`\n` escaped)
* `KEY_DATA` (`str`) - Equivalent to `KEY_FILE` but with explicit (data) contents of the file (`\n` escaped)
* `CA_DATA` (`str`) - Equivalent to `CA_FILE` but with explicit (data) contents of the file (`\n` escaped)

#### Proxy Reverse

* `STS` (`int`) - Defines the strict transport security header value (in seconds) for the reverse proxy, in case
the value is zero the strict transport security is disabled (defaults to `0`)
