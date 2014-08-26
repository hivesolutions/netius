`Netius <http://netius.hive.pt>`__
==================================

Series of network related libraries for the rapid creation of non
blocking async server and clients. The aim of this project is to create
a platform for creation of customized servers and clients for specific
and pre-defined purposes using simple inheritance techniques.

Performance is considered to be one of the main priorities of the
project as it should be possible to replace a native code stack with
netius equivalents. `PyPy <http://pypy.org>`__ should provide the extra
speed required for these kind of (speed savy) use cases.

Installation
------------

    pip install netius

Usage
-----

WSGI Server
~~~~~~~~~~~

.. code:: python

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

More
----

For more information consult the `website <http://netius.hive.pt>`__.
