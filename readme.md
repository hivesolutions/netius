# [Netius Framework](http://netius.com)

Series of network related libraries for the rapid creation of non blocking async server and clients.

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

## Running

In order to run the default servers of the netius infra-structure the out-of-box installation
is sufficient and many services are available for instance:

* WSGIServer - `python -m netius.servers.wsgi`
* HelloServer - `MESSAGE="Hello Netius" python -m netius.extra.hello`
* FileServer - `BASE_PATH=/ python -m netius.extra.file`

## Compatability

Currently netius is compatible with pypy and a typical environment will benefit from a 1.5x to 2.5x
performance increase when compared with the cpython interpreter.

## Benchmarks

Running `ab -n 20000 -c 5 -k http://srio.hive:8080/` whoud should get the following results:

* `HelloServer` - 9.6 K req/sec
* `WSGIServer` - 8.7 K req/sec

These values have been verified under commit #7c2687b under python 2.6.6.