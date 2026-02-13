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

import threading

from . import compat
from . import legacy
from . import observer


class Agent(observer.Observable):
    """
    Top level class for the entry point classes of the multiple
    client and server protocol implementations.

    These classes should contain a series of utilities that facilitate
    the interaction with the Protocol, Event Loop and Transport
    objects (with the end developer in mind).

    Most of the interaction for a simple protocol should be implemented
    using static or class methods, avoiding internal object state and
    instantiation of the concrete Agent class.

    For complex protocols instantiation may be useful to provided extra
    flexibility and context for abstract operations.

    Provides Base-compatible stub methods so that Agents can be added
    to a Container alongside Base-derived objects without requiring
    the Container to use defensive guards. The new code (Agent) adapts
    to the old code (Container), keeping retro-compatibility.
    """

    _container_loop = None
    """ Reference to the container's owner (a Base instance) set by
    `Container.apply_base()` when this agent is added to a container,
    enables protocol connections to join the container's shared poll """

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def connections(self):
        return []

    @classmethod
    def cleanup_s(cls):
        pass

    def cleanup(self, destroy=True):
        if destroy:
            self.destroy()

    def destroy(self):
        observer.Observable.destroy(self)

    def load(self):
        pass

    def unload(self):
        pass

    def ticks(self):
        pass

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def connections_dict(self, full=False, parent=False):
        return dict()

    def info_dict(self, full=False):
        return dict(name=self.name)


class ClientAgent(Agent):

    _clients = dict()
    """ The global static clients map meant to be reused by the
    various static clients that may be created, this client
    may leak creating blocking threads that will prevent the
    system from exiting correctly, in order to prevent that
    the cleanup method should be called """

    @classmethod
    def cleanup_s(cls):
        super(ClientAgent, cls).cleanup_s()
        for client in legacy.itervalues(cls._clients):
            client.close()
        cls._clients.clear()

    @classmethod
    def get_client_s(cls, *args, **kwargs):
        tid = threading.current_thread().ident
        client = cls._clients.get(tid, None)
        if client:
            return client
        client = cls(*args, **kwargs)
        cls._clients[tid] = client
        return client

    def connect(self, host, port, ssl=False, *args, **kwargs):
        """
        Creates a new protocol based connection to the provided
        host and port, using the container's shared event loop when
        available (dual architecture support).

        :type host: String
        :param host: The hostname or IP address of the remote
        host to which the connection should be made.
        :type port: int
        :param port: The port number of the remote host to
        which the connection should be made.
        :type ssl: bool
        :param ssl: If the connection should be established using
        a secure SSL/TLS channel.
        :rtype: Protocol
        :return: The protocol instance that represents the newly
        created connection.
        """

        cls = self.__class__
        protocol = cls.protocol()
        compat.connect_stream(
            lambda: protocol,
            host=host,
            port=port,
            ssl=ssl,
            loop=self._container_loop,
            *args,
            **kwargs
        )
        self._relay_protocol_events(protocol)
        return protocol

    def _relay_protocol_events(self, protocol):
        """
        Relays protocol events through this client agent so that
        observers that bind on the client (eg proxy servers) receive
        events from all managed protocols.

        Subclasses should override this method and call the parent
        implementation to add protocol-specific event relays.

        :type protocol: Protocol
        :param protocol: The protocol instance whose events should
        be relayed through this client agent.
        """

        protocol.bind("open", lambda protocol: self.trigger("connect", self, protocol))
        protocol.bind("close", lambda protocol: self.trigger("close", self, protocol))


class ServerAgent(Agent):
    pass
