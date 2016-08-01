`Netius <http://netius.hive.pt>`__
==================================

Fast and readable async non-blocking network apps

Netius is a Python network library that can be used for the rapid creation of asynchronous non-blocking
servers and clients. It has no dependencies, it's cross-platform, and brings some sample netius-powered
servers out of the box, namely a production-ready WSGI server.

Simplicity and performance are the main drivers of this project. The codebase adheres to very strict
code standards, and is extensively commented; and as far as performance is concerned, it aims to
be up to par with equivalent native implementations, where `PyPy <http://pypy.org>`__ can be used to
provide the extra boost to raise performance up to these standards.

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
            ("Content-Type", "text/plain"),
            ("Connection", "keep-alive")
        )
        start_response(status, headers)
        yield contents

    server = netius.servers.WSGIServer(app = app)
    server.serve(port = 8080)

More
----

For more information consult the `website <http://netius.hive.pt>`__.
