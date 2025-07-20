# Agents.md file

This document serves as the main reference for the agent's configuration, usage, and development notes. Please refer to the sections below for detailed instructions and guidelines.

## Overview

Netius is a Python network library for building asynchronous, non-blocking servers and clients. The concept of an **Agent** is central to Netius, providing a unified interface for both client and server protocol implementations.

## Agent Types

Netius provides three main agent base classes:

- **Agent**: The top-level base class for all agents, providing event handling and utility methods.
- **ClientAgent**: Inherits from `Agent`, used as the base for all client protocol implementations. Manages client instances per thread and provides static helpers for client lifecycle.
- **ServerAgent**: Inherits from `Agent`, used as the base for all server protocol implementations.

All agents inherit from `Observable`, allowing dynamic event binding and triggering.

## Built-in Server Agents

Netius comes with several built-in server agents, available in `src/netius/servers`:

- **WSGIServer**: Production-ready WSGI server.
- **FTPServer**: FTP protocol server.
- **HTTPServer**: HTTP/1.1 server.
- **HTTP2Server**: HTTP/2 server.
- **SMTPServer**: SMTP protocol server.
- **SOCKSServer**: SOCKS4/5 proxy server.
- **TFTPServer**: TFTP protocol server.
- **TorrentServer**: BitTorrent protocol server.
- **EchoServer**: Simple echo server for testing.
- **ProxyServer**: Generic proxy server.
- **POPServer**: POP3 protocol server.
- **MJPGServer**: MJPEG streaming server.
- **WSServer**: WebSocket server.
- **EchoWSServer**: WebSocket echo server.
- **DHCPServer**: DHCP protocol server.

Each server agent can be run as a standalone process or imported and used programmatically.

## Built-in Client Agents

Netius also provides several client agents in `src/netius/clients`:

- **HTTPClient**: HTTP/1.1 client with both synchronous and asynchronous APIs.
- **DNSClient**: DNS protocol client.
- **RawClient**: Raw TCP client for low-level communication.
- **SMTPClient**: SMTP protocol client.
- **SSDPClient**: SSDP protocol client.
- **TorrentClient**: BitTorrent protocol client.
- **WSClient**: WebSocket client.
- **APNClient**: Apple Push Notification client.
- **DHTClient**: Distributed Hash Table client.
- **MJPGClient**: MJPEG streaming client.

## Usage Examples

### Running a Server Agent

```python
import netius.servers

server = netius.servers.WSGIServer(app=my_wsgi_app)
server.serve(port=8080)
```

### Using a Client Agent

```python
import netius.clients

result = netius.clients.HTTPClient.get_s(
    "http://example.com/",
    asynchronous=False
)
print(result["data"])
```

## Event Handling

All agents support event binding via the `Observable` interface:

```python
agent = netius.servers.EchoServer()
agent.bind("data", lambda *args: print("Received data!"))
```

## Cleanup and Resource Management

- Always call the appropriate `cleanup` or `cleanup_s` method on agents to ensure resources are released, especially when using static client agents.
- For long-running servers, ensure proper signal handling and cleanup on shutdown.

## Contributing

- Follow the formatting guidelines above.
- Ensure all new agents inherit from the appropriate base class.
- Document new agents and their events in this file.

## Formatting

Always format the code before commiting using, making sure that the Python code is properly formatted using:

```bash
pip install black
black .
```

## Testing

Run the full test suite:

```bash
pip install -r requirements.txt
pip install -r extra.txt
pip install pytest
HTTPBIN=httpbin.bemisc.com pytest
```

## Style Guide

- Always update `CHANGELOG.md` according to semantic versioning, mentioning your changes in the unreleased section.
- Write commit messages using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
- Never bump the internal package version in `setup.py`. This is handled automatically by the release process.
- Python files use CRLF as the line ending.
- The implementation should be done in Python 2.7+ and compatible with Python 3.12.
- The style should respect the black formatting.
- The implementation should be done in a way that is compatible with the existing codebase.
- Prefer `item not in list` over `not item in list`
- Prefer `item == None` over `item is None`

## Further Reading

- [README.md](README.md) for general usage and installation.
- [doc/configuration.md](doc/configuration.md) for configuration options.
- [doc/advanced.md](doc/advanced.md) for advanced topics.

## License

Netius is licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/).
