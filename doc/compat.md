# Compatibility with asyncio

As part of the effort to make Netius more compatible with asyncio, the following
changes have been made:

- The `netius` module provides a `COMPAT` mode that allows it to be used to allows Netius protocols
to be used with asyncio. This mode is enabled by setting the `COMPAT` environment variable to `True`.

## Testing

To run the echo server Protocol implementation using netius run:

```bash
PYTHONPATH=. python3 netius/servers/echo.py 
```

To use the compat version meaning that an asyncio-like interface will be used underneath the hoods use:

```bash
COMPAT=1 PYTHONPATH=. python3 netius/servers/echo.py
```

To use the compat version and make use of the native asyncio event loop use the following:

```bash
COMPAT=1 ASYNCIO=1 PYTHONPATH=. python3 netius/servers/echo.py
```
