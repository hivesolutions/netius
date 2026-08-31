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

import netius.clients

MULTIPART = b"Content-Type: image/jpeg\r\n" b"Content-Length: 10\r\n" b"\r\n"
""" The head of a part of the stream, which comes before the
data of the image and is not part of it """


class MJPGProtocolTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.protocol = netius.clients.MJPGProtocol("GET", "http://mjpg.local/")
        self.frames = []
        self.protocol.bind("frame", self._on_frame)

    def test_init(self):
        # the buffer of a protocol starts empty, as no part of an image
        # has been received through it yet
        self.assertEqual(self.protocol.buffer_l, [])

    def test_add_buffer(self):
        self.protocol.add_buffer(b"first")
        self.protocol.add_buffer(b"second")

        self.assertEqual(self.protocol.buffer_l, [b"first", b"second"])

    def test_get_buffer(self):
        self.assertEqual(self.protocol.get_buffer(), b"")

        self.protocol.add_buffer(b"first")
        self.protocol.add_buffer(b"second")

        # the parts of the buffer are joined into a single sequence and
        # the buffer is emptied, so that none of them is given twice
        self.assertEqual(self.protocol.get_buffer(), b"firstsecond")
        self.assertEqual(self.protocol.buffer_l, [])

    def test_get_buffer_keep(self):
        self.protocol.add_buffer(b"first")

        # with the deletion turned off the parts are kept in place, so
        # that the very same value may be read again
        self.assertEqual(self.protocol.get_buffer(delete=False), b"first")
        self.assertEqual(self.protocol.buffer_l, [b"first"])

    def test_on_partial(self):
        cls = netius.clients.MJPGProtocol
        image = cls.MAGIC_JPEG + b"body" + cls.EOI_JPEG

        self.protocol.on_partial(MULTIPART + image)

        # the head of the part is not part of the image, so it is dropped
        # from the frame that reaches the ones bound to the event
        self.assertEqual(self.frames, [image])
        self.assertEqual(self.protocol.buffer_l, [b""])

    def test_on_partial_split(self):
        cls = netius.clients.MJPGProtocol
        image = cls.MAGIC_JPEG + b"body" + cls.EOI_JPEG

        self.protocol.on_partial(MULTIPART + image[:6])

        # the end of the image was not reached yet, so the data is kept
        # in the buffer instead of being given as a frame
        self.assertEqual(self.frames, [])
        self.assertEqual(self.protocol.get_buffer(delete=False), MULTIPART + image[:6])

        self.protocol.on_partial(image[6:])

        # the remainder completes the image, which is then joined from
        # the parts that were gathered along the way
        self.assertEqual(self.frames, [image])

    def test_on_partial_remaining(self):
        cls = netius.clients.MJPGProtocol
        image = cls.MAGIC_JPEG + b"body" + cls.EOI_JPEG

        self.protocol.on_partial(MULTIPART + image + b"remaining")

        # what comes after the end of an image is already part of the one
        # that follows it, so it is kept for the next frame
        self.assertEqual(self.frames, [image])
        self.assertEqual(self.protocol.buffer_l, [b"remaining"])

    def test_on_frame_mjpg(self):
        self.protocol.on_frame_mjpg(b"frame")

        self.assertEqual(self.frames, [b"frame"])

    def _on_frame(self, protocol, data):
        self.frames.append(data)
