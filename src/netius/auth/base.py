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

import os
import hashlib
import binascii

import netius

class Auth(object):
    """
    The top level base authentication handler, should define
    and implement generic authentication methods.

    The proper exceptions must be raised when the implementation
    at this abstraction level is insufficient or insecure.
    """

    def __init__(self, *args, **kwargs):
        object.__init__(self, *args, **kwargs)
        self.auth = self.auth_i
        self.auth_assert = self.auth_assert_i

    @classmethod
    def auth(cls, *args, **kwargs):
        raise netius.NotImplemented("Missing implementation")

    @classmethod
    def auth_assert(cls, *args, **kwargs):
        result = cls.auth(*args, **kwargs)
        if not result: raise netius.SecurityError("Invalid authentication")

    @classmethod
    def verify(cls, encoded, decoded):
        type, salt, digest, plain = cls.unpack(encoded)
        if plain: return encoded == decoded
        if salt: decoded += salt
        type = type.lower()
        decoded = netius.legacy.bytes(decoded)
        hash = hashlib.new(type, decoded)
        _digest = hash.hexdigest()
        return _digest == digest

    @classmethod
    def generate(cls, password, type = "sha256", salt = "netius"):
        if type == "plain" : return password
        if salt: password += salt
        password = netius.legacy.bytes(password)
        hash = hashlib.new(type, password)
        digest = hash.hexdigest()
        if not salt: return "%s:%s" % (type, digest)
        salt = netius.legacy.bytes(salt)
        salt = binascii.hexlify(salt)
        salt = netius.legacy.str(salt)
        return "%s:%s:%s" % (type, salt, digest)

    @classmethod
    def unpack(cls, password):
        count = password.count(":")
        if count == 2: type, salt, digest = password.split(":")
        elif count == 1: type, digest = password.split(":"); salt = None
        else: plain = password; type = "plain"; salt = None; digest = None
        if not type == "plain": plain = None
        if salt: salt = netius.legacy.bytes(salt)
        if salt: salt = binascii.unhexlify(salt)
        if salt: salt = netius.legacy.str(salt)
        return (type, salt, digest, plain)

    @classmethod
    def get_file(cls, path, cache = False, encoding = None):
        """
        Retrieves the (file) contents for the file located "under"
        the provided path, these contents are returned as a normal
        string based byte buffer.

        In case the cache flag is set these contents are store in
        memory so that they be latter retrieved much faster.

        If the optional encoding value is provide the final value is
        decoded according to the defined encoding.

        :type path: String
        :param path: The path as string to the file for which the
        contents are going to be retrieved.
        :type cache: bool
        :param cache: If the contents should be stored in memory and
        associated with the current path for latter access.
        :type encoding: String
        :param encoding: The string that identifies the encoding that
        is going to be used for the decoding of the final string value.
        :rtype: String
        :return: The contents (as a string) of the file located under
        the provided path (from the file system).
        """

        # runs the complete set of normalization processes for the path so
        # that the final path to be used in retrieval is canonical, providing
        # a better mechanisms for both loading and cache processes
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        path = os.path.normpath(path)

        # verifies if the cache attribute already exists under the current class
        # and in case it does not creates the initial cache dictionary
        if not hasattr(cls, "_cache"): cls._cache = dict()

        # tries to retrieve the contents of the file using a caches approach
        # and returns such value in case the cache flag is enabled
        result = cls._cache.get(path, None)
        if cache and not result == None: return result

        # as the cache retrieval has not been successful there's a need to
        # load the file from the secondary storage (file system)
        file = open(path, "rb")
        try: contents = file.read()
        finally: file.close

        # in case an encoding value has been passed the contents must be properly
        # decoded so that the "final" contents string is defined
        if encoding: contents = contents.decode(encoding)

        # verifies if the cache mode/flag is enabled and if that's the case
        # store the complete file contents in memory under the dictionary
        if cache: cls._cache[path] = contents
        return contents

    @classmethod
    def is_simple(cls):
        return False

    def auth_i(self, *args, **kwargs):
        return self.__class__.auth(*args, **kwargs)

    def auth_assert_i(self, *args, **kwargs):
        result = self.auth_i(*args, **kwargs)
        if not result: raise netius.SecurityError("Invalid authentication")

    def is_simple_i(self):
        return self.__class__.is_simple()
