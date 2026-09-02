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
import sys
import time
import array
import shutil
import tempfile
import itertools
import unittest

from netius.base import legacy


class LegacyTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.base = tempfile.mkdtemp()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        shutil.rmtree(self.base)

    def test_with_meta(self):
        class Meta(type):
            pass

        result = legacy.with_meta(Meta, dict)

        # the class that is built carries the metaclass and the bases
        # that were asked for, whatever the interpreter
        self.assertEqual(type(result), Meta)
        self.assertEqual(result.__bases__, (dict,))

    def test_eager(self):
        result = legacy.eager(iter([1, 2, 3]))

        self.assertEqual(list(result), [1, 2, 3])

        # the materialization is only required under the newer runtimes,
        # where the views are lazy, the older ones are already eager
        if legacy.PYTHON_3:
            self.assertEqual(legacy.eager([1, 2, 3]), [1, 2, 3])
            self.assertEqual(type(legacy.eager(iter([1]))), list)
        else:
            self.assertEqual(legacy.eager([1, 2, 3]), [1, 2, 3])

    def test_iteritems(self):
        result = legacy.iteritems(dict(first=1))

        # the pairs of the map are given back whatever the shape of the
        # value that carries them, which changes with the interpreter
        self.assertEqual(list(result), [("first", 1)])

    def test_iterkeys(self):
        result = legacy.iterkeys(dict(first=1))

        self.assertEqual(list(result), ["first"])

    def test_itervalues(self):
        result = legacy.itervalues(dict(first=1))

        self.assertEqual(list(result), [1])

    def test_items(self):
        result = legacy.items(dict(first=1))

        self.assertEqual(list(result), [("first", 1)])

    def test_keys(self):
        result = legacy.keys(dict(first=1))

        # the keys are materialized into a sequence, so that they may be
        # indexed, which the view of the newer runtimes does not allow
        self.assertEqual(result[0], "first")

    def test_values(self):
        result = legacy.values(dict(first=1))

        self.assertEqual(result[0], 1)

    def test_xrange(self):
        self.assertEqual(list(legacy.xrange(5)), [0, 1, 2, 3, 4])
        self.assertEqual(list(legacy.xrange(1, 5)), [1, 2, 3, 4])
        self.assertEqual(list(legacy.xrange(1, 10, 2)), [1, 3, 5, 7, 9])

    def test_xrange_zero(self):
        # a stop of zero is a valid bound and not the absence of one, so
        # the sequence must be an empty one instead of counting up to the
        # value that has been given as the start
        self.assertEqual(list(legacy.xrange(5, 0)), [])
        self.assertEqual(
            list(legacy.xrange(10, 0, -1)), [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        )

    def test_range(self):
        self.assertEqual(legacy.range(5), [0, 1, 2, 3, 4])
        self.assertEqual(legacy.range(1, 5), [1, 2, 3, 4])
        self.assertEqual(legacy.range(1, 10, 2), [1, 3, 5, 7, 9])

    def test_range_zero(self):
        self.assertEqual(legacy.range(5, 0), [])
        self.assertEqual(legacy.range(10, 0, -1), [10, 9, 8, 7, 6, 5, 4, 3, 2, 1])

    def test_ord(self):
        self.assertEqual(legacy.ord(b"A"), 65)

        # an integer is already the ordinal of a byte under the newer
        # runtimes, where indexing a sequence gives one back
        if legacy.PYTHON_3:
            self.assertEqual(legacy.ord(65), 65)

    def test_chr(self):
        # the value of a single byte is a byte sequence and not a string,
        # so that it may be joined with the other ones
        self.assertEqual(legacy.chr(65), b"A")

    def test_chri(self):
        # the integer flavour keeps the ordinal as it is under the newer
        # runtimes, where indexing a byte sequence already gives one
        if legacy.PYTHON_3:
            self.assertEqual(legacy.chri(65), 65)
        else:
            self.assertEqual(legacy.chri(65), "A")

    def test_bytes(self):
        result = legacy.bytes("value")

        self.assertEqual(result, b"value")
        self.assertEqual(legacy.bytes(b"value"), b"value")

    def test_str(self):
        result = legacy.str(b"value")

        self.assertEqual(result, "value")
        self.assertEqual(legacy.str("value"), "value")

    def test_u(self):
        result = legacy.u(b"value", force=True)

        self.assertEqual(result, "value")
        self.assertEqual(legacy.u(None, force=True), None)
        self.assertEqual(legacy.u("value", force=True), "value")

        # the decoding is a no operation under the newer runtimes, where a
        # native string is already a unicode one, unless it's forced
        if legacy.PYTHON_3:
            self.assertEqual(legacy.u(b"value"), b"value")
        else:
            self.assertEqual(legacy.u(b"value"), "value")

    def test_ascii(self):
        # a byte sequence that is not representable under the target
        # encoding is replaced instead of raising, as the operation is
        # meant to be used for presentation only
        result = legacy.ascii(b"\xff")

        self.assertEqual(legacy.is_string(result), True)

    def test_orderable(self):
        result = legacy.orderable((1, "first"))

        self.assertEqual(result[0], 1)

    def test_is_str(self):
        self.assertEqual(legacy.is_str("value"), True)
        self.assertEqual(legacy.is_str(1), False)

        # a byte sequence is only told apart from a native string under the
        # newer runtimes, as under the older ones they are the same type
        if legacy.PYTHON_3:
            self.assertEqual(legacy.is_str(b"value"), False)
        else:
            self.assertEqual(legacy.is_str(b"value"), True)

    def test_is_unicode(self):
        self.assertEqual(legacy.is_unicode(b"value"), False)
        self.assertEqual(legacy.is_unicode(1), False)

        # a value that was decoded is a text one whatever the runtime,
        # which is what the operation is meant to tell
        self.assertEqual(legacy.is_unicode(legacy.u("value", force=True)), True)

        # a native string is only a text one under the newer runtimes,
        # the older ones keeping the two kinds of them apart
        if legacy.PYTHON_3:
            self.assertEqual(legacy.is_unicode("value"), True)
        else:
            self.assertEqual(legacy.is_unicode("value"), False)

    def test_is_bytes(self):
        self.assertEqual(legacy.is_bytes(b"value"), True)
        self.assertEqual(legacy.is_bytes(1), False)

        if legacy.PYTHON_3:
            self.assertEqual(legacy.is_bytes("value"), False)
        else:
            self.assertEqual(legacy.is_bytes("value"), True)

    def test_is_string(self):
        self.assertEqual(legacy.is_string("value"), True)
        self.assertEqual(legacy.is_string(1), False)

        if legacy.PYTHON_3:
            self.assertEqual(legacy.is_string(b"value"), False)
        else:
            self.assertEqual(legacy.is_string(b"value"), True)

        # the complete verification also accepts the byte based sequences
        # as strings, which is required for the data coming from a socket
        self.assertEqual(legacy.is_string(b"value", all=True), True)
        self.assertEqual(legacy.is_string(1, all=True), False)

    def test_is_generator(self):
        def generator():
            yield 1

        self.assertEqual(legacy.is_generator(generator()), True)
        self.assertEqual(legacy.is_generator([1]), False)

        # a chain of iterators is taken as a generator as well, as that
        # is one of the ways lazy sequences are built
        self.assertEqual(legacy.is_generator(itertools.chain([1], [2])), True)

    def test_is_async_generator(self):
        # a plain generator is not an asynchronous one, which is what
        # tells the two kinds of them apart
        self.assertEqual(legacy.is_async_generator(self._values()), False)
        self.assertEqual(legacy.is_async_generator("value"), False)

    def test_is_unittest(self):
        # the name is looked for in the lines of the stack, so one that
        # is part of this very call is always found
        self.assertEqual(legacy.is_unittest(name="is_unittest"), True)

        code = compile("result = legacy.is_unittest(name='invalid')", "<test>", "exec")
        global_vars = dict(legacy=legacy)

        exec(code, global_vars)

        # the frame of an evaluated caller has no source on the disk to be
        # looked at, so it should be skipped over instead of raising
        self.assertEqual(global_vars["result"], False)

    def test_execfile(self):
        path = self._store("module.py", "value = 1\nother = value + 1\n")
        global_vars = dict()

        legacy.execfile(path, global_vars)

        # the file is run against the map that is given, so that the
        # names that it defines end up in it
        self.assertEqual(global_vars["value"], 1)
        self.assertEqual(global_vars["other"], 2)

        global_vars = dict()
        local_vars = dict()

        legacy.execfile(path, global_vars, local_vars=local_vars)

        # with a map of its own for the local names those are the ones
        # that receive what the file defines
        self.assertEqual(local_vars["value"], 1)
        self.assertEqual("value" in global_vars, False)

    def test_walk(self):
        os.mkdir(os.path.join(self.base, "first"))
        os.mkdir(os.path.join(self.base, "second"))
        self._store("file.txt", "contents")

        visited = []

        def visit(arg, root, names):
            arg.append((os.path.basename(root), sorted(names)))

        legacy.walk(self.base, visit, visited)

        # every directory of the tree is visited with the names that it
        # holds, the root of it being the first one
        self.assertEqual(visited[0][1], ["file.txt", "first", "second"])
        self.assertEqual(len(visited), 3)

    def test_getargspec(self):
        def sample(first, second=1, *args, **kwargs):
            pass

        result = legacy.getargspec(sample)

        # only the four values of the older specification are kept, so
        # that the shape of it is the same under both runtimes
        self.assertEqual(result[0], ["first", "second"])
        self.assertEqual(result[1], "args")
        self.assertEqual(result[2], "kwargs")
        self.assertEqual(result[3], (1,))

    def test_has_module(self):
        self.assertEqual(legacy.has_module("unittest"), True)
        self.assertEqual(legacy.has_module("netius_missing_module"), False)

        # a module whose parent is not there is reported as absent as
        # well, instead of the failure of the parent reaching the caller
        self.assertEqual(legacy.has_module("netius_missing_module.sub"), False)

    def test_new_module(self):
        result = legacy.new_module("sample")

        # the module that is built is an empty one carrying only the
        # name that was asked for it
        self.assertEqual(result.__name__, "sample")

    def test_reduce(self):
        result = legacy.reduce(lambda first, second: first + second, [1, 2, 3])

        self.assertEqual(result, 6)

    def test_reload(self):
        self._store("sample_reload.py", "value = 1\n")
        dont_write = sys.dont_write_bytecode
        sys.path.insert(0, self.base)

        # keeps the bytecode out of the way, as the oldest of the runtimes
        # tells a cached one apart by its date alone, which the rewriting
        # of the source right after is not guaranteed to move
        sys.dont_write_bytecode = True

        try:
            import sample_reload

            self.assertEqual(sample_reload.value, 1)

            self._store("sample_reload.py", "value = 2\nother = 3\n")

            result = legacy.reload(sample_reload)

            # the reloading happens in place, so the module that comes
            # back is the very same one, carrying the new values
            self.assertEqual(result, sample_reload)
            self.assertEqual(sample_reload.value, 2)
            self.assertEqual(sample_reload.other, 3)
        finally:
            sys.dont_write_bytecode = dont_write
            sys.path.remove(self.base)
            sys.modules.pop("sample_reload", None)

    def test_unichr(self):
        self.assertEqual(legacy.unichr(65), "A")

    def test_build_opener(self):
        opener = legacy.build_opener()

        # the opener is the one of the runtime, which is only asked for
        # the interface that is used to run a request
        self.assertEqual(hasattr(opener, "open"), True)

    def test_to_timestamp(self):
        date_time = legacy.to_datetime(0)
        result = legacy.to_timestamp(date_time)

        # the conversion is a reversible one, so that a timestamp that is
        # turned into a date may be turned back into the very same value
        self.assertEqual(result, 0)

    def test_utcfromtimestamp(self):
        result = legacy.utcfromtimestamp(0)

        self.assertEqual(result.year, 1970)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def test_to_datetime(self):
        result = legacy.to_datetime(0)

        # the epoch is the reference of the conversion and the value is
        # a naive one, with no zone attached to it
        self.assertEqual(result.year, 1970)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.tzinfo, None)

        # the two conversions are the reverse of each other, so a value
        # that goes through both is the one that was given
        self.assertEqual(legacy.to_timestamp(legacy.to_datetime(86400.0)), 86400.0)

    def test_utc_now(self):
        result = legacy.utc_now()

        # the current time is a naive value as well, kept close to the
        # one that the conversion of the epoch based value gives
        self.assertEqual(result.tzinfo, None)
        self.assertEqual(abs((legacy.to_timestamp(result)) - time.time()) < 60.0, True)

    def test_urlparse(self):
        result = legacy.urlparse("http://netius.hive.pt:8080/path?first=1")

        self.assertEqual(result.scheme, "http")
        self.assertEqual(result.netloc, "netius.hive.pt:8080")
        self.assertEqual(result.path, "/path")
        self.assertEqual(result.query, "first=1")

    def test_urlunparse(self):
        result = legacy.urlunparse(
            ("http", "netius.hive.pt", "/path", "", "first=1", "")
        )

        self.assertEqual(result, "http://netius.hive.pt/path?first=1")

    def test_parse_qs(self):
        result = legacy.parse_qs("first=1&second=2&second=3")

        # a name that shows up more than once carries every one of its
        # values, which is why each of them is a sequence
        self.assertEqual(result, dict(first=["1"], second=["2", "3"]))

    def test_quote(self):
        self.assertEqual(legacy.quote("a b"), "a%20b")
        self.assertEqual(legacy.unquote("a%20b"), "a b")

    def test_quote_plus(self):
        self.assertEqual(legacy.quote_plus("a b"), "a+b")
        self.assertEqual(legacy.unquote_plus("a+b"), "a b")

    def test_unquote(self):
        self.assertEqual(legacy.unquote("hello%20world"), "hello world")

        # the plus sign is only a space under the form notation, so the
        # plain unquoting keeps it as it is
        self.assertEqual(legacy.unquote("hello+world"), "hello+world")

    def test_unquote_plus(self):
        self.assertEqual(legacy.unquote_plus("hello+world"), "hello world")
        self.assertEqual(legacy.unquote_plus("hello%20world"), "hello world")

    def test_cmp_to_key(self):
        values = [(2, "second"), (1, "first")]

        values.sort(**legacy.cmp_to_key(lambda first, second: first[0] - second[0]))

        # the comparison is turned into the keyword arguments that the
        # sorting of the runtime expects, whichever they are
        self.assertEqual(values, [(1, "first"), (2, "second")])

    def test_tobytes(self):
        value = array.array("B", [65, 66, 67])

        self.assertEqual(legacy.tobytes(value), b"ABC")

    def test_tostring(self):
        value = array.array("B", [65, 66, 67])

        # the two names are the same operation, kept apart only because
        # the runtimes disagree on how to call it
        self.assertEqual(legacy.tostring(value), b"ABC")

    def test_string_io(self):
        file = legacy.StringIO()

        try:
            file.write("value")
            self.assertEqual(file.getvalue(), "value")
        finally:
            file.close()

        self.assertEqual(legacy.StringIO("value").read(), "value")

    def test_bytes_io(self):
        file = legacy.BytesIO()

        try:
            file.write(b"value")
            self.assertEqual(file.getvalue(), b"value")
        finally:
            file.close()

        self.assertEqual(legacy.BytesIO(b"value").read(), b"value")

    def test_urlencode(self):
        result = legacy.urlencode(dict(first="1"))

        self.assertEqual(result, "first=1")

    def _store(self, name, contents):
        path = os.path.join(self.base, name)
        file = open(path, "wb")
        try:
            file.write(contents.encode("utf-8"))
        finally:
            file.close()
        return path

    def _values(self):
        yield 1
        yield 2
