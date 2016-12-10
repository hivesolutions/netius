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

from . import asn
from . import calc
from . import dhcp
from . import dkim
from . import ftp
from . import geo
from . import http
from . import http2
from . import mime
from . import parser
from . import pop
from . import rsa
from . import setup
from . import smtp
from . import socks
from . import tls
from . import stream
from . import structures
from . import tftp
from . import torrent
from . import util
from . import ws

from .asn import asn1_parse, asn1_length, asn1_gen, asn1_build
from .calc import prime, is_prime, relatively_prime, gcd, egcd, modinv,\
    random_integer_interval, random_primality, jacobi_witness, jacobi, ceil_integer
from .dhcp import SUBNET_DHCP, ROUTER_DHCP, DNS_DHCP, NAME_DHCP, BROADCAST_DHCP,\
    REQUESTED_DHCP, LEASE_DHCP, DISCOVER_DHCP, OFFER_DHCP, REQUEST_DHCP, DECLINE_DHCP,\
    ACK_DHCP, NAK_DHCP, IDENTIFIER_DHCP, RENEWAL_DHCP, REBIND_DHCP, PROXY_DHCP,\
    END_DHCP, OPTIONS_DHCP, TYPES_DHCP, VERBS_DHCP, AddressPool
from .dkim import dkim_sign, dkim_headers, dkim_body, dkim_fold, dkim_generate
from .ftp import FTPParser
from .geo import GeoResolver
from .http import REQUEST, RESPONSE, PLAIN_ENCODING, CHUNKED_ENCODING, GZIP_ENCODING,\
    DEFLATE_ENCODING, HTTP_09, HTTP_10, HTTP_11, VERSIONS_MAP, CODE_STRINGS, HTTPParser,\
    HTTPResponse
from .http2 import DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE,\
    PING, GOAWAY, WINDOW_UPDATE, CONTINUATION, HTTP2_WINDOW, HTTP2_PREFACE,\
    HTTP2_TUPLES, HTTP2_NAMES, HTTP2_SETTINGS, HTTP2_SETTINGS_OPTIMAL, HTTP2_SETTINGS_T,\
    HTTP2_SETTINGS_OPTIMAL_T, HTTP2Parser, HTTP2Stream
from .mime import rfc822_parse, rfc822_join, mime_register
from .parser import Parser
from .pop import POPParser
from .rsa import open_pem_key, open_pem_data, write_pem_key, open_private_key, open_private_key_b64,\
    open_private_key_data, open_public_key, open_public_key_b64, open_public_key_data,\
    write_private_key, write_public_key, asn_private_key, asn_public_key, pem_to_der,\
    pem_limiters, private_to_public, assert_private, rsa_private, rsa_primes, rsa_exponents,\
    rsa_bits, rsa_sign, rsa_verify, rsa_crypt_s, rsa_crypt
from .setup import ensure_setup, ensure_ca
from .smtp import SMTPParser
from .socks import SOCKSParser
from .tls import TLSContextDict, LetsEncryptDict
from .stream import Stream, FileStream, FilesStream
from .structures import PriorityDict
from .tftp import RRQ_TFTP, WRQ_TFTP, DATA_TFTP, ACK_TFTP, ERROR_TFTP, TYPES_TFTP
from .torrent import info_hash, bencode, bdecode, chunk, dechunk, TorrentParser
from .util import cstring, chunks, header_down, header_up, is_ip4, is_ip6, assert_ip4,\
    in_subnet_ip4, addr_to_ip4, ip4_to_addr, string_to_bits, integer_to_bytes,\
    bytes_to_integer, random_integer, host, hostname, size_round_unit, verify
from .ws import encode_ws, decode_ws, assert_ws
