#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

from . import async
from . import client
from . import common
from . import config
from . import conn
from . import container
from . import errors
from . import legacy
from . import log
from . import observer
from . import poll
from . import request
from . import server
from . import stream
from . import tls
from . import util

from .async import Future, coroutine, sleep, wait, notify
from .client import Client, DatagramClient, StreamClient
from .common import NAME, VERSION, IDENTIFIER_SHORT, IDENTIFIER_LONG,\
    IDENTIFIER, TCP_TYPE, UDP_TYPE, SSL_KEY_PATH, SSL_CER_PATH, SSL_CA_PATH,\
    SSL_DH_PATH, Base, BaseThread, get_main, get_loop,\
    get_poll, ensure, ensure_pool
from .config import conf, conf_prefix, conf_s
from .conn import OPEN, CLOSED, PENDING, CHUNK_SIZE, Connection
from .container import Container, ContainerServer
from .errors import NetiusError, PauseError, DataError, ParserError,\
    GeneratorError, SecurityError, NotImplemented, AssertionError
from .log import SILENT, rotating_handler, smtp_handler
from .observer import Observable
from .poll import Poll, EpollPoll, KqueuePoll, PollPoll, SelectPoll
from .request import Request, Response
from .server import Server, DatagramServer, StreamServer
from .stream import Stream
from .tls import thumbprint, match_thumbprint, match_hostname, dnsname_match
from .util import camel_to_underscore
