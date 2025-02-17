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

import os
import time
import socket
import inspect
import datetime
import threading
import collections

import logging.handlers

from . import config

SILENT = logging.CRITICAL + 1
""" The "artificial" silent level used to silent a logger
or an handler, this is used as an utility for debugging
purposes more that a real feature for production systems """

MAX_LENGTH_LOGSTASH = 256
""" The maximum amount of messages that are kept in
memory until they are flushed, avoid a very large
number for this value or else a large amount of memory
may be used for logging purposes """

TIMEOUT_LOGSTASH = 30.0
""" The maximum amount of time in between flush
operations in the logstash handler """


class LogstashHandler(logging.Handler):

    def __init__(
        self,
        level=logging.NOTSET,
        max_length=MAX_LENGTH_LOGSTASH,
        timeout=TIMEOUT_LOGSTASH,
        api=None,
    ):
        logging.Handler.__init__(self, level=level)
        if not api:
            api = self._build_api()
        self.messages = collections.deque()
        self.max_length = max_length
        self.timeout = timeout
        self.api = api
        self._last_flush = time.time()

    @classmethod
    def is_ready(cls):
        try:
            import logstash
        except ImportError:
            return False
        if not config.conf("LOGGING_LOGSTASH", False, cast=bool):
            return False
        return True

    def emit(self, record, raise_e=False):
        from . import common

        # verifies if the API structure is defined and set and if
        # that's not the case returns immediately
        if not self.api:
            return

        # in case the record to be emitted has been marked as being
        # part of a stack (traceback) then ignores it (noise)
        if hasattr(record, "stack") and record.stack:
            return

        # retrieves the current date time value as an utc value
        # and then formats it according to the provided format string
        message = self.format(record)

        # creates the log record structure that is going to be sent
        # to the logstash infra-structure, this should represent a
        # proper structure ready to be debugged
        now = datetime.datetime.utcnow()
        now_s = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # tries to build the right version of the `meta` information
        # present in the record using either the structure `meta`
        # value or the lazy evaluation of the `meta_c` method
        if hasattr(record, "meta"):
            meta = record.meta
        elif hasattr(record, "meta_c"):
            meta = dict()
            for callable in record.meta_c:
                try:
                    ctx = callable()
                except Exception:
                    if raise_e:
                        raise
                    ctx = dict()
                meta.update(ctx)
        else:
            meta = None

        log = {
            "@timestamp": now_s,
            "message_fmt": message,
            "logger": record.name,
            "message": record.message,
            "level": record.levelname,
            "path": record.pathname,
            "lineno": record.lineno,
            "host": socket.gethostname(),
            "hostname": socket.gethostname(),
            "tid": threading.current_thread().ident,
            "pid": os.getpid() if hasattr(os, "getpid") else -1,
            "agent": common.NAME,
            "version": common.VERSION,
            "identifier": common.IDENTIFIER_SHORT,
            "identifier_long": common.IDENTIFIER_LONG,
            "netius": True,
        }
        if not meta == None:
            log["meta"] = meta

        self.messages.append(log)
        message_overflow = len(self.messages) >= self.max_length
        time_overflow = time.time() - self._last_flush > self.timeout
        should_flush = message_overflow or time_overflow
        if should_flush:
            try:
                self.flush(raise_e=raise_e)
            except Exception:
                if raise_e:
                    raise

    def flush(self, force=False, raise_e=False):
        logging.Handler.flush(self)

        # verifies if the API structure is defined and set and if
        # that's not the case returns immediately
        if not self.api:
            return

        # in case the force flag is not set and there are no messages
        # to be flushed returns immediately (nothing to be done)
        messages = self.messages
        if not messages and not force:
            return

        # clears the current set of messages and updates the last flush timestamp
        # does this before the actual flush operation to avoid duplicated messages
        self.messages = []
        self._last_flush = time.time()

        # posts the complete set of messages to logstash, notice that this is a blocking
        # call and may take some time to be completed
        self.api.log_bulk(messages, tag="default", raise_e=raise_e)

    def _build_api(self):
        try:
            import logstash
        except ImportError:
            return None

        if not config.conf("LOGGING_LOGSTASH", False, cast=bool):
            return None

        return logstash.API()


def rotating_handler(
    path="netius.log", max_bytes=1048576, max_log=5, encoding=None, delay=False
):
    return logging.handlers.RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=max_log, encoding=encoding, delay=delay
    )


def smtp_handler(
    host="localhost",
    port=25,
    sender="no-reply@netius.com",
    receivers=[],
    subject="Netius logging",
    username=None,
    password=None,
    stls=False,
):
    address = (host, port)
    if username and password:
        credentials = (username, password)
    else:
        credentials = None
    has_secure = in_signature(logging.handlers.SMTPHandler.__init__, "secure")
    if has_secure:
        kwargs = dict(secure=() if stls else None)
    else:
        kwargs = dict()
    return logging.handlers.SMTPHandler(
        address, sender, receivers, subject, credentials=credentials, **kwargs
    )


def in_signature(callable, name):
    has_full = hasattr(inspect, "getfullargspec")
    if has_full:
        spec = inspect.getfullargspec(callable)
    else:
        spec = inspect.getargspec(callable)
    args, _varargs, kwargs = spec[:3]
    return (args and name in args) or (kwargs and "secure" in kwargs)
