# Diagnostics Server

Netius includes a built-in HTTP diagnostics server that exposes runtime introspection endpoints for
any running netius service. When enabled, it starts in a separate thread alongside the main event
loop, providing live access to system state, connection details, environment variables, and log
level management.

## Prerequisites

The diagnostics server is built on top of [Appier](https://github.com/hivesolutions/appier), a
lightweight Python web framework. To use the diagnostics server, install appier:

```bash
pip install appier
```

If appier is not installed the diagnostics server will fail gracefully and log a warning message,
the main service will continue running normally.

## Enabling

Set the `DIAG` environment variable to activate the diagnostics server:

```bash
DIAG=1 python -m netius.extra.hello
```

By default the server binds to `127.0.0.1:5050`. See the [Configuration](configuration.md#diagnostics)
page for the full set of configuration variables (`DIAG_HOST`, `DIAG_PORT`, `DIAG_SERVER`).

## Endpoints

The following endpoints are available on the diagnostics server.

### GET /info

Returns system information about the running netius instance including the number of active
connections, event loop state, poll type, and instance name.

The `full` query parameter controls the level of detail (defaults to `true`).

```bash
curl http://127.0.0.1:5050/info
curl http://127.0.0.1:5050/info?full=0
```

### GET /connections

Lists all active connections with their status, address, SSL state, and flow control details.

```bash
curl http://127.0.0.1:5050/connections
```

### GET /connections/\<id\>

Returns details for a specific connection identified by its ID.

```bash
curl http://127.0.0.1:5050/connections/abc123
```

### GET /logger

Returns the current logging level of the running instance.

```bash
curl http://127.0.0.1:5050/logger
```

### GET/POST /logger/set

Changes the logging level at runtime without restarting the service. Accepts a `level` query
parameter with standard Python logging level names.

```bash
curl "http://127.0.0.1:5050/logger/set?level=DEBUG"
curl "http://127.0.0.1:5050/logger/set?level=WARNING"
```

### GET /environ

Exposes the full set of environment variables of the running process.

```bash
curl http://127.0.0.1:5050/environ
```

## Security Considerations

The diagnostics server is designed for local debugging and should not be exposed to untrusted
networks. In particular:

* `/environ` exposes all environment variables, which may contain secrets, API keys, and credentials.
* `/logger/set` allows runtime modification of the logging level, which could be used to suppress
  audit logs or generate excessive output.

The default bind address `127.0.0.1` restricts access to the local machine. If you need to change
`DIAG_HOST` to a non-loopback address, ensure access is restricted through firewall rules or a
reverse proxy with authentication.

## Extending with Custom Routes

Subclasses of `Base` can override the `on_diag()` method to register additional routes on the
diagnostics application. The `diag_app` attribute holds the Appier application instance.

For example, the `ReverseProxyServer` adds a `/proxy_r` endpoint exposing its host mapping:

```python
def on_diag(self):
    self.diag_app.add_route("GET", "/proxy_r", self.proxy_r_dict)
```

The `"diag"` event is also triggered when the diagnostics app is created, allowing external
observers to add routes via event binding:

```python
server.bind("diag", lambda server: server.diag_app.add_route(
    "GET", "/custom", lambda: dict(status="ok")
))
```

## Architecture

The diagnostics server is loaded during service startup by `load_diag()` in the `Base` class. The
sequence is:

1. `Base.bind_env()` reads `DIAG` from the environment
2. `Base.load_diag()` checks if diagnostics are enabled and if appier is available
3. A `DiagApp` instance is created with a reference to the parent system (`self`)
4. `on_diag()` is called so subclasses can register custom routes
5. The app is started via `serve(threaded=True)`, running in its own thread

The `DiagApp` holds a reference to the parent netius system, which it uses to call introspection
methods like `info_dict()`, `connections_dict()`, and `level_logging()`.
