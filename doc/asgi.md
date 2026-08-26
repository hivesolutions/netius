# ASGI

Netius ships an ASGI compliant server, so that applications written for frameworks like [Starlette](https://www.starlette.io), [FastAPI](https://fastapi.tiangolo.com), Quart or Litestar may be served by it, the same way that the [WSGI server](../README.md) serves the synchronous ones.

The server is built on top of the HTTP/2 server, so it inherits both the HTTP/1.1 and the HTTP/2 handling, the connection management and the compression decisions from it.

## Usage

```python
import netius.servers

async def app(scope, receive, send):
    await send(
        dict(
            type="http.response.start",
            status=200,
            headers=[(b"content-length", b"11"), (b"content-type", b"text/plain")],
        )
    )
    await send(dict(type="http.response.body", body=b"Hello World"))

server = netius.servers.ASGIServer(app=app)
server.serve(port=8080)
```

The server may also be started from the command line, with the application to be served defined through the `APP` environment variable using the module and attribute notation:

```bash
APP=my_module:app python -m netius.servers.asgi
```

With no application defined a simple hello world one is served instead, which is useful to verify that the infra-structure is properly installed.

## Scopes

The three scope types of the specification are supported:

| Scope       | Support                                                              |
| ----------- | -------------------------------------------------------------------- |
| `http`      | Requests and responses, including streaming ones (`more_body`)        |
| `websocket` | Handshake, text and binary messages, fragmentation, ping/pong, close  |
| `lifespan`  | Startup and shutdown events, around the serving cycle                 |

Both the current (single callable) 3.0 interface and the legacy (double callable) 2.0 one are accepted, the shape of the application is detected when the server is created.

## Modes of execution

The application coroutines may be driven by two different event loops, the mode is selected either by the `asyncio` parameter of the constructor or by the `ASYNCIO` environment variable.

### Native (default)

The coroutines are driven by the Netius event loop itself, using the coroutine and future primitives of the framework. This is the fastest mode and requires no asyncio at all.

Applications that use asyncio primitives which depend on a running asyncio task are **not** supported under this mode. In practice this means that everything built on top of [anyio](https://anyio.readthedocs.io) task groups fails, notably the streaming responses, the background tasks and the synchronous (`def`) endpoints of Starlette and FastAPI. Plain requests and responses, `asyncio.sleep` and the timers do work, as Netius registers its compatibility loop as the asyncio running one.

### Asyncio

```bash
ASYNCIO=1 APP=my_module:app python -m netius.servers.asgi
```

The applications are run as "real" asyncio tasks, on an asyncio event loop owned by the server that is driven from the Netius one, so that the complete set of the asyncio primitives becomes available. This is the mode to use with Starlette, FastAPI and anything else built on top of anyio.

The loop of the applications is advanced on every tick of the Netius loop and also immediately after a request is received, so that no extra latency is added to the handling of it. The timers of the applications have the same resolution as the ones of Netius, meaning that they are bound by the poll timeout of the event loop.

## Performance

Measured on a single core, with keep-alive enabled, serving an 11 byte plain text response (`ab -n 20000 -c 50 -k`, median of 5 runs, Python 3.14, macOS):

| Server                                 | Requests per second | 95% latency |
| -------------------------------------- | ------------------- | ----------- |
| Netius WSGI                            | 21208               | 3 ms        |
| Netius ASGI (native)                   | 15904               | 4 ms        |
| uvicorn                                | 14537               | 4 ms        |
| Netius ASGI (asyncio)                  | 10755               | 6 ms        |
| uvicorn with Starlette                 | 9249                | 6 ms        |
| Netius ASGI (asyncio) with Starlette   | 4977                | 12 ms       |

The synchronous WSGI interface remains the fastest one, as an ASGI request pays for the driving of a coroutine. For a raw ASGI application the native mode is faster than uvicorn, while the asyncio mode trades throughput for the compatibility with the asyncio ecosystem.

## Back pressure

An application that produces the payload of a response faster than the client is able to read it would otherwise accumulate the complete response in the buffer of the connection. To avoid it the sending of a partial payload (`more_body`) or of a WebSocket frame suspends the application whenever the connection is exhausted, meaning that either the payload pending in it has reached `MAX_PENDING` bytes or that the flow control window of the HTTP/2 stream has been closed. The application is resumed once the payload reaches the connection, so the memory used by a response is bounded by the limit and not by its size.

The limit may be changed with the `max_pending` parameter of the constructor or with the `MAX_PENDING` environment variable, note that the suspension only happens once the limit is reached, so a response that fits in the buffer is never delayed by it (streaming a 20 KB response in chunks of 1 KB runs at the same rate with and without the mechanism).

## Lifespan

The startup event is sent before the event loop starts accepting connections and the shutdown one while the server is stopping, in both cases the server waits for the acknowledgment of the application, bound by `LIFESPAN_TIMEOUT`. An application that reports `lifespan.startup.failed` aborts the serving, as required by the specification, so that the requests are never handled by a partially initialized application. An application that raises when handed a lifespan scope is instead taken as one that does not support the protocol, so the server proceeds without it. The support may also be disabled explicitly with `lifespan=False` or with the `LIFESPAN` environment variable.

Note that the waiting is performed outside of the polling cycle, so an application whose startup depends on network operations of its own is not able to complete it before the timeout is reached.

## Limitations

- WebSocket connections are only accepted over HTTP/1.1, as the upgrade mechanism is not part of the HTTP/2 specification.
- The `http.disconnect` and `websocket.disconnect` events are delivered on a best effort basis, as the application is cancelled together with the connection that it's handling.
- Under Python 2.7, and any other interpreter without support for the async/await syntax, the server is a stub that raises an error when instantiated.

## Further reading

- [ASGI specification](https://asgi.readthedocs.io/en/latest/specs/main.html)
- [Architecture](architecture.md) for the event loop, protocol and transport layers
- [Compatibility with asyncio](compat.md) for the execution modes of the event loop
