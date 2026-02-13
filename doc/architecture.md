# Architecture

Netius is a networking library with its own event loop, a Protocol/Transport layer that is
API-compatible with Python's asyncio, and a Container system for multiplexing multiple services
on a shared poll.

## Event Loop

The event loop lives in `Base` (`netius.base.common`) and is built on OS-level I/O multiplexing:
epoll (Linux), kqueue (macOS/BSD), poll (POSIX), or select (fallback).

The core cycle in `Base.loop()`:

```text
while running:
    ticks()              # timers, delayed callbacks, housekeeping
    reads, writes, errors = poll.poll()
    reads(sockets)       # dispatch readable sockets
    writes(sockets)      # dispatch writable sockets
    errors(sockets)      # dispatch error sockets
```

Each socket is registered via `sub_read(socket, owner=self)` -- the `owner` is the `Base` that
created the connection. This ownership is used by the Container for routing (see below).

### Read Path

```text
poll -> on_read(socket) -> connection.recv()
  -> on_data_base(connection, data) -> connection.set_data(data)
    -> connection triggers "data" event
```

`Connection` is the Netius-native socket abstraction handling buffering, SSL, and flow control.

## Protocol / Transport

Netius protocols implement the same interface as `asyncio.Protocol`, so they run on either event
loop unchanged.

```text
Protocol                  connection_made(), connection_lost(), pause/resume_writing
  +-- StreamProtocol      data_received(), send()
  +-- DatagramProtocol    datagram_received(), send_to()
```

`StreamProtocol` also exposes backward-compat delegation properties (`socket`, `renable`,
`is_throttleable()`) that reach through to the underlying `Connection`.

The `Transport` classes (`netius.base.transport`) wrap a `Connection` and bridge the two worlds:

- Binds to `Connection` `"data"` / `"close"` events
- Forwards to `protocol.data_received()` / `protocol.connection_lost()`
- `transport.write(data)` calls `connection.send(data, delay=False)`

Wiring is set up by `transport._set_compat(protocol)` which binds events and calls
`protocol.connection_made(transport)`.

## Agent

`Agent` (`netius.base.agent`) is the entry point for protocol-based implementations.

```text
Agent                Base-compatible stubs (load, unload, ticks, on_start, on_stop)
  +-- ClientAgent    connect(), event relay, thread-local caching, _container_loop
  +-- ServerAgent
```

`ClientAgent.connect()` creates a protocol, calls `connect_stream(loop=self._container_loop)`,
and relays protocol events (`"open"` -> `"connect"`, `"close"` -> `"close"`) so observers on the
client receive events from all managed protocols.

Agent provides Base-compatible stubs so it can participate in a Container without defensive guards.

## Container

The `Container` (`netius.base.container`) multiplexes multiple `Base` and `Agent` instances on a
shared poll. Used by composite servers like `ProxyServer` (front-end server + back-end clients).

```python
def loop(self):
    while self._running:
        self.ticks()
        result = self.poll.poll_owner()  # events grouped by owning Base
        for base, (reads, writes, errors) in result.items():
            base.reads(reads)
            base.writes(writes)
            base.errors(errors)
```

### Socket Ownership

`Base.sub_read(socket)` registers `owner=self` in the poll. `poll_owner()` groups ready sockets
by owner and returns a dict, so the Container routes each group to the correct Base.

### _container_loop

Agent-based objects need `_container_loop` (set to `Container.owner` by `apply_base()`) so that
`connect_stream()` calls `owner.connect()` instead of `Container.connect()`. This ensures:

1. Connections are owned by the right Base (eg ProxyServer)
2. `poll_owner()` routes their events to that Base's `on_read()` -> `on_data_base()`
3. Data reaches the transport -> protocol layer

Without it, `connect_stream(loop=None)` falls back to `common.get_loop()` which returns the
Container (as `Base._MAIN`). Connections owned by the Container would not be routed through the
correct `on_data_base()` bridging path.
