#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import threading

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
    """

    @classmethod
    def cleanup_s(cls):
        pass

    def cleanup(self, destroy = True):
        if destroy: self.destroy()

    def destroy(self):
        observer.Observable.destroy(self)

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
        if client: return client
        client = cls(*args, **kwargs)
        cls._clients[tid] = client
        return client

class ServerAgent(Agent):
    pass
