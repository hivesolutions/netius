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

from . import legacy
from . import request
from . import observer


class Protocol(observer.Observable):
    """
    Abstract base for protocol implementations, providing
    an interface that is API-compatible with asyncio's
    `Protocol` class.

    Manages the lifecycle of a connection through the
    standard `connection_made` and `connection_lost` callbacks
    and provides flow control via `pause_writing` and
    `resume_writing`.

    Concrete subclasses should override data handling
    methods (eg `data_received`, `datagram_received`)
    to implement their specific protocol logic.
    """

    def __init__(self, owner=None):
        observer.Observable.__init__(self)
        self.owner = owner
        self._transport = None
        self._loop = None
        self._writing = True
        self._open = False
        self._closed = False
        self._closing = False
        self._delayed = []
        self._callbacks = []

    def open(self):
        # in case the protocol is already open, ignores the current
        # call as it's considered a double opening
        if self.is_open():
            return

        # calls the concrete implementation of the open operation
        # allowing an extra level of indirection
        self.open_c()

        self.trigger("open", self)

    def close(self):
        # in case the protocol is already closed, ignores the current
        # call considering it a double closing operation
        if self.is_closed() or self.is_closing():
            return

        # calls the concrete implementation of the close operation
        # allowing an extra level of indirection, allowing subclasses
        # to implement custom close behavior
        self.close_c()

        # triggers the close event before the delayed finish
        # operation runs, this is critical because when _loop
        # is None the delay call executes finish() synchronously
        # which destroys all event bindings via unbind_all(),
        # the event must fire while handlers are still bound
        self.trigger("close", self)

        # delays the execution of the finish (cleanup) operation
        # so that all the pending operations from the close
        # can be executed in the meantime, ensuring a proper,
        # secure and clean execution of the finish method
        self.delay(self.finish)

    def finish(self):
        # in case the current protocol is already (completely) closed
        # or is not in the state of closing, nothing should be done
        if self.is_closed():
            return
        if not self.is_closing():
            return

        # calls the concrete implementation of the finish operation
        # allowing an extra level of indirection
        self.finish_c()

        self.trigger("finish", self)

        # runs the "final" destroy operation that is going to run
        # the most structural elements of this object
        self.destroy()

    def open_c(self):
        # unmarks the current protocol from closed (and closing)
        # meaning that it will be opened one more time and
        # so it must not be considered as closed
        self._open = True
        self._closed = False
        self._closing = False

    def close_c(self):
        # marks the current protocol as closing, meaning that although
        # the close operation is not yet finished it's starting
        self._closing = True

        # runs the close transport call that triggers the process
        # of closing the underlying transport method, notice that
        # this operation is only considered to be safely completed
        # on the next tick of the event loop
        self._close_transport()

    def finish_c(self):
        del self._delayed[:]
        del self._callbacks[:]

        self._transport = None
        self._loop = None
        self._writing = True
        self._open = False
        self._closed = True
        self._closing = False

    def info_dict(self, full=False):
        if not self._transport:
            return dict()
        info = self._transport.info_dict(full=full)
        return info

    def connection_made(self, transport):
        self._transport = transport

        # ensure that the protocol is open, please notice
        # that most of the time the protocol is already open
        self.open()

    def connection_lost(self, exception):
        self.close()

    def transport(self):
        return self._transport

    def loop(self):
        return self._loop

    def loop_set(self, loop):
        self._loop = loop

        self.trigger("loop_set", self)

    def loop_unset(self):
        self._loop = None

        self.trigger("loop_unset", self)

    def pause_writing(self):
        self._writing = False

    def resume_writing(self):
        self._writing = True
        self._flush_callbacks()
        self._flush_send()

    def delay(self, callable, timeout=None):
        # in case there's no event loop defined for the protocol
        # it's not possible to delay this execution so the
        # callable is called immediately
        if not self._loop:
            return callable()

        # verifies if the assigned loop contains the non-standard
        # delay method and if that's the case calls it instead of
        # the base asyncio API ones (compatibility)
        if hasattr(self._loop, "delay"):
            immediately = timeout == None
            return self._loop.delay(callable, timeout=timeout, immediately=immediately)

        # calls the proper call method taking into account if a timeout
        # value exists or not (soon against later)
        if timeout:
            return self._loop.call_later(timeout, callable)
        else:
            return self._loop.call_soon(callable)

    def debug(self, object):
        if not self._loop:
            return
        if not hasattr(self._loop, "debug"):
            return
        self._loop.debug(object)

    def info(self, object):
        if not self._loop:
            return
        if not hasattr(self._loop, "info"):
            return
        self._loop.info(object)

    def warning(self, object):
        if not self._loop:
            return
        if not hasattr(self._loop, "warning"):
            return
        self._loop.warning(object)

    def error(self, object):
        if not self._loop:
            return
        if not hasattr(self._loop, "error"):
            return
        self._loop.error(object)

    def critical(self, object):
        if not self._loop:
            return
        if not hasattr(self._loop, "critical"):
            return
        self._loop.critical(object)

    def is_pending(self):
        return not self._open and not self._closed and not self._closing

    def is_open(self):
        return self._open

    def is_closed(self):
        return self._closed

    def is_closing(self):
        return self._closing

    def is_closed_or_closing(self):
        return self._closed or self._closing

    def is_devel(self):
        if not self._loop:
            return False
        if not hasattr(self._loop, "is_devel"):
            return False
        return self._loop.is_devel()

    def _close_transport(self, force=False):
        if not self._transport:
            return
        self._transport.abort()

    def _delay_send(self, data, address=None, callback=None):
        item = (data, address, callback)
        self._delayed.append(item)
        return len(data)

    def _flush_callbacks(self):
        while self._callbacks:
            callback = self._callbacks.pop(0)
            self.delay(lambda: callback(self._transport))

    def _flush_send(self):
        while True:
            if not self._delayed:
                break
            if not self._writing:
                break
            data, address, callback = self._delayed.pop(0)
            if address:
                self.send(data, address, callback=callback)  # pylint: disable=E1101
            else:
                self.send(data, callback=callback)  # pylint: disable=E1101


class DatagramProtocol(Protocol):
    """
    Protocol for connectionless datagram-based communication
    (eg UDP), API-compatible with asyncio's
    `DatagramProtocol`.

    Incoming data arrives through `datagram_received`
    and outgoing data is sent via `send`. Maintains a
    request queue for correlating responses to pending
    requests using their identifiers.
    """

    def __init__(self):
        Protocol.__init__(self)
        self.requests = []
        self.requests_m = {}

    def datagram_received(self, data, address):
        self.on_data(address, data)

    def error_received(self, exception):
        pass

    def on_data(self, address, data):
        self.trigger("data", self, data)

    def send(self, data, address, delay=True, force=False, callback=None):
        return self.send_to(data, address, delay=delay, force=force, callback=callback)

    def send_to(self, data, address, delay=True, force=False, callback=None):
        # ensures that the provided data value is a bytes sequence
        # so that its format is compliant with what's expected by
        # the underlying transport send to operation
        data = legacy.bytes(data)

        # in case the current transport buffers do not allow writing
        # (paused mode) the writing of the data is delayed until the
        # writing is again enabled (resume writing)
        if not self._writing:
            return self._delay_send(data, address=address, callback=callback)

        # pushes the write data down to the transport layer immediately
        # as writing is still allowed for the current protocol
        self._transport.sendto(data, address)

        # in case there's a callback associated with the send
        # tries to see if the data has been completely flushed
        # (writing still enabled) and if so schedules the callback
        # to be called on the next tick, otherwise adds it to the
        # callbacks to be called upon the next write resume operation
        if callback:
            if self._writing:
                self.delay(lambda: callback(self._transport))
            else:
                self._callbacks.append(callback)

        # returns the size (in bytes) of the data that has just been
        # explicitly sent through the associated transport
        return len(data)

    def add_request(self, request):
        # adds the current request object to the list of requests
        # that are pending a valid response, a garbage collector
        # system should be able to erase this request from the
        # pending list in case a timeout value has passed
        self.requests.append(request)
        self.requests_m[request.id] = request

    def remove_request(self, request):
        self.requests.remove(request)
        del self.requests_m[request.id]

    def get_request(self, id):
        is_response = isinstance(id, request.Response)
        if is_response:
            id = id.get_id()
        return self.requests_m.get(id, None)


class StreamProtocol(Protocol):
    """
    Protocol for stream-based (TCP) communication, providing
    an interface compatible with asyncio's `Protocol` class.

    Incoming bytes arrive through `data_received` and
    outgoing data is written via `send`. Exposes backward
    compatibility delegation properties (`socket`, `renable`,
    `is_throttleable`, etc.) that reach through the transport
    to the underlying `Connection` object, allowing protocol
    instances to be used in code paths that still expect the
    older `Connection` interface (eg proxy servers).
    """

    @property
    def connection(self):
        """
        Returns the underlying connection for backward compatibility
        with code that expects a Connection object (eg proxy servers).

        :rtype: Connection
        :return: The underlying connection object associated with
        the transport, or None if no transport is set or does not
        expose a connection object.
        """

        # in case there's no transport associated with the current protocol
        # it's not possible to retrieve the connection object so None is
        # returned to indicate the absence of a connection
        if not self._transport:
            return None

        # in asyncio compat mode the transport may be an asyncio transport
        # instance, which does not expose the private `_connection`
        # attribute, guard access to avoid AttributeError while keeping
        # backward compatibility for custom transports that do define it.
        if not hasattr(self._transport, "_connection"):
            return None

        return self._transport._connection

    @property
    def socket(self):
        connection = self.connection
        if not connection:
            return None
        return connection.socket

    @property
    def address(self):
        connection = self.connection
        if connection:
            return connection.address
        return getattr(self, "_address", None)

    @address.setter
    def address(self, value):
        self._address = value
        connection = self.connection
        if connection:
            connection.address = value

    @property
    def renable(self):
        connection = self.connection
        if not connection:
            return True
        return connection.renable

    @renable.setter
    def renable(self, value):
        connection = self.connection
        if not connection:
            return
        connection.renable = value

    def is_throttleable(self):
        connection = self.connection
        if not connection:
            return False
        return connection.is_throttleable()

    def is_exhausted(self):
        connection = self.connection
        if not connection:
            return False
        return connection.is_exhausted()

    def is_restored(self):
        connection = self.connection
        if not connection:
            return True
        return connection.is_restored()

    def disable_read(self):
        connection = self.connection
        if not connection:
            return
        connection.disable_read()

    def enable_read(self):
        connection = self.connection
        if not connection:
            return
        connection.enable_read()

    @property
    def max_pending(self):
        connection = self.connection
        if connection:
            return connection.max_pending
        return getattr(self, "_max_pending", -1)

    @max_pending.setter
    def max_pending(self, value):
        self._max_pending = value
        connection = self.connection
        if connection:
            connection.max_pending = value

    @property
    def min_pending(self):
        connection = self.connection
        if connection:
            return connection.min_pending
        return getattr(self, "_min_pending", -1)

    @min_pending.setter
    def min_pending(self, value):
        self._min_pending = value
        connection = self.connection
        if connection:
            connection.min_pending = value

    def connection_made(self, transport):
        Protocol.connection_made(self, transport)

        # propagates any pending limit values that were set before the
        # connection was established, this is required for container
        # proxy scenarios where limits are set right after connect()
        connection = self.connection
        if connection:
            if hasattr(self, "_max_pending"):
                connection.max_pending = self._max_pending
            if hasattr(self, "_min_pending"):
                connection.min_pending = self._min_pending

    def data_received(self, data):
        self.on_data(data)

    def eof_received(self):
        pass

    def on_data(self, data):
        self.trigger("data", self, data)

    def send(self, data, delay=True, force=False, callback=None):
        # ensures that the provided data value is a bytes sequence
        # so that its format is compliant with what's expected by
        # the underlying transport write operation
        data = legacy.bytes(data)

        # in case the transport has been unset (connection closed or
        # closing) the send operation is silently ignored
        if not self._transport:
            return 0

        # in case the current transport buffers do not allow writing
        # (paused mode) the writing of the data is delayed until the
        # writing is again enabled (resume writing)
        if not self._writing:
            return self._delay_send(data, callback=callback)

        # pushes the write data down to the transport layer immediately
        # as writing is still allowed for the current protocol
        self._transport.write(data)

        # in case there's a callback associated with the send
        # tries to see if the data has been completely flushed
        # (writing still enabled), and if so, schedules the callback
        # to be called on the next tick otherwise adds it to the
        # callbacks to be called upon the next write resume operation
        if callback:
            if self._writing:
                self.delay(lambda: callback(self._transport))
            else:
                self._callbacks.append(callback)

        # returns the size (in bytes) of the data that has just been
        # explicitly sent through the associated transport
        return len(data)
