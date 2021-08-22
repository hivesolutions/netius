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

import unittest

import netius.common

class RSATest(unittest.TestCase):

    def test_rsa_crypt(self):
        number = 87521618088882533792115812
        exponent = 36510217105848231284079274231564906186307560780534247831648648175045225318561460162728717234530889577546652846221026215879731017938647097448942278391102846302059960991452569135619524616218782987723300816771871234796688783233883245022643852052966438968493009984572453713313165894751634193657763224930190644678
        modulus = 96932149016243683313202436463884391894442557094585987087679466243837140612162774296465245821614029972754395721149915741918184810668111591608828515674917153485786305039311784635247807314685477198540013198150331209390992944093549127578416635618276838812255204836659792055944277295324948158500484872595001982643
        expected = 77582017281983556473055444885999671275845710142539492742164750164915723397427639169767703318619952155855354799282839237590830862415463205074741285319459521280599333234352017115848949043330478158462953508557273618244552244536252761419615268258174029143566887421875425091295665101338067462122465562948190873420
        result = netius.common.rsa_crypt(number, exponent, modulus)
        self.assertEqual(result, expected)
