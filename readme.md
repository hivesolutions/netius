# [Netius Framework](http://netius.com)

Series of network related libraries for the rapid creation of non blocking async server and clients.
The aim of this project is to create a platform for creation of customized servers and clients for
specific and pre-defined purposes using simple inheritance techniques.

## Usage

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

## Examples

A series of example are located in the examples.md page.

## Running

In order to run the default servers of the netius infra-structure the out-of-box installation
is sufficient and many services are available for instance:

* WSGIServer - `python -m netius.servers.wsgi`
* HelloServer - `MESSAGE="Hello Netius" python -m netius.extra.hello`
* FileServer - `BASE_PATH=/ python -m netius.extra.file`
* SMTPServer - `python -m netius.servers.smtp`
* RelaySMTPServer - `python -m netius.extra.smtp_r`

## Cryptography

It's possible to read information from both private and public RSA based keys for that use the
following command from the bash:

```bash
python -m netius.sh.rsa read_private private.key
python -m netius.sh.rsa read_public public.pub
python -m netius.sh.rsa private_to_public private.key public.pub
```

DKIM is an infra-structure for signing SMTP based message and provides a way to avoid unwanted
SPAM tagging, netius provides a series of utilities for processing of DKIM, these are some
examples of DKIM bash usage:

```bash
python -m netius.sh.dkim generate hive.pt
python -m netius.sh.dkim sign hello.mail dkim.key 20140327175143 hive.pt
```

To be able to generate a password protected by a cryptographic hash and that is meant to be used
under the netius authentication/authorization infra-structure use:

```bash
python -m netius.sh.auth generate your_password
```

## Compatibility

Currently netius is compatible with pypy and a typical environment will benefit from a 1.5x to 2.5x
performance increase when compared with the cpython interpreter.

## Debugging

It's important to keep track of the memory leaks that may be created by any circular references or
unclosed resources associated with a netius server. For that a [special document](leak.md) has been created
documenting the various tools and strategies that may be used.

## Testing

### Edge triggered polling

Edge based polling is a bit tricky as it may easly end up in a dead lock of data.
The best way to testing this kind of problem is to change the `POLL_TIMEOUT` value to a negative
value so that the loop blocks for data.

```bash
LEVEL=DEBUG POLL_TIMEOUT=-1 BASE_PATH=/ python -m netius.extra.file
```

The try to extract a really large file from this server (eg: 1.0 GB) and see if it is able to serve it
without any problems.

## Benchmarks

Running `ab -n 20000 -c 5 -k http://srio.hive:8080/` whoud should get the following results:

* `HelloServer` - 9.6 K req/sec
* `WSGIServer` - 8.7 K req/sec

These values have been verified under commit #7c2687b under python 2.6.6.