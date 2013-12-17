# [Netius Framework](http://netius.com)

Series of network related libraries for the rapid creation of non blocking async server and clients.

## Usage

### HTTP Client

```python
import netius.clients

def on_partial(client, parser, data):
    print data

netius.clients.HTTPClient.get_s(
    "http://www.flickr.com/",
    on_data = on_partial
)
```

## Benchmarks

Running `ab -n 20000 -c 5 -k http://srio.hive:8080/` whoud should get the following results:

* `HelloServer` - 9.6 K req/sec
* `WSGIServer` - 8.7 K req/sec
