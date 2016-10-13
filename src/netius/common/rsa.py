#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2016 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2016 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import math
import base64

import netius

from . import asn
from . import util
from . import calc

PRIVATE_TOKEN = "RSA PRIVATE KEY"
PUBLIC_TOKEN = "PUBLIC KEY"

def open_pem_key(path, token = PRIVATE_TOKEN):
    is_file = not type(path) in netius.legacy.STRINGS
    if is_file: file = path
    else: file = open(path, "rb")
    try:
        data = file.read()
    finally:
        if not is_file: file.close()
    return open_pem_data(data, token = token)

def open_pem_data(data, token = PRIVATE_TOKEN):
    begin, end = pem_limiters(token)

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
    data = b"\n".join(chunks)

    is_file = not type(path) in netius.legacy.STRINGS
    file = path if is_file else open(path, "wb")
    try:
        file.write(begin)
        file.write(b"\n")
        file.write(data)
        file.write(b"\n")
        file.write(end)
        file.write(b"\n")
    finally:
        if not is_file: file.close()

def open_private_key(path):
    data = open_pem_key(
        path,
        token = PRIVATE_TOKEN
    )
    return open_private_key_data(data)

def open_private_key_b64(data_b64):
    data = base64.b64decode(data_b64)
    return open_private_key_data(data)

def open_private_key_data(data):
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
        coefficient = asn1[8],
        bits = rsa_bits(asn1[1])
    )
    return private_key

def open_public_key(path):
    data = open_pem_key(
        path,
        token = PUBLIC_TOKEN
    )
    return open_public_key_data(data)

def open_public_key_b64(data_b64):
    data = base64.b64decode(data_b64)
    return open_public_key_data(data)

def open_public_key_data(data):
    asn1 = asn.asn1_parse(asn.ASN1_OBJECT, data)[0]
    asn1 = asn.asn1_parse(asn.ASN1_RSA_PUBLIC_KEY, asn1[1][1:])[0]
    public_key = dict(
        modulus = asn1[0],
        public_exponent = asn1[1],
        bits = rsa_bits(asn1[0])
    )
    return public_key

def write_private_key(path, private_key):
    data = asn_private_key(private_key)
    write_pem_key(
        path,
        data,
        token = PRIVATE_TOKEN
    )

def write_public_key(path, public_key):
    data = asn_public_key(public_key)
    write_pem_key(
        path,
        data,
        token = PUBLIC_TOKEN
    )

def asn_private_key(private_key):
    return asn.asn1_gen(
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

def asn_public_key(public_key):
    data = b"\x00" + asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.INTEGER, public_key["modulus"]),
            (asn.INTEGER, public_key["public_exponent"])
        ])
    )
    return asn.asn1_gen(
        (asn.SEQUENCE, [
            (asn.SEQUENCE, [
                (asn.OBJECT_IDENTIFIER, asn.RSAID_PKCS1),
                (asn.NULL, None)
            ]),
            (asn.BIT_STRING, data)
        ])
    )

def pem_to_der(in_path, out_path, token = PRIVATE_TOKEN):
    data = open_pem_key(in_path, token = token)
    file = open(out_path, "wb")
    try: file.write(data)
    finally: file.close()

def pem_limiters(token):
    begin = netius.legacy.bytes("-----BEGIN " + token + "-----")
    end = netius.legacy.bytes("-----END " + token + "-----")
    return (begin, end)

def private_to_public(private_key):
    public_key = dict(
        modulus = private_key["modulus"],
        public_exponent = private_key["public_exponent"]
    )
    return public_key

def assert_private(private_key, number_bits = None):
    prime_1 = private_key["prime_1"]
    prime_2 = private_key["prime_2"]
    private_exponent = private_key["private_exponent"]

    modulus = prime_1 * prime_2
    exponent_1 = private_exponent % (prime_1 - 1)
    exponent_2 = private_exponent % (prime_2 - 1)
    coefficient = calc.modinv(prime_2, prime_1)

    assert modulus == private_key["modulus"]
    assert exponent_1 == private_key["exponent_1"]
    assert exponent_2 == private_key["exponent_2"]
    assert coefficient == private_key["coefficient"]

    if number_bits:
        assert number_bits // 2 == rsa_bits(private_key["prime_1"])
        assert number_bits // 2 == rsa_bits(private_key["prime_2"])
        assert number_bits == private_key["bits"]

    message = b"Hello World"
    signature = rsa_sign(b"Hello World", private_key)
    result = rsa_verify(signature, private_key)
    result = result.lstrip(b"\0")

    assert result == message

def rsa_private(number_bits):
    """
    Generates a new "random" private with the requested number
    of bits as the base for exponents and modulus.

    This method is extremely time consuming in terms of processor
    and should be used carefully to avoid any problem.

    :type number_bits: int
    :param number_bits: The number of bits that are going to be
    used for the generation of the private key.
    :rtype: Dictionary
    :return: The generated private key structure, may then be used
    for processing or written to a file.
    """

    while True:
        prime_1, prime_2 = rsa_primes(number_bits // 2)
        public_exponent, private_exponent = rsa_exponents(prime_1, prime_2, number_bits // 2)
        if private_exponent > 0: break

    modulus = prime_1 * prime_2
    exponent_1 = private_exponent % (prime_1 - 1)
    exponent_2 = private_exponent % (prime_2 - 1)
    coefficient = calc.modinv(prime_2, prime_1)
    bits = rsa_bits(modulus)

    private_key = dict(
        version = 0,
        modulus = modulus,
        public_exponent = public_exponent,
        private_exponent = private_exponent,
        prime_1 = prime_1,
        prime_2 = prime_2,
        exponent_1 = exponent_1,
        exponent_2 = exponent_2,
        coefficient = coefficient,
        bits = bits
    )

    return private_key

def rsa_primes(number_bits):
    """
    Generates two different prime numbers (p and q values)
    and returns them inside a tuple structure.

    The generation is made according to the number of bits
    defined and using a trial and error strategy (expensive).

    :type number_bits: int
    :param number_bits: The number of bits to be used in
    prime generation, this affects security.
    :rtype: Tuple
    :return: A tuple containing the two different prime
    numbers to be returned.
    """

    # calculates the total number of bits for the key as
    # the double of the requested for the primes generation
    total_bits = number_bits * 2

    # constructs the clojure based function that is going to
    # be used as the validator of the primes combination, this
    # used for a trial an error based approach for the generation
    # of the primes to be used in the private key
    def rsa_acceptable(prime_1, prime_2):
        if prime_1 == prime_2: return False
        modulus_bits = rsa_bits(prime_1 * prime_2)
        return modulus_bits == total_bits

    # generates the "first" version of both prime values
    # that is going to serve as the first iteration of
    # each of the values, and start the is odd variable
    prime_1 = calc.prime(number_bits)
    prime_2 = calc.prime(number_bits)
    is_odd = True

    # iterates continuously trying to find a combination
    # of prime numbers that is acceptable and valid
    while True:
        if rsa_acceptable(prime_1, prime_2): break
        if is_odd: prime_1 = calc.prime(number_bits)
        else: prime_2 = calc.prime(number_bits)

    # returns a tuple containing both of the generated
    # primes and returns it to the caller method
    return (prime_1, prime_2)

def rsa_exponents(prime_1, prime_2, number_bits, basic = True):
    """
    Generates both the public and the private exponents for
    the rsa cryptography system taking as base the provided
    prime numbers and the amount of bits for the values.

    :type prime_1: int
    :param prime_1: The first prime number use for rsa.
    :type prime_2: int
    :param prime_2: The second prime number use for rsa.
    :type number_bits: int
    :param number_bits: The number of bits that are going to be
    used for the generation of the values.
    :type basic: bool
    :param basic: If the basic approach to the generation of the
    public exponent should be taken into account.
    :rtype: Tuple
    :return: The tuple containing the generated public and
    private keys (properly tested).
    """

    # calculates the modulus and the phi value for the
    # modulus, as the y are going to be used for calculus
    modulus = prime_1 * prime_2
    phi_modulus = (prime_1 - 1) * (prime_2 - 1)

    # starts by setting the is first flag so that the first iteration
    # of the public exponent generation cycle is taking into account
    # the possible basic flag value for the public exponent
    is_first = True

    # iterates continuously to find a valid public exponent, one
    # that satisfies the relative prime
    while True:
        # make sure e has enough bits so we ensure "wrapping" through
        # modulus (n value) note that if the this is the first attempt
        # to create a public exponent and the basic mode is active the
        # number chosen is the "magic" number (compatibility)
        public_exponent = calc.prime(max(8, number_bits // 2))
        if is_first and basic: public_exponent = 65537; is_first = False

        # checks if the exponent and the modulus are relative primes
        # and also checks if the exponent and the phi modulus are relative
        # primes, for that situation a valid public exponent has been fond
        # and the cycle may be broken
        is_relative = calc.relatively_prime(public_exponent, modulus)
        is_relative_phi = calc.relatively_prime(public_exponent, phi_modulus)
        if is_relative and is_relative_phi: break

    # retrieves the result of the extended euclid greatest common divisor,
    # this value is going to be used as the basis for the calculus of the
    # private exponent for the current operation
    d, l, _e = calc.egcd(public_exponent, phi_modulus)
    private_exponent = l

    # in case the greatest common divisor between both is not one, the values
    # are not relative primes and an exception must be raised
    if not d == 1: raise netius.GeneratorError(
        "The public exponent '%d' and the phi modulus '%d' are not relative primes" %
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

def rsa_bits(modulus):
    bits = math.log(modulus, 2)
    return calc.ceil_integer(bits)

def rsa_sign(message, private_key):
    message = netius.legacy.bytes(message)
    modulus = private_key["modulus"]
    private_exponent = private_key["private_exponent"]
    return rsa_crypt_s(message, private_exponent, modulus)

def rsa_verify(signature, public_key):
    signature = netius.legacy.bytes(signature)
    modulus = public_key["modulus"]
    public_exponent = public_key["public_exponent"]
    return rsa_crypt_s(signature, public_exponent, modulus)

def rsa_crypt_s(message, exponent, modulus):
    modulus_l = calc.ceil_integer(math.log(modulus, 256))

    message_i = util.bytes_to_integer(message)
    message_crypt = rsa_crypt(message_i, exponent, modulus)
    message_crypt_s = util.integer_to_bytes(message_crypt, modulus_l)

    return message_crypt_s

def rsa_crypt(number, exponent, modulus):
    if not type(number) in netius.legacy.INTEGERS:
        raise TypeError("you must pass a long or an int")

    if number > 0 and math.floor(math.log(number, 2)) > math.floor(math.log(modulus, 2)):
        raise OverflowError("the message is too long")

    return pow(number, exponent, modulus)
