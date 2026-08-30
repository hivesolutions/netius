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

import collections
import unittest

import netius.servers


class MJPGServerTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.servers = []

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        for server in self.servers:
            server.cleanup()

    def test_init(self):
        server = self._make_server()

        # the boundary of the stream falls back to the one of the module,
        # which is what separates the parts of it
        self.assertEqual(server.boundary, netius.servers.mjpg.BOUNDARY)

        server = self._make_server(boundary="custom")

        self.assertEqual(server.boundary, "custom")

    def test_on_data_http(self):
        server = self._make_server()
        connection = _MockConnection()

        server.on_data_http(connection, self._make_parser())

        headers = connection.headers[0]

        # the answer announces a stream whose parts replace one another,
        # separated by the boundary, and is never cached
        self.assertEqual(
            headers["headers"]["Content-type"],
            "multipart/x-mixed-replace; boundary=%s" % server.boundary,
        )
        self.assertEqual(headers["headers"]["Cache-Control"], "no-cache")
        self.assertEqual(headers["code"], 200)
        self.assertEqual(headers["version"], "HTTP/1.1")

        data, kwargs = connection.parts[0]

        # the part carries the boundary, the head of the image and the
        # image itself, and is never the final one of the answer
        self.assertEqual(data.startswith(b"--mjpegboundary\r\n"), True)
        self.assertEqual(b"Content-Type: image/jpeg\r\n" in data, True)
        self.assertEqual(data.endswith(b"\r\n"), True)
        self.assertEqual(kwargs["final"], False)

    def test_on_data_http_next(self):
        server = self._make_server()
        connection = _MockConnection()

        server.on_data_http(connection, self._make_parser())

        _data, kwargs = connection.parts[0]

        # the answering of a part is what schedules the one that follows
        # it, after the delay that the server asks for
        kwargs["callback"](connection)
        server.delayed[0][0]()

        self.assertEqual(server.delayed[0][1], 1)
        self.assertEqual(len(connection.parts), 2)

    def test_on_data_http_empty(self):
        server = self._make_server(cls=_EmptyMJPGServer)
        connection = _MockConnection()

        server.on_data_http(connection, self._make_parser())

        data, _kwargs = connection.parts[0]

        # a provider that gives no image is warned about, the part being
        # sent with no body instead of the answer being broken
        self.assertEqual(b"Content-Length: 0\r\n" in data, True)

    def test_on_send_mjpg(self):
        server = self._make_server()

        # the hook of the sending carries no behaviour of its own, being
        # meant to be taken over by the implementations
        self.assertEqual(server.on_send_mjpg(_MockConnection()), None)

    def test_get_delay(self):
        server = self._make_server()

        self.assertEqual(server.get_delay(_MockConnection()), 1)

    def test_get_image(self):
        server = self._make_server()
        connection = _MockConnection()

        first = server.get_image(connection)

        # the images that are served come from the ones that the package
        # carries, so both of them are proper JPEG files
        self.assertEqual(first.startswith(b"\xff\xd8"), True)
        self.assertEqual(connection.index, 1)

        second = server.get_image(connection)

        # the provider walks the images in turn, so the one that follows
        # is a different one from the first
        self.assertNotEqual(second, first)
        self.assertEqual(connection.index, 2)

        # the walking wraps around, which brings the first image back
        self.assertEqual(server.get_image(connection), first)

    def _make_server(self, cls=None, **kwargs):
        cls = cls or _MockMJPGServer
        server = cls(**kwargs)
        self.servers.append(server)
        return server

    def _make_parser(self, version_s="HTTP/1.1"):
        Parser = collections.namedtuple("Parser", "version_s")
        return Parser(version_s=version_s)


class _MockMJPGServer(netius.servers.MJPGServer):
    """
    Variant of the server that keeps the callables that are
    delayed instead of handing them to the event loop.
    """

    def __init__(self, *args, **kwargs):
        netius.servers.MJPGServer.__init__(self, *args, **kwargs)
        self.delayed = []

    def delay(self, callable, timeout=None, *args, **kwargs):
        self.delayed.append((callable, timeout))


class _EmptyMJPGServer(_MockMJPGServer):
    """
    Variant of the server whose provider of images is never
    able to give one back.
    """

    def get_image(self, connection):
        return None


class _MockConnection(object):
    """
    Stand in for a connection that keeps both the header and
    the parts that are sent through it.
    """

    def __init__(self):
        self.headers = []
        self.parts = []

    def resolve_encoding(self, parser):
        pass

    def send_header(self, headers=None, version=None, code=200, code_s=None):
        self.headers.append(
            dict(headers=headers, version=version, code=code, code_s=code_s)
        )

    def send_part(self, data, final=True, callback=None):
        self.parts.append((data, dict(final=final, callback=callback)))
