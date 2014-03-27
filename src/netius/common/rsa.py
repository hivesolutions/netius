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

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

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

import math
import types
import base64

import netius

import asn
import util
import calc

PRIVATE_TOKEN = "RSA PRIVATE KEY"
PUBLIC_TOKEN = "PUBLIC KEY"

def open_pem_key(path, token = PRIVATE_TOKEN):
    begin, end = pem_limiters(token)

    file = open(path, "rb")
    try: data = file.read()
    finally: file.close()

    begin_index = data.find(begin)
    end_index = data.find(end)

    if begin_index == -1: raise netius.ParserError("Invalid key format")
    if end_index == -1: raise netius.ParserError("Invalid key format")

    begin_index += len(begin)

    data = data[begin_index:end_index]
    data = data.strip()
    return base64.b64decode(data)

def write_pem_key(
    path,
    data,
    token = PRIVATE_TOKEN,
    width = 64
):
    begin, end = pem_limiters(token)

    data = base64.b64encode(data)

    chunks = [chunk for chunk in util.chunks(data, width)]
    data = "\n".join(chunks)

    file = open(path, "wb")
    try:
        file.write(begin)
        file.write("\n")
        file.write(data)
        file.write("\n")
        file.write(end)
        file.write("\n")
    finally:
        file.close()

def open_private_key(path):
    data = open_pem_key(
        path,
        token = PRIVATE_TOKEN
    )
    asn1 = asn.asn1_parse(asn.ASN1_RSA_PRIVATE_KEY, data)[0]
    private_key = dict(
        version = asn1[0],
        modulus = asn1[1],
        public_exponent = asn1[2],
        private_exponent = asn1[3],
        prime_1 = asn1[4],
        prime_2 = asn1[5],
        exponent_1 = asn1[6],
        exponent_2 = asn1[7],
        coefficient = asn1[8]
    )
    return private_key

def open_public_key(path):
    data = open_pem_key(
        path,
        token = PUBLIC_TOKEN
    )
    asn1 = asn.asn1_parse(asn.ASN1_OBJECT, data)[0]
    asn1 = asn.asn1_parse(asn.ASN1_RSA_PUBLIC_KEY, asn1[1][1:])[0]
    public_key = dict(
        modulus = asn1[0],
        public_exponent = asn1[1]
    )
    return public_key

def write_private_key(path, private_key):
    data = asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.INTEGER, private_key["version"]),
            (asn.INTEGER, private_key["modulus"]),
            (asn.INTEGER, private_key["public_exponent"]),
            (asn.INTEGER, private_key["private_exponent"]),
            (asn.INTEGER, private_key["prime_1"]),
            (asn.INTEGER, private_key["prime_2"]),
            (asn.INTEGER, private_key["exponent_1"]),
            (asn.INTEGER, private_key["exponent_2"]),
            (asn.INTEGER, private_key["coefficient"])
        ])
    )
    write_pem_key(
        path,
        data,
        token = PRIVATE_TOKEN
    )

def write_public_key(path, public_key):
    data = "\x00" + asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.INTEGER, public_key["modulus"]),
            (asn.INTEGER, public_key["public_exponent"])
        ])
    )
    data = asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.SEQUENCE, [
                (asn.OBJECT_IDENTIFIER, asn.RSAID_PKCS1),
                (asn.NULL, None)
            ]),
            (asn.BIT_STRING, data)
        ])
    )
    write_pem_key(
        path,
        data,
        token = PUBLIC_TOKEN
    )

def pem_to_der(in_path, out_path, token = PRIVATE_TOKEN):
    data = open_pem_key(in_path, token = token)
    file = open(out_path, "wb")
    try: file.write(data)
    finally: file.close()

def pem_limiters(token):
    begin = "-----BEGIN " + token + "-----"
    end = "-----END " + token + "-----"
    return (begin, end)

def private_to_public(private_key):
    public_key = dict(
        modulus = private_key["modulus"],
        public_exponent = private_key["public_exponent"]
    )
    return public_key

def rsa_private(number_bits):
    """
    Generates a new "random" private with the requested number
    of bits as the base for exponents and modulus.

    This method is extremely time consuming in terms of processor
    and should be used carefully to avoid any problem.

    @type number_bits: int
    @param number_bits: The number of bits that are going to be
    used for the generation of the private key.
    @rtype: Dictionary
    @return: The generated private key structure, may then be used
    for processing or written to a file.
    """

    while True:
        prime_1, prime_2 = rsa_primes(number_bits)
        public_exponent, private_exponent = rsa_exponents(prime_1, prime_2, number_bits)
        if private_exponent > 0: break

    modulus = prime_1 * prime_2
    exponent_1 = private_exponent % (prime_1 - 1)
    exponent_2 = private_exponent % (prime_2 - 1)
    coefficient = (1 / prime_2) % prime_1

    private_key = dict(
        version = 0,
        modulus = modulus,
        public_exponent = public_exponent,
        private_exponent = private_exponent,
        prime_1 = prime_1,
        prime_2 = prime_2,
        exponent_1 = exponent_1,
        exponent_2 = exponent_2,
        coefficient = coefficient
    )

    return private_key

def rsa_primes(number_bits):
    """
    Generates two different prime numbers (p and q values)
    and returns them inside a tuple structure.

    The generation is made according to the number of bits
    defined and using a trial and error strategy (expensive).

    @type number_bits: int
    @param number_bits: The number of bits to be used in
    prime generation, this affects security.
    @rtype: Tuple
    @return: A tuple containing the two different prime
    numbers to be returned.
    """

    # generates a prime number to serve as p value
    # or the first prime value
    prime_1 = calc.prime(number_bits)

    # iterates continuously trying to find a second prime
    # number that is not equal to the first one
    while True:
        # generates a prime number to serve as q value
        # and verifies if the value of both primes is the
        # same, in case it's not the value is considered
        # to be valid and breaks the loop
        prime_2 = calc.prime(number_bits)
        if not prime_2 == prime_1: break

    # returns a tuple containing both of the generated
    # primes and returns it to the caller method
    return (prime_1, prime_2)

def rsa_exponents(prime_1, prime_2, number_bits):
    """
    Generates both the public and the private exponents for
    the rsa cryptography system taking as base the provided
    prime numbers and the amount of bits for the values.

    @type prime_1: int
    @param prime_1: The first prime number use for rsa.
    @type prime_2: int
    @param prime_2: The second prime number use for rsa.
    @type number_bits: int
    @param number_bits: The number of bits that are going to be
    used for the generation of the values.
    @rtype: Tuple
    @return: The tuple containing the generated public and
    private keys (properly tested).
    """

    # calculates the modulus and the phi value for the
    # modulus, as the y are going to be used for calculus
    modulus = prime_1 * prime_2
    phi_modulus = (prime_1 - 1) * (prime_2 - 1)

    # iterates continuously to find a valid public exponent, one
    # that satisfies the relative prime
    while True:
        # make sure e has enough bits so we ensure "wrapping" through
        # modulus (n value)
        public_exponent = calc.prime(max(8, number_bits / 2))

        # checks if the exponent and the modulus are relative primes
        # and also checks if the exponent and the phi modulus are relative
        # primes, for that situation a valid public exponent has been fond
        # and the cycle may be broken
        is_relative = calc.relatively_prime(public_exponent, modulus)
        is_relative_phi = calc.relatively_prime(public_exponent, phi_modulus)
        if is_relative and is_relative_phi: break

    # retrieves the result of the extended euclid greatest common divisor
    d, k, _l = calc.extended_gcd(public_exponent, phi_modulus)
    private_exponent = k

    # in case the greatest common divisor between both is not one, the values
    # are not relative primes and an exception must be raised
    if not d == 1: raise netius.GeneratorError(
        "The public exponent '%d' and the phi modulus '%d' are not relative primes" %\
        (public_exponent, phi_modulus)
    )

    # calculates the inverse modulus for both exponent and in case it's not one
    # an exception is raised about the problem
    inverse_modulus = (public_exponent * private_exponent) % phi_modulus
    if not inverse_modulus == 1: netius.GeneratorError(
        "The public exponent '%d' and private exponent '%d' are not multiplicative inverse modulus of phi modulus '%d'" %
        (public_exponent, private_exponent, phi_modulus)
    )

    # creates the tuple that contains both the public and the private
    # exponent values that may be used for rsa based cryptography
    return (public_exponent, private_exponent)

def rsa_crypt(value, exponent, modulus):
    if type(value) == types.IntType:
        return rsa_crypt(long(value), exponent, modulus)

    if not type(value) == types.LongType:
        raise TypeError("you must pass a long or an int")

    if value > 0 and math.floor(math.log(value, 2)) > math.floor(math.log(modulus, 2)):
        raise OverflowError("the message is too long")

    return pow(value, exponent, modulus)
