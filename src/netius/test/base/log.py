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

import logging
import logging.handlers
import unittest

import netius

import netius.base.log


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

    def test_logstash_handler_emit_no_api(self):
        handler = netius.LogstashHandler(api=None)
        record = logging.LogRecord("test", logging.INFO, "", 0, "message", (), None)

        handler.emit(record)

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_flush_no_api(self):
        handler = netius.LogstashHandler(api=None)

        handler.flush()

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_flush_empty(self):
        handler = netius.LogstashHandler(api=None)

        handler.flush(force=True)

        self.assertEqual(len(handler.messages), 0)

    def test_logstash_handler_is_ready(self):
        result = netius.LogstashHandler.is_ready()

        self.assertEqual(type(result), bool)

    def test_rotating_handler(self):
        handler = netius.rotating_handler(path="/dev/null", max_bytes=1024, max_log=3)

        self.assertEqual(type(handler), logging.handlers.RotatingFileHandler)
        self.assertEqual(handler.maxBytes, 1024)
        self.assertEqual(handler.backupCount, 3)

        handler.close()

    def test_rotating_handler_defaults(self):
        handler = netius.rotating_handler(path="/dev/null")

        self.assertEqual(handler.maxBytes, 1048576)
        self.assertEqual(handler.backupCount, 5)

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

        result = netius.base.log.in_signature(sample, "secure")

        self.assertEqual(result, True)

    def test_in_signature_missing(self):
        def sample(a, b):
            pass
            
        result = logging.log.in_signature(sample, "secure")

        self.assertFalse(result)

    def test_in_signature_args(self):
        def sample(a, b, secure):
            pass

        result = netius.base.log.in_signature(sample, "secure")

        self.assertEqual(result, True)
