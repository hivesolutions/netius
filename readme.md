# [![Netius](res/logo.png)](http://netius.hive.pt)

**Fast and readable async non-blocking network apps**

Netius is a Python network library that can be used for the rapid creation of asynchronous non-blocking
servers and clients. It has no dependencies, it's cross-platform, and brings some sample netius-powered
servers out of the box, namely a production-ready WSGI server.

Simplicity and performance are the main drivers of this project. The codebase adheres to very strict
code standards, and is extensively commented; and as far as performance is concerned, it aims to
be up to par with equivalent native implementations, where [PyPy](http://pypy.org) can be used to
provide the extra boost to raise performance up to these standards.

Bear in mind that although netius is non-blocking, it will naturally still block if the operations
performed within the event loop are blocking, like reading or writing a file, which are both blocking
operations in the Python standard library. Running multiple netius instances in parallel, and having
a fast server like [nginx](http://nginx.org) act as their reverse proxy, is one way of minimising the
perceptibility of such blockages.

## Installation

```bash
pip install netius
```

Or download the source from [GitHub](https://github.com/hivesolutions/netius).

Netius has no dependencies, and is therefore cross-platform. It's compatible with [PyPy](http://pypy.org),
with which it benefits of performance increases up to 1.5x - 2.5x faster in most environments, when
compared with running it with the cPython interpreter.

## Usage

### WSGI Server

```python
import netius.servers

def app(environ, start_response):
    status = "200 OK"
    contents = "Hello World"
    content_l = len(contents)
    headers = (
        ("Content-Length", content_l),
        ("Content-type", "text/plain"),
        ("Connection", "keep-alive")
    )
    start_response(status, headers)
    yield contents

server = netius.servers.WSGIServer(app = app)
server.serve(port = 8080)
```

### HTTP Client

#### Synchronous usage

```python
import netius.clients
result = netius.clients.HTTPClient.get_s(
    "http://www.flickr.com/",
    async = False
)
print result["data"]
```
#### Asynchronous usage

```python
import netius.clients

def on_partial(client, parser, data):
    print data

def on_message(client, parser, message):
    netius.clients.HTTPClient.cleanup_s()

netius.clients.HTTPClient.get_s(
    "http://www.flickr.com/",
    callback = on_message,
    on_data = on_partial
)
```

### Test servers

The servers that come with netius out-of-the-box, can be tested through the command line:

* WSGIServer - `python -m netius.servers.wsgi`
* FTPServer - `python -m netius.servers.ftp`
* HelloServer - `MESSAGE="Hello Netius" python -m netius.extra.hello`
* FileServer - `BASE_PATH=/ python -m netius.extra.file`
* SMTPServer - `python -m netius.servers.smtp`
* RelaySMTPServer - `python -m netius.extra.smtp_r`

### Advanced topics

More information can be found in the [Advanced Topics](doc/advanced.md) page.

## License

Netius is currently licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/).

## Build Automation

[![Build Status](https://travis-ci.org/hivesolutions/netius.png?branch=master)](https://travis-ci.org/hivesolutions/netius)
[![Coverage Status](https://coveralls.io/repos/hivesolutions/netius/badge.png?branch=master)](https://coveralls.io/r/hivesolutions/netius?branch=master)
[![PyPi Status](https://pypip.in/v/netius/badge.png)](https://pypi.python.org/pypi/netius)
