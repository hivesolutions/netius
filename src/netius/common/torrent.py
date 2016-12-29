#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2017 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2017 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import re
import struct
import hashlib

import netius

from . import parser

HANDSHAKE_SIZE = 68
""" The typical size for an handshake message according
to the current torrent protocol definition, the value
is defined in bytes """

DECIMAL_REGEX = re.compile(r"\d")
""" Simple regular expression that matched any
character and expression with decimal digits """

TORRENT_TYPES = {
    -1 : "keep-alive",
    0 : "choke",
    1 : "unchoke",
    2 : "interested",
    3 : "not interested",
    4 : "have",
    5 : "bitfield",
    6 : "request",
    7 : "piece",
    8 : "cancel",
    9 : "port"
}
""" The map that associates the various message type
identifiers with their internal string representations """

def info_hash(root):
    info = root["info"]
    data = bencode(info)
    info_hash = hashlib.sha1(data)
    return info_hash.digest()

def bencode(root):
    # joins the complete set of values created by
    # generator that has been returned from the chunk
    # function using the provided root value
    data = b"".join([value for value in chunk(root)])
    return data

def bdecode(data):
    # converts the provide (string) data into a list
    # of chunks (characters) reversing it so that the
    # proper pop/push operations may be performed, as
    # pop is done from the back of the list
    data = netius.legacy.str(data)
    chunks = list(data)
    chunks.reverse()

    # runs the dechunking operation in the created list
    # of chunks obtaining a dictionary base structure
    # as the result of the bencoding operation
    root = dechunk(chunks)
    return root

def chunk(item):
    chunk_t = type(item)

    if chunk_t == bytes:
        item = netius.legacy.str(item)
        chunk_t = type(item)

    if chunk_t == dict:
        yield b"d"
        keys = item.keys()
        keys = list(keys)
        keys.sort()
        for key in keys:
            value = item[key]
            for part in chunk(key): yield part
            for part in chunk(value): yield part
        yield b"e"

    elif chunk_t == list:
        yield b"l"
        for value in item:
            for part in chunk(value): yield part
        yield b"e"

    elif chunk_t in netius.legacy.INTEGERS:
        yield netius.legacy.bytes("i%de" % item)

    elif chunk_t in netius.legacy.STRINGS:
        yield netius.legacy.bytes("%d:%s" % (len(item), item))

    else:
        raise netius.ParserError("Not possible to encode")

def dechunk(chunks):
    item = chunks.pop()

    if item == "d":
        item = chunks.pop()
        hash = {}

        while not item == "e":
            chunks.append(item)
            key = dechunk(chunks)
            hash[key] = dechunk(chunks)
            item = chunks.pop()

        return hash

    elif item == "l":
        item = chunks.pop()
        list = []

        while not item == "e":
            chunks.append(item)
            list.append(dechunk(chunks))
            item = chunks.pop()

        return list

    elif item == "i":
        item = chunks.pop()
        number = ""

        while not item == "e":
            number += item
            item = chunks.pop()

        return int(number)

    elif DECIMAL_REGEX.search(item):
        number = ""

        while DECIMAL_REGEX.search(item):
            number += item
            item = chunks.pop()

        line = []
        number = int(number)

        for _index in range(number):
            char = chunks.pop()
            line.append(char)

        line = "".join(line)

        return line

    raise netius.ParserError("Invalid input: '%s'" % item)

class TorrentParser(parser.Parser):

    def __init__(self, owner, store = False):
        parser.Parser.__init__(self, owner)

        self.length = None
        self.buffer = []
        self.buffer_l = 0

        self.build()

    def build(self):
        """
        Builds the initial set of states ordered according to
        their internal integer definitions, this method provides
        a fast and scalable way of parsing data.
        """

        parser.Parser.build(self)

        self.states = (
            self._parse_handshake,
            self._parse_message
        )
        self.state_l = len(self.states)

    def destroy(self):
        """
        Destroys the current structure for the parser meaning that
        it's restored to the original values, this method should only
        be called on situation where no more parser usage is required.
        """

        parser.Parser.destroy(self)

        self.states = ()
        self.state_l = 0

    def parse(self, data):
        """
        Parses the provided data chunk, changing the current
        state of the parser accordingly and returning the
        number of processed bytes from it.

        :type data: String
        :param data: The string containing the data to be parsed
        in the current parse operation.
        :rtype: int
        :return: The amount of bytes of the data string that have
        been "parsed" in the current parse operation.
        """

        parser.Parser.parse(self, data)

        # retrieves the size of the data that has been sent for parsing
        # and saves it under the size original variable
        size = len(data)
        size_o = size

        # iterates continuously to try to process all that
        # data that has been sent for processing
        while size > 0:
            # in case there's no owner associated with the
            # current parser must break the loop because
            # there's no way to continue with parsing
            if not self.owner: break

            # retrieves the parsing method for the current
            # state and then runs it retrieving the number
            # of valid parsed bytes in case this value is
            # zero the parsing iteration is broken
            method = self.states[self.owner.state - 1]
            count = method(data)
            if count == 0: break

            # decrements the size of the data buffer by the
            # size of the parsed bytes and then retrieves the
            # sub part of the data buffer as the new data buffer
            size -= count
            data = data[count:]

        # in case not all of the data has been processed
        # must add it to the buffer so that it may be used
        # latter in the next parsing of the message
        if size > 0: self.buffer.append(data); self.buffer_l += size

        # returns the number of read (processed) bytes of the
        # data that has been sent to the parser
        return size_o - size

    def _join(self, data):
        self.buffer.append(data)
        result = b"".join(self.buffer)
        self.buffer = [result]
        self.buffer_l = len(result)
        return result

    def _parse_handshake(self, data):
        total = len(data) + self.buffer_l

        if total < HANDSHAKE_SIZE: return 0

        diff = HANDSHAKE_SIZE - self.buffer_l if self.buffer_l < HANDSHAKE_SIZE else 0
        result = self._join(data[:diff])

        _length, protocol, reserved, info_hash, peer_id = struct.unpack("!B19sQ20s20s", result)
        self.trigger("on_handshake", protocol, reserved, info_hash, peer_id)

        self.length = None
        del self.buffer[:]
        self.buffer_l = 0

        return diff

    def _parse_message(self, data):
        # starts the current processed byte count at zero and then
        # measures the current total received bytes using the length
        # of the current data chunk received and the buffer length
        count = 0
        total = len(data) + self.buffer_l

        # in case the length is not yet defined it must be searched
        # inside the current message so that it may than be re-used
        # to check if the complete message has been received
        if self.length == None:
            if total < 4: return 0
            diff = 4 - self.buffer_l if self.buffer_l < 4 else 0
            result = self._join(data[:diff])
            data = data[diff:]
            self.length, = struct.unpack("!L", result[:4])
            count += diff

        # calculates the "target" total message length and verifies
        # that the total number of bytes received for the message
        # have already reached that value otherwise returns count
        # to the caller method (delayed execution)
        message_length = self.length + 4
        if total < message_length: return count

        # calculates the difference between meaning the amount of
        # data from the current chunk that is going to be processed
        # and then joins the current buffer accordingly
        diff = message_length - self.buffer_l if self.buffer_l < message_length else 0
        result = self._join(data[:diff])

        # verifies if the message contains a payload (length is
        # greater than zero) for such situations the type must
        # be loaded, otherwise the type is assumed to be the keep
        # alive one (only message with no payload available)
        if self.length > 0: type, = struct.unpack("!B", result[4:5])
        else: type = -1

        # resolves the current type integer based type into the proper
        # string based type values so that it may be used from now on
        type_s = TORRENT_TYPES.get(type, "invalid")
        data = result[5:]

        # triggers the on message event notifying the listeners about
        # the current message that has been received (includes payload and type)
        self.trigger("on_message", self.length, type_s, data)

        # resets the current message processing state as the message
        # has been completely processed, new message may come and require
        # a newly created state for the parser (to be correctly processed)
        self.length = None
        del self.buffer[:]
        self.buffer_l = 0

        # increments the current byte processed counter with the current
        # diff value and then returns the count value to the caller method
        # notifying it about the number of processed bytes
        count += diff
        return count
