# [Netius Framework](http://netius.com)

Series of network related libraries for the rapid creation of non blocking async server and clients.

## Benchmarks

Running `ab -n 20000 -c 5 -k http://srio.hive:8080/` whoud should get the following results:

* `HelloServer` - 9.6k req/sec
* `WSGIServer` - 8.7K req/sec
