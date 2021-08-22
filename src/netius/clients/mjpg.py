#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2020 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2020 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os

import netius

from . import http

class MJPGProtocol(http.HTTPProtocol):

    MAGIC_JPEG = b"\xff\xd8\xff\xe0"
    """ The magic signature for the JPEG infra-structure, this
    sequence of bytes is going to be used to detect new frames
    coming from the HTTP based stream """

    EOI_JPEG = b"\xff\xd9"
    """ The sequence of bytes that indicate the end of the current
    image, when these bytes are detected on the stream the message
    should be "flushed" to the current output (emit) """

    def __init__(self, *args, **kwargs):
        http.HTTPProtocol.__init__(self, *args, **kwargs)
        self.buffer_l = []

    def add_buffer(self, data):
        self.buffer_l.append(data)

    def get_buffer(self, delete = True):
        if not self.buffer_l: return b""
        buffer = b"".join(self.buffer_l)
        if delete: del self.buffer_l[:]
        return buffer

    def on_partial(self, data):
        http.HTTPProtocol.on_partial(self, data)

        # retrieves the reference to the top class that is going to
        # be used for the correct parsing of the image
        cls = self.__class__

        # tries to find the end of image (EOI) indicator in the current
        # received data, and in case it's not found add the (partial)
        # data to the current buffer, to be latter processed
        eoi_index = data.find(cls.EOI_JPEG)
        if eoi_index == -1: self.buffer_l.append(data); return

        # calculates the size of the end of image (EOI) token so that
        # this value will be used for the calculus of the image data
        eoi_size = len(cls.EOI_JPEG)

        # adds the partial valid data of the current chunk to the buffer
        # and then joins the current buffer as the frame data, removing
        # the multipart header from it (to become a valid image)
        self.buffer_l.append(data[:eoi_index + eoi_size])
        frame = b"".join(self.buffer_l)
        multipart_index = frame.find(b"\r\n\r\n")
        frame = frame[multipart_index + 4:]

        # clears the current buffer and adds the remaining part of the
        # current chunk, that may be already part of a new image
        del self.buffer_l[:]
        self.buffer_l.append(data[eoi_index + eoi_size:])

        # calls the proper event handler for the new frame data that has
        # just been received, triggering the processing of the frame
        self.on_frame_mjpg(frame)

    def on_frame_mjpg(self, data):
        self.trigger("frame", self, data)

class MJPGClient(http.HTTPClient):

    protocol = MJPGProtocol

if __name__ == "__main__":
    index = 0
    limit = 30

    def on_frame(protocol, data):
        global index
        index += 1
        if index >= limit: return protocol.close()
        base_path = netius.conf("IMAGES_PATH", "images")
        base_path = os.path.abspath(base_path)
        base_path = os.path.normpath(base_path)
        if not os.path.exists(base_path): os.makedirs(base_path)
        path = os.path.join(base_path, "%08d.jpg" % index)
        file = open(path, "wb")
        try: file.write(data)
        finally: file.close()
        print("Saved frame %08d of %d bytes" % (index, len(data)))

    def on_finish(protocol):
        netius.compat_loop(loop).stop()

    url = netius.conf("MJPG_URL", "http://euglena.stanford.edu:20005/?action=stream")

    client = MJPGClient()
    loop, protocol = client.get(url)

    protocol.bind("frame", on_frame)
    protocol.bind("finish", on_finish)

    loop.run_forever()
    loop.close()
else:
    __path__ = []
