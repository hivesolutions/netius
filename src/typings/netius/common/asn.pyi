import netius as netius
import netius.common.util as util

__version__: str
__revision__: str
__date__: str
INTEGER: int
BIT_STRING: int
OCTET_STRING: int
NULL: int
OBJECT_IDENTIFIER: int
SEQUENCE: int
ASN1_OBJECT: list
ASN1_RSA_PUBLIC_KEY: list
ASN1_RSA_PRIVATE_KEY: list
RSAID_PKCS1: bytes
HASHID_SHA1: bytes
HASHID_SHA256: bytes
def asn1_parse(template, data): ...
def asn1_length(length): ...
def asn1_gen(node): ...
def asn1_build(node): ...
