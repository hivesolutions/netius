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

import unittest

import netius.common


class MimeTest(unittest.TestCase):

    def test_headers_getitem(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")
        headers.set(b"Second", b"second")

        # the value of a header may be reached by its name and the pair
        # of it by the position that it holds in the sequence
        self.assertEqual(headers[b"Second"], b"second")
        self.assertEqual(headers[0], [b"First", b"first"])

        # a name that was never set names no value at all, which is an
        # error and not a value of its own
        self.assertRaises(KeyError, lambda: headers[b"Missing"])

    def test_headers_setitem(self):
        headers = netius.common.mime.Headers()
        headers[b"First"] = b"first"

        self.assertEqual(headers, [[b"First", b"first"]])

        # a position that is given in the place of a name replaces the
        # pair that is there, instead of adding one of its own
        headers[0] = [b"Second", b"second"]

        self.assertEqual(headers, [[b"Second", b"second"]])

    def test_headers_delitem(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")
        headers.set(b"Second", b"second")

        del headers[b"First"]

        self.assertEqual(headers, [[b"Second", b"second"]])

        del headers[0]

        self.assertEqual(headers, [])

    def test_headers_contains(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")

        self.assertEqual(b"First" in headers, True)
        self.assertEqual(b"Missing" in headers, False)

        # a value that is not a name is looked for as the pair that it
        # is, which is how a plain sequence behaves
        self.assertEqual([b"First", b"first"] in headers, True)
        self.assertEqual([b"First", b"other"] in headers, False)

    def test_headers_item(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")

        # the pair itself is the one that is given back, so that the
        # value of it may be changed in place
        item = headers.item(b"First")

        self.assertEqual(item, [b"First", b"first"])

        item[1] = b"other"

        self.assertEqual(headers[b"First"], b"other")

        self.assertRaises(KeyError, lambda: headers.item(b"Missing"))

    def test_headers_get(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")

        self.assertEqual(headers.get(b"First"), b"first")

        # a name that is not there gives the value that the caller named
        # as the fallback, instead of raising for it
        self.assertEqual(headers.get(b"Missing"), None)
        self.assertEqual(headers.get(b"Missing", b"default"), b"default")

    def test_headers_set_append(self):
        headers = netius.common.mime.Headers()
        headers.set(b"First", b"first")
        headers.set(b"First", b"other")

        # setting a name that is already there replaces the value of it,
        # so that the header is never named twice
        self.assertEqual(headers, [[b"First", b"other"]])

        headers.set(b"First", b"another", append=True)

        # with the appending asked for the name is written a second time,
        # which is what a header that carries many values needs
        self.assertEqual(len(headers), 2)
        self.assertEqual(headers[1], [b"First", b"another"])

    def test_headers_normalize(self):
        headers = netius.common.mime.Headers()
        headers.set("First", 1)

        # a value of any kind is turned into a byte sequence, as that is
        # what travels in the message
        self.assertEqual(headers, [[b"First", b"1"]])

    def test_headers(self):
        headers = netius.common.mime.Headers()
        headers.set("Header", "Value")
        headers_s = headers.join()
        self.assertEqual(headers_s, b"Header: Value")

        headers = netius.common.mime.Headers()
        headers.set(b"Header", b"Value")
        headers_s = headers.join()
        self.assertEqual(headers_s, b"Header: Value")

        headers = netius.common.mime.Headers()
        headers.set(b"Header", netius.legacy.u("值").encode("utf-8"))
        headers_s = headers.join()
        self.assertEqual(headers_s, netius.legacy.u("Header: 值").encode("utf-8"))

    def test_headers_pop(self):
        headers = netius.common.mime.Headers()
        headers.set(b"Message-ID", b"<123@example.com>")
        result = headers.pop("Message-ID", None)
        self.assertEqual(result, b"<123@example.com>")
        self.assertEqual(len(headers), 0)

    def test_headers_pop_bytes(self):
        headers = netius.common.mime.Headers()
        headers.set(b"Message-ID", b"<123@example.com>")
        result = headers.pop(b"Message-ID", None)
        self.assertEqual(result, b"<123@example.com>")
        self.assertEqual(len(headers), 0)

    def test_headers_pop_default(self):
        headers = netius.common.mime.Headers()
        result = headers.pop("Missing", "default")
        self.assertEqual(result, "default")

    def test_rfc822_parse(self):
        message = (
            b"From: sender@example.com\r\n"
            b"To: target@example.com\r\n"
            b"Subject: Hello World\r\n"
            b"\r\n"
            b"the body of it\r\n"
            b"and one more line"
        )

        headers, body = netius.common.rfc822_parse(message)

        # the headers of the message are gathered in the order that they
        # come, the body being what follows the empty line
        self.assertEqual(headers[b"From"], b"sender@example.com")
        self.assertEqual(headers[b"Subject"], b"Hello World")
        self.assertEqual(len(headers), 3)
        self.assertEqual(body, b"the body of it\r\nand one more line")

    def test_rfc822_parse_continuation(self):
        message = b"Subject: Hello\r\n" b" World\r\n" b"\r\n" b"body"

        headers, body = netius.common.rfc822_parse(message)

        # a line that starts with a space is the continuation of the one
        # before it, so the two of them are a single header
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[b"Subject"], b"Hello\r\n World")
        self.assertEqual(body, b"body")

    def test_rfc822_parse_strip(self):
        message = b"Subject:   Hello World\r\n\r\nbody"

        headers, _body = netius.common.rfc822_parse(message)

        self.assertEqual(headers[b"Subject"], b"Hello World")

        # without the stripping the value is kept exactly as it came,
        # which is what the signing of a message needs
        headers, _body = netius.common.rfc822_parse(message, strip=False)

        self.assertEqual(headers[b"Subject"], b"   Hello World")

    def test_rfc822_parse_from(self):
        message = b"From john Mon Jan  1 00:00:00 2024\r\nSubject: Hello\r\n\r\nbody"

        headers, _body = netius.common.rfc822_parse(message)

        # the line of the old fashioned mailbox format names no header,
        # and is tolerated instead of breaking the parsing
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[b"Subject"], b"Hello")

    def test_rfc822_parse_invalid(self):
        message = b"this is not a header at all\r\n\r\nbody"

        # a line that names no header and is not the tolerated one has
        # no place in the message, so the parsing is refused
        self.assertRaises(
            netius.ParserError, lambda: netius.common.rfc822_parse(message)
        )

    def test_rfc822_join(self):
        headers = netius.common.mime.Headers()
        headers.set(b"From", b"sender@example.com")
        headers.set(b"Subject", b"Hello World")

        result = netius.common.rfc822_join(headers, b"the body")

        # the joining is the reverse of the parsing, the empty line being
        # what tells the headers from the body
        self.assertEqual(
            result,
            b"From: sender@example.com\r\nSubject: Hello World\r\n\r\nthe body",
        )

        headers, body = netius.common.rfc822_parse(result)

        self.assertEqual(headers[b"Subject"], b"Hello World")
        self.assertEqual(body, b"the body")

    def test_mime_register(self):
        import mimetypes

        netius.common.mime_register()

        # the types of the package are added to the ones of the runtime,
        # so that a file of them is named correctly
        extension, _encoding = mimetypes.guess_type("file.js")

        self.assertEqual(extension, "application/javascript")

        # the registration happens only once, so a second call is a no
        # operation that leaves the types as they are
        netius.common.mime_register()

        self.assertEqual(netius.common.mime.MIME_REGISTERED, True)
