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
import unittest

import netius


class LogTest(unittest.TestCase):

    def test_trace_value(self):
        self.assertEqual(netius.TRACE, 5)
        self.assertEqual(netius.TRACE, logging.DEBUG - 5)

    def test_trace_below_debug(self):
        self.assertTrue(netius.TRACE < logging.DEBUG)

    def test_patch_logging(self):
        netius.patch_logging()

        result = logging.getLevelName(netius.TRACE)

        self.assertEqual(result, "TRACE")

    def test_patch_logging_idempotent(self):
        netius.patch_logging()
        netius.patch_logging()

        result = logging.getLevelName(netius.TRACE)

        self.assertEqual(result, "TRACE")

    def test_patch_logging_logger_trace(self):
        netius.patch_logging()

        logger = logging.getLogger("netius.test.trace")

        self.assertTrue(hasattr(logger, "trace"))

    def test_patch_logging_logger_trace_call(self):
        netius.patch_logging()

        logger = logging.getLogger("netius.test.trace.call")
        logger.setLevel(netius.TRACE)
        handler = logging.StreamHandler()
        handler.setLevel(netius.TRACE)
        logger.addHandler(handler)

        logger.trace("trace test message")

    def test_silent_value(self):
        self.assertEqual(netius.SILENT, logging.CRITICAL + 1)
