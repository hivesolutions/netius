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
import logging
import tempfile
import unittest

import logging.handlers

import netius

from netius.base import log


class LogTest(unittest.TestCase):

    def test_silent_value(self):
        self.assertEqual(netius.SILENT, logging.CRITICAL + 1)
        self.assertEqual(type(netius.SILENT), int)

    def test_silent_above_critical(self):
        self.assertTrue(netius.SILENT > logging.CRITICAL)

    def test_trace_value(self):
        self.assertEqual(netius.TRACE, 5)
        self.assertEqual(netius.TRACE, logging.DEBUG - 5)
        self.assertEqual(type(netius.TRACE), int)

    def test_trace_below_debug(self):
        self.assertTrue(netius.TRACE < logging.DEBUG)

    def test_max_length_logstash(self):
        self.assertEqual(netius.MAX_LENGTH_LOGSTASH, 256)
        self.assertEqual(type(netius.MAX_LENGTH_LOGSTASH), int)

    def test_timeout_logstash(self):
        self.assertEqual(netius.TIMEOUT_LOGSTASH, 30.0)
        self.assertEqual(type(netius.TIMEOUT_LOGSTASH), float)

    def test_level_ordering(self):
        self.assertTrue(netius.TRACE < logging.DEBUG)
        self.assertTrue(logging.DEBUG < logging.INFO)
        self.assertTrue(logging.INFO < logging.WARNING)
        self.assertTrue(logging.WARNING < logging.ERROR)
        self.assertTrue(logging.ERROR < logging.CRITICAL)
        self.assertTrue(logging.CRITICAL < netius.SILENT)

    def test_logstash_handler_init(self):
        handler = netius.LogstashHandler(api=None)

        self.assertEqual(handler.max_length, netius.MAX_LENGTH_LOGSTASH)
        self.assertEqual(handler.timeout, netius.TIMEOUT_LOGSTASH)
        self.assertEqual(handler.api, None)
        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_init_custom(self):
        handler = netius.LogstashHandler(max_length=128, timeout=10.0, api=None)

        self.assertEqual(handler.max_length, 128)
        self.assertEqual(handler.timeout, 10.0)
        self.assertEqual(handler.api, None)

    def test_logstash_handler_init_api(self):
        api = LogstashAPI()
        handler = netius.LogstashHandler(api=api)

        # an API that is given is the one that the handler uses, no
        # attempt being made at building one of its own
        self.assertEqual(handler.api, api)

    def test_logstash_handler_emit_no_api(self):
        handler = netius.LogstashHandler(api=None)
        record = logging.LogRecord("test", logging.INFO, "", 0, "message", (), None)

        handler.emit(record)

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_emit(self):
        handler = netius.LogstashHandler(api=LogstashAPI(), max_length=2)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )

        handler.emit(record)

        self.assertEqual(len(handler.messages), 1)

        log = handler.messages[0]

        # the record is turned into the structure that logstash expects,
        # carrying both the message and the origin of it
        self.assertEqual(log["message"], "message")
        self.assertEqual(log["message_fmt"], "message")
        self.assertEqual(log["logger"], "test")
        self.assertEqual(log["level"], "INFO")
        self.assertEqual(log["path"], "path.py")
        self.assertEqual(log["lineno"], 10)
        self.assertEqual(log["netius"], True)
        self.assertEqual(log["agent"], netius.NAME)
        self.assertEqual(log["version"], netius.VERSION)

        # a record that carries no meta information leaves the field out
        # of the structure, instead of setting it to an invalid value
        self.assertEqual("meta" in log, False)

    def test_logstash_handler_emit_stack(self):
        handler = netius.LogstashHandler(api=LogstashAPI(), max_length=2)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )
        record.stack = True

        handler.emit(record)

        # a record that is part of a traceback is noise for the structured
        # log, so it is dropped instead of being emitted
        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_emit_meta(self):
        handler = netius.LogstashHandler(api=LogstashAPI(), max_length=2)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )
        record.meta = dict(first=1)

        handler.emit(record)

        # the meta of the record travels with it, so that the context of
        # the message is not lost on the way to logstash
        self.assertEqual(handler.messages[0]["meta"], dict(first=1))

    def test_logstash_handler_emit_meta_c(self):
        handler = netius.LogstashHandler(api=LogstashAPI(), max_length=2)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )
        record.meta_c = [lambda: dict(first=1), lambda: dict(second=2)]

        handler.emit(record)

        # the lazy meta is only evaluated at the moment of the emission,
        # the values of every callable being merged into a single one
        self.assertEqual(handler.messages[0]["meta"], dict(first=1, second=2))

    def test_logstash_handler_emit_meta_c_error(self):
        handler = netius.LogstashHandler(api=LogstashAPI(), max_length=2)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )
        record.meta_c = [self._raiser, lambda: dict(second=2)]

        handler.emit(record)

        # a callable that fails does not take the record with it, the
        # ones that follow still contributing to the meta
        self.assertEqual(handler.messages[0]["meta"], dict(second=2))

        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )
        record.meta_c = [self._raiser]

        # with the raising asked for the failure is no longer swallowed,
        # so that the caller is able to notice it
        self.assertRaises(
            netius.NetiusError, lambda: handler.emit(record, raise_e=True)
        )

    def test_logstash_handler_emit_overflow(self):
        api = LogstashAPI()
        handler = netius.LogstashHandler(api=api, max_length=1)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )

        handler.emit(record)

        # the buffer is full with the very first record, so the emission
        # ends in a flush of it towards the API
        self.assertEqual(len(api.bulks), 1)
        self.assertEqual(len(api.bulks[0][0]), 1)
        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_emit_overflow_error(self):
        handler = netius.LogstashHandler(api=LogstashErrorAPI(), max_length=1)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )

        handler.emit(record)

        # a flush that fails must not break the emission of the record,
        # as logging is never meant to interrupt the caller
        self.assertEqual(len(handler.messages), 0)

        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )

        self.assertRaises(
            netius.NetiusError, lambda: handler.emit(record, raise_e=True)
        )

    def test_logstash_handler_flush_no_api(self):
        handler = netius.LogstashHandler(api=None)

        handler.flush()

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_flush_empty(self):
        handler = netius.LogstashHandler(api=None)

        handler.flush(force=True)

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_flush(self):
        api = LogstashAPI()
        handler = netius.LogstashHandler(api=api, max_length=4)
        record = logging.LogRecord(
            "test", logging.INFO, "path.py", 10, "message", (), None
        )

        handler.emit(record)
        handler.flush()

        # the messages that were gathered are posted in a single bulk and
        # the buffer is emptied, so that none of them is sent twice
        self.assertEqual(len(api.bulks), 1)
        self.assertEqual(len(api.bulks[0][0]), 1)
        self.assertEqual(api.bulks[0][1], "default")
        self.assertEqual(len(handler.messages), 0)

        handler.flush()

        # with nothing left to be flushed the API is not reached again,
        # as there would be no message to carry
        self.assertEqual(len(api.bulks), 1)

    def test_logstash_handler_is_ready(self):
        result = netius.LogstashHandler.is_ready()

        self.assertEqual(type(result), bool)

    def test_rotating_handler(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            handler = netius.rotating_handler(path=path, max_bytes=1024, max_log=3)

            self.assertEqual(type(handler), logging.handlers.RotatingFileHandler)
            self.assertEqual(handler.maxBytes, 1024)
            self.assertEqual(handler.backupCount, 3)

            handler.close()
        finally:
            os.unlink(path)

    def test_rotating_handler_defaults(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        try:
            handler = netius.rotating_handler(path=path)

            self.assertEqual(handler.maxBytes, 1048576)
            self.assertEqual(handler.backupCount, 5)

            handler.close()
        finally:
            os.unlink(path)

    def test_smtp_handler(self):
        handler = log.smtp_handler(receivers=["target@netius.com"])

        try:
            self.assertEqual(type(handler), logging.handlers.SMTPHandler)
            self.assertEqual(handler.mailhost, "localhost")
            self.assertEqual(handler.mailport, 25)
            self.assertEqual(handler.fromaddr, "no-reply@netius.com")
            self.assertEqual(handler.toaddrs, ["target@netius.com"])
            self.assertEqual(handler.subject, "Netius logging")

            # with no username nor password there are no credentials to be
            # used, so that the session is never authenticated
            self.assertEqual(handler.username, None)
        finally:
            handler.close()

    def test_smtp_handler_credentials(self):
        handler = log.smtp_handler(
            host="smtp.netius.com",
            port=587,
            receivers=["target@netius.com"],
            username="username",
            password="password",
        )

        try:
            self.assertEqual(handler.mailhost, "smtp.netius.com")
            self.assertEqual(handler.mailport, 587)
            self.assertEqual(handler.username, "username")
            self.assertEqual(handler.password, "password")
        finally:
            handler.close()

    def test_smtp_handler_stls(self):
        handler = log.smtp_handler(receivers=["target@netius.com"], stls=True)

        try:
            # the secure value is what turns the start TLS on, an empty
            # sequence meaning that no certificate is presented
            self.assertEqual(handler.secure, ())
        finally:
            handler.close()

        handler = log.smtp_handler(receivers=["target@netius.com"])

        try:
            self.assertEqual(handler.secure, None)
        finally:
            handler.close()

    def test_patch_logging(self):
        netius.patch_logging()

        result = logging.getLevelName(netius.TRACE)

        self.assertEqual(result, "TRACE")

    def test_patch_logging_reverse(self):
        netius.patch_logging()

        result = logging.getLevelName("TRACE")

        self.assertEqual(result, netius.TRACE)

    def test_patch_logging_idempotent(self):
        netius.patch_logging()
        netius.patch_logging()

        result = logging.getLevelName(netius.TRACE)

        self.assertEqual(result, "TRACE")

    def test_patch_logging_logger_trace(self):
        netius.patch_logging()

        logger = logging.getLogger("netius.test.trace")

        self.assertTrue(hasattr(logger, "trace"))
        self.assertTrue(callable(logger.trace))

    def test_patch_logging_logger_trace_call(self):
        netius.patch_logging()

        logger = logging.getLogger("netius.test.trace.call")
        logger.setLevel(netius.TRACE)
        records = []
        handler = logging.Handler()
        handler.setLevel(netius.TRACE)
        handler.emit = lambda record: records.append(record)
        logger.addHandler(handler)

        try:
            logger.trace("trace test message")

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].getMessage(), "trace test message")
            self.assertEqual(records[0].levelno, netius.TRACE)
            self.assertEqual(records[0].levelname, "TRACE")
        finally:
            logger.removeHandler(handler)

    def test_patch_logging_logger_trace_filtered(self):
        netius.patch_logging()

        logger = logging.getLogger("netius.test.trace.filtered")
        logger.setLevel(logging.DEBUG)
        records = []
        handler = logging.Handler()
        handler.setLevel(netius.TRACE)
        handler.emit = lambda record: records.append(record)
        logger.addHandler(handler)

        try:
            # the trace message should be filtered since the logger
            # level is set to DEBUG which is above TRACE
            logger.trace("this should be filtered")

            self.assertEqual(len(records), 0)
        finally:
            logger.removeHandler(handler)

    def test_setup_logging(self):
        logger = logging.getLogger()
        handlers = list(logger.handlers)
        level = logger.level

        try:
            del logger.handlers[:]
            log.setup_logging(level="INFO")

            # the level that is asked for is resolved from its name and is
            # the one that the root logger ends up with
            self.assertEqual(logger.level, logging.INFO)

            del logger.handlers[:]
            log.setup_logging(level=logging.ERROR)

            # a level that is already a number is used as it is, with no
            # resolution being attempted for it
            self.assertEqual(logger.level, logging.ERROR)

            del logger.handlers[:]
            log.setup_logging(level="TRACE")

            # the trace level is only nameable once the patching is done,
            # which is the first thing that the setting up takes care of
            self.assertEqual(logger.level, log.TRACE)

            del logger.handlers[:]
            with netius.conf_override("LEVEL", "WARNING"):
                log.setup_logging()

            # with no level given the one of the configuration answers for
            # it, the default of the function being the last resort
            self.assertEqual(logger.level, logging.WARNING)
        finally:
            del logger.handlers[:]
            logger.handlers.extend(handlers)
            logger.setLevel(level)

    def test_trace_before_patch(self):
        # temporarily removes the patched state to simulate a
        # scenario where patch_logging() has not been called yet
        patched = getattr(logging, "_netius_patched", None)
        if patched:
            del logging._netius_patched
        trace_method = getattr(logging.Logger, "trace", None)
        if trace_method:
            del logging.Logger.trace
        try:
            base = netius.Base.__new__(netius.Base)
            base._logging = False
            base.logger = logging.getLogger("netius.test.trace.before")
            base.logger.setLevel(netius.TRACE)
            records = []
            handler = logging.Handler()
            handler.setLevel(netius.TRACE)
            handler.emit = lambda record: records.append(record)
            base.logger.addHandler(handler)

            base.trace("trace before patch")

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].getMessage(), "trace before patch")
            self.assertEqual(records[0].levelno, netius.TRACE)
        finally:
            base.logger.removeHandler(handler)
            if patched:
                logging._netius_patched = patched
            if trace_method:
                logging.Logger.trace = trace_method

    def test_level_trace_before_patch(self):
        # temporarily removes the patched state to simulate a
        # scenario where patch_logging() has not been called yet
        patched = getattr(logging, "_netius_patched", None)
        if patched:
            del logging._netius_patched
        trace_method = getattr(logging.Logger, "trace", None)
        if trace_method:
            del logging.Logger.trace
        try:
            base = netius.Base.__new__(netius.Base)

            result = base._level("TRACE")

            self.assertEqual(result, netius.TRACE)
            self.assertEqual(result, 5)
        finally:
            if patched:
                logging._netius_patched = patched
            if trace_method:
                logging.Logger.trace = trace_method

    def test_level_trace_after_patch(self):
        netius.patch_logging()

        base = netius.Base.__new__(netius.Base)

        result = base._level("TRACE")

        self.assertEqual(result, netius.TRACE)
        self.assertEqual(result, 5)

    def test_level_silent(self):
        base = netius.Base.__new__(netius.Base)

        result = base._level("SILENT")

        self.assertEqual(result, netius.SILENT)

    def test_level_integer(self):
        base = netius.Base.__new__(netius.Base)

        result = base._level(logging.DEBUG)

        self.assertEqual(result, logging.DEBUG)

    def test_level_none(self):
        base = netius.Base.__new__(netius.Base)

        result = base._level(None)

        self.assertEqual(result, None)

    def test_in_signature(self):
        def sample(a, b, secure=None):
            pass

        result = log.in_signature(sample, "secure")

        self.assertEqual(result, True)

    def test_in_signature_missing(self):
        def sample(a, b):
            pass

        result = log.in_signature(sample, "secure")

        self.assertEqual(result, False)

    def test_in_signature_args(self):
        def sample(a, b, secure):
            pass

        result = log.in_signature(sample, "secure")

        self.assertEqual(result, True)

    def _raiser(self):
        raise netius.NetiusError("Unable to build the meta")


class LogstashAPI(object):
    """
    Stand in for the logstash API that keeps the bulks that
    are posted to it, so that they may be asserted.
    """

    def __init__(self):
        self.bulks = []

    def log_bulk(self, messages, tag=None, raise_e=False):
        self.bulks.append((messages, tag, raise_e))


class LogstashErrorAPI(LogstashAPI):
    """
    Variant of the stand in that is never able to post the
    bulk that it is given, raising instead.
    """

    def log_bulk(self, messages, tag=None, raise_e=False):
        LogstashAPI.log_bulk(self, messages, tag=tag, raise_e=raise_e)
        raise netius.NetiusError("Unable to log the bulk")
