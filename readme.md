# [Netius Framework](http://netius.com)

Series of network related libraries for the rapid creation of non blocking async server and clients.

## Benchmarks

Running `ab -n 2000 -c 5 -k http://srio.hive:8080/` whoud should get the following results:

* `HelloServer` - 4.3 req/sec
* `WSGIServer` - 2.5 req/sec

Old version of netius provide much better performance as they defer the sending request to
a latter stage this would improve the performance to a really high level.