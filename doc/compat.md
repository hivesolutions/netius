# Compatibility with asyncio

The `netius.base.compat` module allows Netius protocols to run on different event loops. Each
bootstrap function (`connect_stream`, `serve_stream`, `build_datagram`) dispatches to a **native**
or **compat** variant based on runtime configuration.

## Execution Modes

### Native (Default)

Uses the Netius event loop directly. Fastest path - pure callbacks, no asyncio overhead.

```bash
PYTHONPATH=. python3 netius/servers/echo.py
```

### Compat

Wraps the Netius event loop in `CompatLoop` to present an `asyncio.AbstractEventLoop` interface.
Allows third-party asyncio protocols to run on Netius event loop.

```bash
COMPAT=1 PYTHONPATH=. python3 netius/servers/echo.py
```

### Asyncio

Replaces the Netius event loop with Python's native asyncio loop. Netius protocols work because
they implement the standard asyncio Protocol interface. Implies compat mode.

```bash
COMPAT=1 ASYNCIO=1 PYTHONPATH=. python3 netius/servers/echo.py
```

## Dispatch

`is_compat()` returns `True` when `COMPAT=1` or `ASYNCIO=1` is set:

```python
def connect_stream(*args, **kwargs):
    if is_compat():
        return _connect_stream_compat(...)
    else:
        return _connect_stream_native(...)
```

The same pattern applies to `serve_stream()` and `build_datagram()`.

## Native Path

Calls `Base.connect()` / `Base.serve()` directly with callbacks:

```python
def _connect_stream_native(..., loop=None):
    loop = loop or common.get_loop()
    protocol = protocol_factory()
    loop.connect(host, port, ssl=ssl, callback=on_complete)
    # on_complete creates TransportStream, wires protocol
```

No futures, no coroutines, no translation layer. SSL parameters go straight to `Base.connect()`
which wraps the socket at the OS level.

## Compat Path

Routes through the asyncio API exposed by `CompatLoop`:

```python
def _connect_stream_compat(..., loop=None):
    loop = loop or common.get_loop()
    protocol = protocol_factory()
    connect = loop.create_connection(build_protocol, host=host, port=port, ssl=ssl)
    future = loop.create_task(connect)
    future.add_done_callback(on_connect)
```

`CompatLoop.create_connection()` internally calls `Base.connect()` but wraps the result in a
Future and wires the protocol inside a generator-based coroutine.

## CompatLoop

Wraps a Netius `Base` loop and translates asyncio API calls:

| asyncio API                  | Netius equivalent                          |
| ---------------------------- | ------------------------------------------ |
| `call_soon(cb)`              | `Base.delay(cb, immediately=True)`         |
| `call_later(delay, cb)`      | `Base.delay(cb, timeout=delay)`            |
| `create_future()`            | `Base.build_future()`                      |
| `create_task(coroutine)`     | `Base.ensure(coroutine)` wrapped in `Task` |
| `create_connection(...)`     | `Base.connect(...)` wrapped in a Future    |
| `create_server(...)`         | `Base.serve(...)` wrapped in a Future      |
| `run_until_complete(future)` | `Base.run_coroutine(future)`               |
| `run_forever()`              | `Base.run_forever()`                       |
| `stop()`                     | `Base.pause()`                             |

Attributes not explicitly implemented fall through to the underlying `Base` via `__getattr__`.

## Why Native is Faster

1. **No Future/Task overhead.** Native uses direct callbacks. Compat allocates a Future, creates a Task, and dispatches through done-callbacks for every operation.
2. **No translation layer.** Native calls `Base.connect()` directly. Compat routes every call through `CompatLoop` which translates asyncio API into Netius equivalents.
3. **No coroutine frames.** Compat's `_create_connection()` and `_create_server()` are generator coroutines (`yield future`). Native is purely callback-driven.
4. **Direct SSL.** Native passes SSL parameters to `Base.connect()` for OS-level wrapping. Compat constructs an `ssl.SSLContext` and routes through asyncio's SSL layer.

The difference accumulates under high connection rates where per-connection overhead matters.
