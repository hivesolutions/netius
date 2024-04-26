#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Netius System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import sys
import time
import socket
import weakref

from . import config
from . import errors
from . import legacy
from . import transport

from . import asynchronous

asyncio = asynchronous.get_asyncio() if asynchronous.is_neo() else None
BaseLoop = asyncio.AbstractEventLoop if asyncio else object


class CompatLoop(BaseLoop):
    """
    Top level compatibility class that adds compatibility support
    for the asyncio event loop strategy.

    This is required to be able to access netius event loop on a
    asyncio like manner.

    :see: https://docs.python.org/3/library/asyncio-eventloop.html
    """

    def __init__(self, loop):
        self._loop = weakref.proxy(loop)
        self._loop_ref = weakref.ref(loop)
        self._task_factory = asynchronous.Task
        self._executor = asynchronous.ThreadPoolExecutor(loop)
        self._handler = self._default_handler

    def __getattr__(self, name):
        if hasattr(self._loop, name):
            return getattr(self._loop, name)
        raise AttributeError("'%s' not found" % name)

    def time(self):
        return time.time()

    def call_soon(self, callback, *args):
        return self._call_delay(callback, args, immediately=True)

    def call_soon_threadsafe(self, callback, *args):
        return self._call_delay(callback, args, immediately=True, safe=True)

    def call_at(self, when, callback, *args):
        delay = when - self.time()
        return self._call_delay(callback, args, timeout=delay)

    def call_later(self, delay, callback, *args):
        """
        Calls the provided callback with the provided parameters after
        the defined delay (in seconds), should ensure proper sleep operation.

        :type delay: float
        :param delay: The delay in seconds after which the callback is going
        to be called with the provided arguments.
        :type callback: Function
        :param callback: The function to be called after the provided delay.
        :rtype: Handle
        :return: The handle object to the operation, that may be used to cancel it.
        """

        return self._call_delay(callback, args, timeout=delay)

    def create_future(self):
        return self._loop.build_future()

    def create_task(self, coroutine):
        future = self._loop.ensure(coroutine)
        task = self._task_factory(future)
        return task

    def create_server(self, *args, **kwargs):
        coroutine = self._create_server(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def create_connection(self, *args, **kwargs):
        coroutine = self._create_connection(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def create_datagram_endpoint(self, *args, **kwargs):
        coroutine = self._create_datagram_endpoint(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def getaddrinfo(self, *args, **kwargs):
        coroutine = self._getaddrinfo(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def getnameinfo(self, *args, **kwargs):
        coroutine = self._getnameinfo(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def run_until_complete(self, future):
        self._set_current_task(future)
        try:
            return self._loop.run_coroutine(future)
        finally:
            self._unset_current_task()

    def run_forever(self):
        return self._loop.run_forever()

    def run_in_executor(self, *args, **kwargs):
        coroutine = self._run_in_executor(*args, **kwargs)
        return asynchronous.coroutine_return(coroutine)

    def stop(self):
        self._loop.pause()

    def close(self):
        self._loop.close()

    def get_exception_handler(self):
        return self._handler

    def set_exception_handler(self, handler):
        self._handler = handler

    def default_exception_handler(self, context):
        return self._default_handler(context)

    def call_exception_handler(self, context):
        if not self._handler:
            return
        return self._handler(context)

    def get_debug(self):
        return self._loop.is_debug()

    def set_debug(self, enabled):
        pass

    def set_default_executor(self, executor):
        self._executor = executor

    def get_task_factory(self):
        return self._task_factory

    def set_task_factory(self, factory):
        self._task_factory = factory

    def is_running(self):
        return self._loop.is_running()

    def is_closed(self):
        return self._loop.is_stopped()

    def _getaddrinfo(self, host, port, family=0, type=0, proto=0, flags=0):
        future = self.create_future()
        result = socket.getaddrinfo(host, port, family, type, proto, flags=flags)
        self._loop.delay(lambda: future.set_result(result), immediately=True)
        yield future

    def _getnameinfo(self, sockaddr, flags=0):
        raise errors.NotImplemented("Missing implementation")

    def _run_in_executor(self, executor, func, *args):
        executor = executor or self._executor
        future = executor.submit(func, *args)
        yield future

    def _create_server(
        self,
        protocol_factory,
        host=None,
        port=None,
        family=0,
        flags=0,
        sock=None,
        backlog=100,
        ssl=None,
        reuse_address=None,
        reuse_port=None,
        start_serving=True,
        *args,
        **kwargs
    ):
        family = family or socket.AF_INET

        future = self.create_future()

        def on_complete(service, serve, success):
            if success:
                on_success(service, serve=serve)
            else:
                on_error(service)

        def on_success(service, serve=None):
            server = transport.ServerTransport(self, service)
            server._set_compat(protocol_factory, serve=serve)
            if start_serving:
                server._serve()
                server._serving = True
            future.set_result(server)

        def on_error(connection):
            future.set_exception(errors.RuntimeError("Server creation issue"))

        self._loop.serve(host, port, ssl=ssl, family=family, callback=on_complete)

        yield future

    def _create_connection(
        self,
        protocol_factory,
        host=None,
        port=None,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
        sock=None,
        local_addr=None,
        server_hostname=None,
        *args,
        **kwargs
    ):
        family = family or socket.AF_INET
        proto = proto or socket.SOCK_STREAM

        future = self.create_future()

        def on_complete(connection, success):
            if success:
                on_connect(connection)
            else:
                on_error(connection)

        def on_connect(connection):
            protocol = protocol_factory()
            _transport = transport.TransportStream(self, connection)
            _transport._set_compat(protocol)
            future.set_result((_transport, protocol))

        def on_error(connection):
            future.set_exception(errors.RuntimeError("Connection issue"))

        self._loop.connect(host, port, ssl=ssl, family=family, callback=on_complete)

        yield future

    def _create_datagram_endpoint(
        self,
        protocol_factory,
        local_addr=None,
        remote_addr=None,
        family=0,
        proto=0,
        flags=0,
        reuse_address=None,
        reuse_port=None,
        allow_broadcast=None,
        sock=None,
        *args,
        **kwargs
    ):
        family = family or socket.AF_INET
        proto = proto or socket.SOCK_DGRAM

        future = self.create_future()

        def on_complete(connection, success):
            if success:
                on_connect(connection)
            else:
                on_error(connection)

        def on_connect(connection):
            protocol = protocol_factory()
            _transport = transport.TransportDatagram(self, connection)
            _transport._set_compat(protocol)
            future.set_result((_transport, protocol))

        def on_error(connection):
            future.set_exception(errors.RuntimeError("Connection issue"))

        connection = self._loop.datagram(
            family=family,
            type=proto,
            local_host=local_addr[0] if local_addr else None,
            local_port=local_addr[1] if local_addr else None,
            remote_host=remote_addr[0] if remote_addr else None,
            remote_port=remote_addr[1] if remote_addr else None,
        )

        self._loop.delay(lambda: on_complete(connection, True))
        yield future

    def _start_serving(
        self,
        protocol_factory,
        sock,
        sslcontext=None,
        server=None,
        backlog=100,
        ssl_handshake_timeout=None,
    ):
        # @TODO: this is pending proper Netius implementation
        self._add_reader(
            sock.fileno(),
            self._accept_connection,
            protocol_factory,
            sock,
            sslcontext,
            server,
            backlog,
            ssl_handshake_timeout,
        )

    def _set_current_task(self, task):
        """
        Updates the currently executing task in the global
        asyncio state, remember that only one task can be
        running per each event loop.

        :type task: Task
        :param task: The task object that is going to be set
        as the currently running task.
        """

        asyncio = asynchronous.get_asyncio()
        if not asyncio:
            return
        self._current_tasks[self] = task

    def _unset_current_task(self):
        """
        Removes the currently running task for the current
        event loop (pop operation).
        """

        asyncio = asynchronous.get_asyncio()
        if not asyncio:
            return
        self._current_tasks.pop(self, None)

    def _call_delay(
        self, callback, args, timeout=None, immediately=False, verify=False, safe=False
    ):
        # creates the callable to be called after the timeout, note the
        # clojure around the "normal" arguments (allows proper propagation)
        callable = lambda: callback(*args)

        # schedules the delay call of the created callable according to
        # the provided set of options expected by the delay operation the
        # callback tuple is returned so that a proper handle may be created
        callable_t = self._loop.delay(
            callable, timeout=timeout, immediately=immediately, verify=verify, safe=safe
        )

        # creates the handle to control the operation and then returns the
        # object to the caller method, allowing operation cancellation
        handle = asynchronous.Handle(callable_t=callable_t)
        return handle

    def _sleep(self, timeout, future=None):
        # verifies if a future variable is meant to be re-used
        # or if instead a new one should be created for the new
        # sleep operation to be executed
        future = future or self.create_future()

        # creates the callable that is going to be used to set
        # the final value of the future variable
        callable = lambda: future.set_result(timeout)

        # delays the execution of the callable so that it is executed
        # after the requested amount of timeout, note that the resolution
        # of the event loop will condition the precision of the timeout
        future._loop.call_later(timeout, callable)
        return future

    def _default_handler(self, context):
        message = context.pop("message", None)
        sys.stderr.write("%s\n" % message)
        for key, value in legacy.iteritems(context):
            sys.stderr.write("%s: %s\n" % (key, value))

    @property
    def _thread_id(self):
        return self._loop.tid

    @property
    def _current_tasks(self):
        if hasattr(asyncio.tasks, "_current_tasks"):
            return asyncio.tasks._current_tasks
        return asyncio.Task._current_tasks


def is_compat():
    """
    Determines if the compatibility mode for the netius
    event loop is required.

    Under this mode the event loop for netius tries to emulate
    the behaviour of the asyncio event loop so that it may
    be used with 3rd party protocol classes (not compliant
    with the netius protocol).

    :rtype: bool
    :return: If the netius infra-structure should run under
    the compatibility mode.
    """

    compat = config.conf("COMPAT", False, cast=bool)
    compat |= is_asyncio()
    return compat and asynchronous.is_neo()


def is_asyncio():
    """
    Checks if the asyncio mode of execution (external event
    loop) is the required approach under the current runtime.

    If that's the case the netius event loop is not going to
    be used and the asyncio one is going to be used instead.

    :rtype: bool
    :return: If the asyncio event loop model is enabled and
    proper library support available.
    """

    asyncio = config.conf("ASYNCIO", False, cast=bool)
    return asyncio and asynchronous.is_asynclib()


def run(coro):
    from . import common

    loop = common.get_loop(_compat=True)
    loop.run_until_complete(coro)


def build_datagram(*args, **kwargs):
    if is_compat():
        return _build_datagram_compat(*args, **kwargs)
    else:
        return _build_datagram_native(*args, **kwargs)


def connect_stream(*args, **kwargs):
    if is_compat():
        return _connect_stream_compat(*args, **kwargs)
    else:
        return _connect_stream_native(*args, **kwargs)


def serve_stream(*args, **kwargs):
    if is_compat():
        return _serve_stream_compat(*args, **kwargs)
    else:
        return _serve_stream_native(*args, **kwargs)


def _build_datagram_native(
    protocol_factory,
    family=socket.AF_INET,
    type=socket.SOCK_DGRAM,
    remote_host=None,
    remote_port=None,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    """
    Builds a datagram assuming that the current event
    loop in execution is a Netius one and that the support
    for the Netius specific methods exist.

    This method is typically faster than using the compat
    one which only makes use of the asyncio API.

    The end goal of this method is to call the callback method
    with a tuple containing both the transport and the protocol
    for the requested datagram based "connection".
    """

    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def on_ready():
        loop.datagram(
            family=family,
            type=type,
            remote_host=remote_host,
            remote_port=remote_port,
            callback=on_complete,
        )

    def on_complete(connection, success):
        if success:
            on_connect(connection)
        else:
            on_error(connection)

    def on_connect(connection):
        _transport = transport.TransportDatagram(loop, connection)
        _transport._set_compat(protocol)
        if not callback:
            return
        if callback:
            callback((_transport, protocol))

    def on_error(connection):
        protocol.close()

    loop.delay(on_ready)

    return loop


def _build_datagram_compat(
    protocol_factory,
    family=socket.AF_INET,
    type=socket.SOCK_DGRAM,
    remote_host=None,
    remote_port=None,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def build_protocol():
        return protocol

    def on_connect(future):
        if future.cancelled() or future.exception():
            protocol.close()
        else:
            result = future.result()
            if callback:
                callback(result)

    remote_addr = (
        (remote_host, remote_port)
        if remote_host and remote_port
        else kwargs.pop("remote_addr", None)
    )

    connect = loop.create_datagram_endpoint(
        build_protocol,
        family=family,
        proto=type,
        remote_addr=remote_addr,
        *args,
        **kwargs
    )

    future = loop.create_task(connect)
    future.add_done_callback(on_connect)

    return loop


def _connect_stream_native(
    protocol_factory,
    host,
    port,
    ssl=False,
    key_file=None,
    cer_file=None,
    ca_file=None,
    ca_root=True,
    ssl_verify=False,
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    """
    Runs the connect operation for a given stream using the internal
    Netius based strategy, meaning that the underlying structures
    involved should include connection and the base Netius event loop
    methods should be used.

    The end goal of this function is to call the provided callback
    with a tuple containing both a transport and a protocol instance.

    This callback should only be called once a proper connection has
    been established.
    """

    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def on_ready():
        loop.connect(
            host,
            port,
            ssl=ssl,
            key_file=key_file,
            cer_file=cer_file,
            ca_file=ca_file,
            ca_root=ca_root,
            ssl_verify=ssl_verify,
            family=family,
            type=type,
            callback=on_complete,
        )

    def on_complete(connection, success):
        if success:
            on_connect(connection)
        else:
            on_error(connection)

    def on_connect(connection):
        _transport = transport.TransportStream(loop, connection)
        _transport._set_compat(protocol)
        if not callback:
            return
        if callback:
            callback((_transport, protocol))

    def on_error(connection):
        protocol.close()

    loop.delay(on_ready)

    return loop


def _connect_stream_compat(
    protocol_factory,
    host,
    port,
    ssl=False,
    key_file=None,
    cer_file=None,
    ca_file=None,
    ca_root=True,
    ssl_verify=False,
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def build_protocol():
        return protocol

    def on_connect(future):
        if future.cancelled() or future.exception():
            protocol.close()
        else:
            result = future.result()
            if callback:
                callback(result)

    if ssl and cer_file and key_file:
        import ssl as _ssl

        ssl_context = _ssl.SSLContext()
        ssl_context.load_cert_chain(cer_file, keyfile=key_file)
        ssl = ssl_context
    else:
        ssl = None

    connect = loop.create_connection(
        build_protocol,
        host=host,
        port=port,
        ssl=ssl,
        family=family,
        proto=type,
        *args,
        **kwargs
    )

    future = loop.create_task(connect)
    future.add_done_callback(on_connect)

    return loop


def _serve_stream_native(
    protocol_factory,
    host,
    port,
    ssl=False,
    key_file=None,
    cer_file=None,
    ca_file=None,
    ca_root=True,
    ssl_verify=False,
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    backlog=None,
    reuse_address=None,
    reuse_port=None,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def on_ready():
        loop.serve(host=host, port=port, callback=on_complete)

    def on_complete(service, serve, success):
        if success:
            on_success(service, serve=serve)
        else:
            on_error(service)

    def on_success(service, serve=None):
        server = transport.ServerTransport(loop, service)
        server._set_compat(protocol, serve=serve)
        if not callback:
            return
        callback(server)

    def on_error(connection):
        protocol.close()

    loop.delay(on_ready)

    return loop


def _serve_stream_compat(
    protocol_factory,
    host,
    port,
    ssl=False,
    key_file=None,
    cer_file=None,
    ca_file=None,
    ca_root=True,
    ssl_verify=False,
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    backlog=None,
    reuse_address=None,
    reuse_port=None,
    callback=None,
    loop=None,
    *args,
    **kwargs
):
    """
    Compatible version of the stream server creation method to
    make use of the same netius bootstrap infrastructure and
    the asyncio event loop.

    :see: https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.create_server
    """

    # @TODO: implement this stuff meaning that the compat
    # mode is the mode in which Netius runs compatible
    # with the asyncio module
    from . import common

    loop = loop or common.get_loop()

    protocol = protocol_factory()
    has_loop_set = hasattr(protocol, "loop_set")
    if has_loop_set:
        protocol.loop_set(loop)

    def build_protocol():
        return protocol

    def on_build(future):
        if future.cancelled() or future.exception():
            protocol.close()
        else:
            result = future.result()
            if callback:
                callback(result)

    if ssl and cer_file and key_file:
        import ssl as _ssl

        ssl_context = _ssl.SSLContext()
        ssl_context.load_cert_chain(cer_file, keyfile=key_file)
        ssl = ssl_context
    else:
        ssl = None

    # removes some of the extra arguments that may be
    # present in kwargs and would create issues
    kwargs.pop("env", None)

    build = loop.create_server(
        build_protocol,
        host=host,
        port=port,
        ssl=ssl or None,
        family=family,
        *args,
        **kwargs
    )

    future = loop.create_task(build)
    future.add_done_callback(on_build)

    return loop
