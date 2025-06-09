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

import subprocess
import sys
import unittest


class StubsTest(unittest.TestCase):
    MODULES = [
        "netius.base.agent",
        "netius.base.client",
        "netius.base.common",
        "netius.base.container",
        "netius.base.observer",
        "netius.base.poll",
        "netius.base.server",
        "netius.base.service",
        "netius.base.stream",
        "netius.base.util",
    ]

    def _run_stubtest(self, module: str) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy.stubtest",
                module,
                "--mypy-config-file",
                "/dev/null",
                "--ignore-missing-stub",
                "--allowlist",
                "/dev/null",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_stubtest(self):
        for module in self.MODULES:
            self._run_stubtest(module)
