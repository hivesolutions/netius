from typing import Any, Generator, Sequence

INTEGER: int
BIT_STRING: int
OCTET_STRING: int
NULL: int
OBJECT_IDENTIFIER: int
SEQUENCE: int
ASN1_OBJECT: list[tuple[int, list[Any]]]
ASN1_RSA_PUBLIC_KEY: list[tuple[int, list[int]]]
ASN1_RSA_PRIVATE_KEY: list[tuple[int, list[int]]]
RSAID_PKCS1: bytes
HASHID_SHA1: bytes
HASHID_SHA256: bytes

def asn1_parse(template: Sequence[int | tuple[int, Any]], data: bytes) -> list[Any]: ...
def asn1_length(length: int) -> bytes: ...
def asn1_gen(node: tuple[int, Any]) -> bytes: ...
def asn1_build(node: tuple[int, Any]) -> Generator[bytes, None, None]: ...
