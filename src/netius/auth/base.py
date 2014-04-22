#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Netius System. If not, see <http://www.gnu.org/licenses/>.

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

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
        decoded = netius.bytes(decoded)
        hash = hashlib.new(type, decoded)
        _digest = hash.hexdigest()
        return _digest == digest

    @classmethod
    def generate(cls, password, type = "sha256", salt = "netius"):
        if type == "plain" : return password
        if salt: password += salt
        password = netius.bytes(password)
        hash = hashlib.new(type, password)
        digest = hash.hexdigest()
        if not salt: return "%s:%s" % (type, digest)
        salt = netius.bytes(salt)
        salt = binascii.hexlify(salt)
        salt = netius.str(salt)
        return "%s:%s:%s" % (type, salt, digest)

    @classmethod
    def unpack(cls, password):
        count = password.count(":")
        if count == 2: type, salt, digest = password.split(":")
        elif count == 1: type, digest = password.split(":"); salt = None
        else: plain = password; type = "plain"; salt = None; digest = None
        if not type == "plain": plain = None
        if salt: salt = binascii.unhexlify(salt)
        return (type, salt, digest, plain)
