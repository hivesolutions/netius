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

from . import agent
from . import asynchronous
from . import client
from . import common
from . import compat
from . import config
from . import conn
from . import container
from . import errors
from . import legacy
from . import log
from . import observer
from . import poll
from . import protocol
from . import request
from . import server
from . import stream
from . import tls
from . import transport
from . import util

from .agent import Agent, ClientAgent, ServerAgent
from .asynchronous import Future, Task, Handle, Executor, ThreadPoolExecutor, coroutine,\
    async_test_all, async_test, ensure_generator, get_asyncio, is_coroutine,\
    is_coroutine_object, is_coroutine_native, is_future, is_neo, is_asynclib, is_await,\
    wakeup, sleep, wait, notify, coroutine_return
from .client import Client, DatagramClient, StreamClient
from .common import NAME, VERSION, IDENTIFIER_SHORT, IDENTIFIER_LONG,\
    IDENTIFIER, TCP_TYPE, UDP_TYPE, SSL_KEY_PATH, SSL_CER_PATH, SSL_CA_PATH,\
    SSL_DH_PATH, Base, BaseThread, new_loop_main, new_loop_asyncio, new_loop,\
    ensure_main, ensure_asyncio, ensure_loop, get_main, get_loop, get_event_loop,\
    stop_loop, compat_loop, get_poll, build_future, ensure, ensure_pool
from .compat import BaseLoop, CompatLoop, is_compat, is_asyncio, build_datagram,\
    connect_stream
from .config import conf, conf_prefix, conf_suffix, conf_s, conf_r, conf_d
from .conn import OPEN, CLOSED, PENDING, CHUNK_SIZE, Connection
from .container import Container, ContainerServer
from .errors import NetiusError, RuntimeError, StopError, PauseError, DataError, ParserError,\
    GeneratorError, SecurityError, NotImplemented, AssertionError
from .log import SILENT, rotating_handler, smtp_handler
from .observer import Observable
from .poll import Poll, EpollPoll, KqueuePoll, PollPoll, SelectPoll
from .protocol import Protocol, DatagramProtocol, StreamProtocol
from .request import Request, Response
from .server import Server, DatagramServer, StreamServer
from .stream import Stream
from .tls import fingerprint, match_fingerprint, match_hostname, dnsname_match,\
    dump_certificate
from .transport import Transport, TransportDatagram, TransportStream
from .util import camel_to_underscore, verify
