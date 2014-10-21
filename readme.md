# [![Netius](res/logo.png)](http://netius.hive.pt)

**Readable, simple and fast asynchronous non-blocking network apps**

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
* HelloServer - `MESSAGE="Hello Netius" python -m netius.extra.hello`
* FileServer - `BASE_PATH=/ python -m netius.extra.file`
* SMTPServer - `python -m netius.servers.smtp`
* RelaySMTPServer - `python -m netius.extra.smtp_r`

### Other examples

More examples can be found in the [examples.md](examples.md) page.

## Benchmarks

Running `ab -n 20000 -c 5 -k http://localhost:8080/` should achieve the following results:

* `HelloServer` - 9.6 K req/sec
* `WSGIServer` - 8.7 K req/sec

These values have been verified for commit #7c2687b running in Python 2.6.6.

## Advanced topics

### Cryptography

Netius has some built-in cryptography utilities. The following are some 
examples of RSA key operations that can be tested through the command line:

```bash
python -m netius.sh.rsa read_private private.key
python -m netius.sh.rsa read_public public.pub
python -m netius.sh.rsa private_to_public private.key public.pub
```

DKIM is an infra-structure for signing SMTP based messages which provides a way to avoid unwanted
SPAM tagging. Netius provides a series of utilities for DKIM processing, here are some examples:

```bash
python -m netius.sh.dkim generate hive.pt
python -m netius.sh.dkim sign hello.mail dkim.key 20140327175143 hive.pt
```

To generate a password protected by a cryptographic hash to be used with the netius 
authentication/authorization infra-structure use:

```bash
python -m netius.sh.auth generate your_password
```

### IPv6

Netius is compatible with IPv6. To activate this mode set the `IPV6` configuration variable
to a valid value (eg: 1 or True), and an IPv6 socket will be used instead.

```python
IPV6=1 MESSAGE="Hello Netius" python -m netius.extra.hello
```

### Debugging

It's important to keep track of the memory leaks that may be created by any circular references or
unclosed resources associated with a netius server. For that purpose, a [special document](leak.md) has 
been created, documenting the various tools and strategies that may be used to detect such leaks.

### Testing

#### Edge triggered polling

Edge based polling is a bit tricky as it may easily end up in a data deadlock. The best way to test this 
kind of problem is to change the `POLL_TIMEOUT` value to a negative value so that the loop blocks for data:

```bash
LEVEL=DEBUG POLL_TIMEOUT=-1 BASE_PATH=/ python -m netius.extra.file
```

Then try to extract a really large file from this server (eg: 1.0 GB) and see if it is able to serve it
without any problems.

## Build Automation

[![Build Status](https://travis-ci.org/hivesolutions/netius.png?branch=master)](https://travis-ci.org/hivesolutions/netius)
