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
import json
import shutil
import tempfile
import unittest

import netius

try:
    import unittest.mock as mock
except ImportError:
    mock = None


class ConfigTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_basic(self):
        netius.conf_s("NAME", "name")
        result = netius.conf("NAME")

        self.assertEqual(result, "name")

        result = netius.conf("NAME", cast=str)

        self.assertEqual(result, "name")
        self.assertEqual(type(result), str)

        result = netius.conf("NAME", cast="str")

        self.assertEqual(result, "name")
        self.assertEqual(type(result), str)

        netius.conf_s("AGE", "10")
        result = netius.conf("AGE", cast=int)

        self.assertEqual(result, 10)
        self.assertEqual(type(result), int)

        result = netius.conf("AGE", cast="int")

        self.assertEqual(result, 10)
        self.assertEqual(type(result), int)

        result = netius.conf("AGE", cast=str)

        self.assertEqual(result, "10")
        self.assertEqual(type(result), str)

        result = netius.conf("HEIGHT")

        self.assertEqual(result, None)

    def test_none(self):
        netius.conf_s("AGE", None)
        result = netius.conf("AGE", cast=int)

        self.assertEqual(result, None)

        result = netius.conf("HEIGHT", cast=int)

        self.assertEqual(result, None)

    def test_conf_prefix(self):
        ctx = self._ctx(NETIUS_FIRST="first", NETIUS_SECOND="second", OTHER="other")

        result = netius.config.conf_prefix("NETIUS_", ctx=ctx)

        # only the names that start with the prefix are part of the result,
        # the value of each of them being kept as it is
        self.assertEqual(result, dict(NETIUS_FIRST="first", NETIUS_SECOND="second"))

        self.assertEqual(netius.config.conf_prefix("MISSING_", ctx=ctx), {})

    def test_conf_suffix(self):
        ctx = self._ctx(FIRST_PORT="80", SECOND_PORT="443", FIRST_HOST="localhost")

        result = netius.config.conf_suffix("_PORT", ctx=ctx)

        self.assertEqual(result, dict(FIRST_PORT="80", SECOND_PORT="443"))

        self.assertEqual(netius.config.conf_suffix("_MISSING", ctx=ctx), {})

    def test_conf_r(self):
        ctx = self._ctx(NAME="name")

        netius.config.conf_r("NAME", ctx=ctx)

        self.assertEqual(netius.config.conf("NAME", ctx=ctx), None)

        # the removal of a name that is not set is a no operation, instead
        # of a failure over the name that is missing
        self.assertEqual(netius.config.conf_r("NAME", ctx=ctx), None)

    def test_conf_d(self):
        ctx = self._ctx(NAME="name")

        result = netius.config.conf_d(ctx=ctx)

        # the map that is given back is the one that backs the context, so
        # that a change to it is visible through the accessors
        self.assertEqual(result, dict(NAME="name"))

        result["AGE"] = "10"

        self.assertEqual(netius.config.conf("AGE", ctx=ctx), "10")

    def test_conf_ctx(self):
        ctx = netius.config.conf_ctx()

        self.assertEqual(ctx["configs"], {})

        # the files that have been loaded are kept in a sequence, as the
        # loading of one appends to it and removes from it
        self.assertEqual(ctx["config_f"], [])
        self.assertEqual(type(ctx["config_f"]), list)

    def test_conf_override(self):
        netius.conf_s("NAME", "name")

        with netius.conf_override("NAME", "other"):
            self.assertEqual(netius.conf("NAME"), "other")

        # the value that was there before is put back in place once the
        # override comes to an end
        self.assertEqual(netius.conf("NAME"), "name")

        netius.config.conf_r("MISSING")

        with netius.conf_override("MISSING", "value"):
            self.assertEqual(netius.conf("MISSING"), "value")

        # a name that was not set is removed instead of being restored,
        # so that the override leaves nothing behind
        self.assertEqual(netius.conf("MISSING"), None)
        self.assertEqual("MISSING" in netius.config.conf_d(), False)

    def test_load_file(self):
        ctx = netius.config.conf_ctx()
        self._store("netius.json", json.dumps(dict(NAME="name", AGE="10")))

        netius.config.load_file(name="netius.json", path=self.base, ctx=ctx)

        self.assertEqual(netius.config.conf("NAME", ctx=ctx), "name")
        self.assertEqual(netius.config.conf("AGE", cast=int, ctx=ctx), 10)

        # the file that was loaded is remembered, so that the origin of
        # the values may be known afterwards
        self.assertEqual(len(ctx["config_f"]), 1)

        netius.config.load_file(name="netius.json", path=self.base, ctx=ctx)

        # a file that is loaded again is moved to the end of the sequence
        # instead of being named twice in it
        self.assertEqual(len(ctx["config_f"]), 1)

    def test_load_file_missing(self):
        ctx = netius.config.conf_ctx()

        netius.config.load_file(name="missing.json", path=self.base, ctx=ctx)

        # neither a file that is not there nor an empty one carries any
        # value, so both of them leave the context untouched
        self.assertEqual(ctx["configs"], {})
        self.assertEqual(ctx["config_f"], [])

        self._store("empty.json", "")

        netius.config.load_file(name="empty.json", path=self.base, ctx=ctx)

        self.assertEqual(ctx["configs"], {})

    def test_load_file_includes(self):
        ctx = netius.config.conf_ctx()
        self._store("included.json", json.dumps(dict(INCLUDED="included")))
        self._store(
            "netius.json", json.dumps({"$import": "included.json", "NAME": "name"})
        )

        netius.config.load_file(name="netius.json", path=self.base, ctx=ctx)

        # the file that is imported is loaded into the very same context,
        # instead of reaching the global configuration
        self.assertEqual(netius.config.conf("INCLUDED", ctx=ctx), "included")
        self.assertEqual(netius.conf("INCLUDED"), None)

        # the name that names the imports is not a configuration value of
        # its own, so it is left out of the result
        self.assertEqual("$import" in ctx["configs"], False)
        self.assertEqual(netius.config.conf("NAME", ctx=ctx), "name")

    def test_load_dot_env(self):
        if mock == None:
            self.skipTest("Skipping test: mock unavailable")

        mock_data = mock.mock_open(
            read_data=b"#This is a comment\nAGE=10\nNAME=colony\n"
        )

        with mock.patch("os.path.exists", return_value=True), mock.patch(
            "builtins.open", mock_data, create=True
        ) as mock_open:
            ctx = dict(configs={}, config_f=[])

            netius.config.load_dot_env(".env", "utf-8", ctx)

            result = netius.conf("AGE", cast=int)
            self.assertEqual(type(result), int)
            self.assertEqual(result, 10)

            result = netius.conf("AGE", cast=str)

            self.assertEqual(result, "10")
            self.assertEqual(type(result), str)

            result = netius.conf("HEIGHT", cast=int)
            self.assertEqual(result, None)

            self.assertEqual(len(ctx["configs"]), 2)

            self.assertEqual(mock_open.return_value.close.call_count, 1)

    def test_load_dot_env_file(self):
        ctx = netius.config.conf_ctx()
        path = self._store(
            ".env",
            "# a comment\n\nNAME=name\nQUOTED=\"quoted\"\nSINGLE='single'\n",
        )

        netius.config.load_dot_env(name=path, ctx=ctx)

        # the comment and the empty line carry no value, only the three
        # assignments taking part in the result
        self.assertEqual(len(ctx["configs"]), 3)
        self.assertEqual(netius.config.conf("NAME", ctx=ctx), "name")

        # the quotes that surround a value are part of the notation and
        # not of the value, so they are stripped from it
        self.assertEqual(netius.config.conf("QUOTED", ctx=ctx), "quoted")
        self.assertEqual(netius.config.conf("SINGLE", ctx=ctx), "single")

        self.assertEqual(len(ctx["config_f"]), 1)

        netius.config.load_dot_env(name=path, ctx=ctx)

        self.assertEqual(len(ctx["config_f"]), 1)

    def test_load_dot_env_missing(self):
        ctx = netius.config.conf_ctx()

        netius.config.load_dot_env(name=os.path.join(self.base, ".missing"), ctx=ctx)

        self.assertEqual(ctx["configs"], {})

        path = self._store(".empty", "")

        netius.config.load_dot_env(name=path, ctx=ctx)

        self.assertEqual(ctx["configs"], {})

    def test_load_env(self):
        ctx = netius.config.conf_ctx()
        original = os.environ.get("NETIUS_TEST_VALUE", None)
        original_i = os.environ.get("$import", None)
        os.environ["NETIUS_TEST_VALUE"] = "value"
        os.environ["$import"] = "missing.json"

        try:
            netius.config.load_env(ctx=ctx)
        finally:
            self._restore("NETIUS_TEST_VALUE", original)
            self._restore("$import", original_i)

        # the environment is carried into the context as it is, the name
        # that names the imports being the only one that is refused
        self.assertEqual(netius.config.conf("NETIUS_TEST_VALUE", ctx=ctx), "value")
        self.assertEqual("$import" in ctx["configs"], False)

    def test_get_homes(self):
        homes = netius.config.HOMES
        original = os.environ.get("HOMES", None)

        try:
            netius.config.HOMES = []
            os.environ["HOMES"] = "/first;/second"

            # the environment names the homes directly, taking precedence
            # over both the default one and the file
            self.assertEqual(netius.config.get_homes(), ["/first", "/second"])

            netius.config.HOMES = []
            self._restore("HOMES", None)

            result = netius.config.get_homes(
                file_path=os.path.join(self.base, "missing")
            )

            # with no file to redirect them the home of the user is the
            # only one that answers for the configuration
            self.assertEqual(result, [self._normalize("~")])

            first = os.path.join(self.base, "first")
            second = os.path.join(self.base, "second")
            path = self._store(".home", "%s\n\n%s\n" % (first, second))

            netius.config.HOMES = []

            result = netius.config.get_homes(file_path=path)

            # the file replaces the default home with the ones that it
            # names, the empty line of it being skipped
            self.assertEqual(result, [self._normalize(first), self._normalize(second)])

            netius.config.HOMES = []

            result = netius.config.get_homes(file_path=path, force_default=True)

            # with the default forced it is kept in front of the ones of
            # the file, instead of being replaced by them
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0], self._normalize("~"))

            # the value is remembered, so that the file is read only once
            # whatever the number of times that it is asked for
            self.assertEqual(netius.config.get_homes(), result)
        finally:
            netius.config.HOMES = homes
            self._restore("HOMES", original)

    def test__is_valid(self):
        self.assertEqual(netius.config._is_valid("NAME"), True)

        # the names that name the imports are directives and not values,
        # so none of them is a valid configuration name
        for name in netius.config.IMPORT_NAMES:
            self.assertEqual(netius.config._is_valid(name), False)

    def _ctx(self, **kwargs):
        ctx = netius.config.conf_ctx()
        ctx["configs"].update(kwargs)
        return ctx

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents.encode("utf-8"))
        finally:
            file.close()
        return path

    def _normalize(self, path):
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        path = os.path.normpath(path)
        return path

    def _restore(self, name, value):
        if value == None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
