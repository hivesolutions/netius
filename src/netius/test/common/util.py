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
import shutil
import tempfile
import unittest

import netius.common


class UtilTest(unittest.TestCase):

    def test_cstring(self):
        # the value is cut at the first of the null bytes, which is what
        # ends a string under the C conventions
        self.assertEqual(netius.common.cstring("value\0rest"), "value")

        # a value that carries no null byte at all is already a complete
        # one, so it is given back as it is
        self.assertEqual(netius.common.cstring("value"), "value")
        self.assertEqual(netius.common.cstring(""), "")

    def test_is_ip4(self):
        result = netius.common.is_ip4("127.0.0.1")
        self.assertEqual(result, True)

        result = netius.common.is_ip4("172.16.0.0/16")
        self.assertEqual(result, False)

    def test_is_ip4_invalid(self):
        # every one of the four parts of an address stands for a single
        # byte, so neither a negative nor a larger value names one
        self.assertEqual(netius.common.is_ip4("192.168.1.-1"), False)
        self.assertEqual(netius.common.is_ip4("192.168.1.256"), False)
        self.assertEqual(netius.common.is_ip4("192.168.1.value"), False)

    def test_is_ip6(self):
        result = netius.common.is_ip6("::1")
        self.assertEqual(result, True)

        result = netius.common.is_ip6("127.0.0.1")
        self.assertEqual(result, False)

    def test_assert_ip4(self):
        allowed = ("127.0.0.1", "192.168.0.1", "172.16.0.0/16")

        result = netius.common.assert_ip4("127.0.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("192.168.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("192.168.0.2", allowed)
        self.assertEqual(result, False)

        result = netius.common.assert_ip4("172.16.0.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("172.16.1.1", allowed)
        self.assertEqual(result, True)

        result = netius.common.assert_ip4("172.17.0.1", allowed)
        self.assertEqual(result, False)

    def test_in_subnet_ip4(self):
        result = netius.common.in_subnet_ip4("127.0.0.1", "127.0.0.0/24")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.2", "127.0.0.0/24")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.1", "127.0.0.0/31")
        self.assertEqual(result, True)

        result = netius.common.in_subnet_ip4("127.0.0.2", "127.0.0.0/31")
        self.assertEqual(result, False)

        result = netius.common.in_subnet_ip4("127.0.0.1", "128.0.0.0/24")
        self.assertEqual(result, False)

    def test_addr_to_ip4(self):
        result = netius.common.addr_to_ip4(2130706433)
        self.assertEqual(result, "127.0.0.1")

        result = netius.common.addr_to_ip4(3232235521)
        self.assertEqual(result, "192.168.0.1")

        result = netius.common.addr_to_ip4(3627733678)
        self.assertEqual(result, "216.58.210.174")

    def test_addr_to_ip6(self):
        result = netius.common.addr_to_ip6(1)
        self.assertEqual(result, "0000:0000:0000:0000:0000:0000:0000:0001")

        result = netius.common.addr_to_ip6(338288524927261089654018896841347694593)
        self.assertEqual(result, "fe80:0000:0000:0000:0000:0000:0000:0001")

        result = netius.common.addr_to_ip6(55827987829222246039918918277097594894)
        self.assertEqual(result, "2a00:1450:4003:0801:0000:0000:0000:200e")

    def test_bytes_to_integer(self):
        result = netius.common.bytes_to_integer(b"Hello World")
        self.assertEqual(result, 87521618088882533792115812)

    def test_integer_to_bytes(self):
        result = netius.common.integer_to_bytes(87521618088882533792115812)
        self.assertEqual(result, b"Hello World")

    def test_integer_to_bytes_length(self):
        result = netius.common.integer_to_bytes(1, length=4)

        # the length that is asked for is filled with the bytes that are
        # missing, which are placed in front of the value
        self.assertEqual(result, b"\x00\x00\x00\x01")

        # a length that is smaller than the one of the value changes
        # nothing, as no byte of it may be dropped
        self.assertEqual(netius.common.integer_to_bytes(256, length=1), b"\x01\x00")

    def test_integer_to_bytes_invalid(self):
        # only an integer carries the bytes that the conversion reads,
        # so a value of another kind is refused
        self.assertRaises(netius.DataError, lambda: netius.common.integer_to_bytes("1"))

    def test_bytes_to_integer_invalid(self):
        # only a byte sequence carries the value that the conversion
        # reads, so one of another kind is refused
        self.assertRaises(netius.DataError, lambda: netius.common.bytes_to_integer(1))

        # a text value is not a byte one either, whichever of the two
        # runtimes is the one that runs the case
        self.assertRaises(
            netius.DataError,
            lambda: netius.common.bytes_to_integer(netius.legacy.u("value")),
        )

    def test_hostname(self):
        result = netius.common.hostname()

        # the name of the machine is a string of its own, whatever the
        # value that the runtime gives for it
        self.assertEqual(netius.legacy.is_string(result), True)
        self.assertEqual(len(result) > 0, True)

    def test_is_sub_path(self):
        base = os.path.abspath(os.path.join(os.sep, "srv", "ftp"))

        # the base path itself and anything below it are contained, the
        # separator being what tells a child apart from a sibling whose
        # name only starts like the base path
        self.assertEqual(netius.common.is_sub_path(base, base), True)
        self.assertEqual(
            netius.common.is_sub_path(base, os.path.join(base, "file.txt")), True
        )
        self.assertEqual(
            netius.common.is_sub_path(base, os.path.join(base, "sub", "file.txt")),
            True,
        )
        self.assertEqual(netius.common.is_sub_path(base, os.path.dirname(base)), False)
        self.assertEqual(netius.common.is_sub_path(base, base + "-backup"), False)
        self.assertEqual(
            netius.common.is_sub_path(base, os.path.join(base + "-backup", "file.txt")),
            False,
        )
        self.assertEqual(
            netius.common.is_sub_path(base, os.path.join(os.sep, "etc", "passwd")),
            False,
        )

        # the root of the file system contains every path there is
        root = os.path.abspath(os.sep)
        self.assertEqual(
            netius.common.is_sub_path(root, os.path.join(root, "etc", "passwd")),
            True,
        )

    def test_is_sub_path_missing(self):
        base = tempfile.mkdtemp()

        try:
            # a path that is not there yet (the one of a file that is about
            # to be written) is judged by its name alone, as there is no
            # link in it to be resolved
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "new.txt")), True
            )
            self.assertEqual(
                netius.common.is_sub_path(
                    base, os.path.join(base, "missing", "new.txt")
                ),
                True,
            )
        finally:
            shutil.rmtree(base)

    def test_is_sub_path_link(self):
        base = tempfile.mkdtemp()
        outside = tempfile.mkdtemp()

        try:
            self._store(os.path.join(outside, "secret.txt"))
            self._store(os.path.join(base, "file.txt"))
            os.makedirs(os.path.join(base, "sub"))
            self._link(
                os.path.join(outside, "secret.txt"), os.path.join(base, "link.txt")
            )
            self._link(os.path.join(base, "file.txt"), os.path.join(base, "inside.txt"))
            self._link(outside, os.path.join(base, "sub", "link"))
            self._link(os.pardir, os.path.join(base, "sub", "up"))

            # a link is judged by its target, so one that leads out of the
            # base path is not contained while one that stays under it is
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "link.txt")),
                False,
            )
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "inside.txt")),
                True,
            )

            # the link may sit anywhere below the base path, what follows
            # it in the path being reached through its target
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "sub", "link")),
                False,
            )
            self.assertEqual(
                netius.common.is_sub_path(
                    base, os.path.join(base, "sub", "link", "secret.txt")
                ),
                False,
            )

            # a link that climbs and yet lands under the base path leads
            # nowhere it should not, so what is reached through it counts
            self.assertEqual(
                netius.common.is_sub_path(
                    base, os.path.join(base, "sub", "up", "file.txt")
                ),
                True,
            )
            self.assertEqual(
                netius.common.is_sub_path(
                    base, os.path.join(base, "sub", "up", "link.txt")
                ),
                False,
            )

            # the operator may publish through a link on purpose, in which
            # case the name under the base path is enough
            self.assertEqual(
                netius.common.is_sub_path(
                    base, os.path.join(base, "link.txt"), follow_links=True
                ),
                True,
            )
        finally:
            shutil.rmtree(base)
            shutil.rmtree(outside)

    def test_is_sub_path_base_link(self):
        target = tempfile.mkdtemp()
        outside = tempfile.mkdtemp()
        base = target + "-link"

        try:
            self._link(target, base)
            self._store(os.path.join(target, "file.txt"))
            self._store(os.path.join(outside, "secret.txt"))
            self._link(
                os.path.join(outside, "secret.txt"), os.path.join(target, "link.txt")
            )

            # a base path that is itself reached through a link resolves the
            # same way on both sides, so what sits under it is contained
            # while a link out of it is still refused
            self.assertEqual(netius.common.is_sub_path(base, base), True)
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "file.txt")), True
            )
            self.assertEqual(
                netius.common.is_sub_path(base, os.path.join(base, "link.txt")),
                False,
            )
        finally:
            os.remove(base)
            shutil.rmtree(target)
            shutil.rmtree(outside)

    def test_size_round_unit(self):
        result = netius.common.size_round_unit(209715200, space=True)
        self.assertEqual(result, "200 MB")

        result = netius.common.size_round_unit(20480, space=True)
        self.assertEqual(result, "20 KB")

        result = netius.common.size_round_unit(2048, reduce=False, space=True)
        self.assertEqual(result, "2.00 KB")

        result = netius.common.size_round_unit(2500, space=True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(2500, reduce=False, space=True)
        self.assertEqual(result, "2.44 KB")

        result = netius.common.size_round_unit(1)
        self.assertEqual(result, "1B")

        result = netius.common.size_round_unit(2048, minimum=2049, reduce=False)
        self.assertEqual(result, "2048B")

        result = netius.common.size_round_unit(2049, places=4, reduce=False)
        self.assertEqual(result, "2.001KB")

        result = netius.common.size_round_unit(2048, places=0, reduce=False)
        self.assertEqual(result, "2KB")

        result = netius.common.size_round_unit(2049, places=0, reduce=False)
        self.assertEqual(result, "2KB")

    def test_size_round_unit_justify(self):
        result = netius.common.size_round_unit(2048, justify=True)

        # the justification pads the value so that a column of them may
        # be aligned, the unit coming right after the padded value
        self.assertEqual(result.startswith(" "), True)
        self.assertEqual(result.strip(), "2KB")

        # without it the value carries no padding at all, which is the
        # whole of the difference that the flag makes
        self.assertEqual(netius.common.size_round_unit(2048), "2KB")

    def test_verify(self):
        result = netius.common.verify(1 == 1)
        self.assertEqual(result, None)

        result = netius.common.verify("hello" == "hello")
        self.assertEqual(result, None)

        self.assertRaises(netius.AssertionError, lambda: netius.common.verify(1 == 2))

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify(1 == 2, exception=netius.NetiusError),
        )

    def test_verify_equal(self):
        result = netius.common.verify_equal(1, 1)
        self.assertEqual(result, None)

        result = netius.common.verify_equal("hello", "hello")
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_equal(1, 2)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_equal(1, 2, exception=netius.NetiusError),
        )

    def test_verify_not_equal(self):
        result = netius.common.verify_not_equal(1, 2)
        self.assertEqual(result, None)

        result = netius.common.verify_not_equal("hello", "world")
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_not_equal(1, 1)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_not_equal(1, 1, exception=netius.NetiusError),
        )

    def test_verify_type(self):
        result = netius.common.verify_type("hello", str)
        self.assertEqual(result, None)

        result = netius.common.verify_type(1, int)
        self.assertEqual(result, None)

        result = netius.common.verify_type(None, int)
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_type(1, str)
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_type(1, str, exception=netius.NetiusError),
        )

        self.assertRaises(
            netius.AssertionError,
            lambda: netius.common.verify_type(None, str, null=False),
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_type(
                None, str, null=False, exception=netius.NetiusError
            ),
        )

    def test_verify_many(self):
        result = netius.common.verify_many((1 == 1, 2 == 2, 3 == 3))
        self.assertEqual(result, None)

        result = netius.common.verify_many(("hello" == "hello",))
        self.assertEqual(result, None)

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_many((1 == 2,))
        )

        self.assertRaises(
            netius.AssertionError, lambda: netius.common.verify_many((1 == 1, 1 == 2))
        )

        self.assertRaises(
            netius.NetiusError,
            lambda: netius.common.verify_many(
                (1 == 1, 1 == 2), exception=netius.NetiusError
            ),
        )

    def _link(self, source, target):
        # the creation of a link is reserved to a privileged user under
        # some systems, in which case the case has nothing to run
        try:
            os.symlink(source, target)
        except (AttributeError, NotImplementedError, OSError):
            self.skipTest("Skipping test: symbolic links unavailable")

    def _store(self, path, contents=b"contents"):
        file = open(path, "wb")
        try:
            file.write(contents)
        finally:
            file.close()
