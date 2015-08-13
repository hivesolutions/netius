# Advanced Topics

This page presents advanced information in a not so structured manner. It is used as both a reference
for external and internal developers, and therefore rewards flexibility over structure.

## Examples

Multiple netius examples can be found in the [Examples](examples.md) page.

## Python 3

The migration to Python 3 is not easy and as such a compatability layer was created under the name of
[legacy.py](../src/netius/base/legacy.py). This file should be the primary source of functionality related
with the compatability between Python 2 and Python 3 and all the code regarding the transition should
be store there and used from there.

### WSGI

WSGI specification is specialy problematic regarding the Python 3 unicode vs bytes problem and a common
specification for how to solve this is still pending, please refer to the links section for more information
regarding problems and solutions for Python 3 and WSGI.

### Links

* [Python3/WSGI](http://wsgi.readthedocs.org/en/latest/python3.html)
* [WSGI 2.0](http://wsgi.readthedocs.org/en/latest/proposals-2.0.html)

## Configuration

```json
"SSL_CONTEXTS" : {
    "localhost" : {
        "key_file" : "/secret.key",
        "cer_file" : "/secret.cer"
    }
}
```

## Benchmarks

Running `ab -n 20000 -c 5 -k http://localhost:8080/` should achieve the following results:

* `HelloServer` - 9.6 K req/sec
* `WSGIServer` - 8.7 K req/sec

These values have been verified for commit #7c2687b running in Python 2.6.6.

## Cryptography

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

## IPv6

Netius is compatible with IPv6. To activate this mode set the `IPV6` configuration variable
to a valid value (eg: 1 or True), and an IPv6 socket will be used instead.

```python
IPV6=1 MESSAGE="Hello Netius" python -m netius.extra.hello
```

## Debugging

It's important to keep track of the memory leaks that may be created by any circular references or
unclosed resources associated with a netius server. For that purpose, a [special document](leak.md) has
been created, documenting the various tools and strategies that may be used to detect such leaks.

## Testing

### Edge triggered polling

Edge based polling is a bit tricky as it may easily end up in a data deadlock. The best way to test this
kind of problem is to change the `POLL_TIMEOUT` value to a negative value so that the loop blocks for data:

```bash
LEVEL=DEBUG POLL_TIMEOUT=-1 BASE_PATH=/ python -m netius.extra.file
```

Then try to extract a really large file from this server (eg: 1.0 GB) and see if it is able to serve it
without any problems.
