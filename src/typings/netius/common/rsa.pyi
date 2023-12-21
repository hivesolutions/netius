import netius as netius
import netius.common.asn as asn
import netius.common.calc as calc
import netius.common.util as util
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str
PRIVATE_TOKEN: str
PUBLIC_TOKEN: str
def open_pem_key(path, token: str = ...): ...
def open_pem_data(data, token: str = ...): ...
def write_pem_key(path, data, token: str = ..., width: int = ...): ...
def open_private_key(path): ...
def open_private_key_b64(data_b64): ...
def open_private_key_data(data): ...
def open_public_key(path): ...
def open_public_key_b64(data_b64): ...
def open_public_key_data(data): ...
def write_private_key(path, private_key): ...
def write_public_key(path, public_key): ...
def asn_private_key(private_key): ...
def asn_public_key(public_key): ...
def pem_to_der(in_path, out_path, token: str = ...): ...
def pem_limiters(token): ...
def private_to_public(private_key): ...
def assert_private(private_key, number_bits: Incomplete | None = ...): ...
def rsa_private(number_bits): ...
def rsa_primes(number_bits): ...
def rsa_exponents(prime_1, prime_2, number_bits, basic: bool = ...): ...
def rsa_bits(modulus): ...
def rsa_sign(message, private_key): ...
def rsa_verify(signature, public_key): ...
def rsa_crypt_s(message, exponent, modulus): ...
def rsa_crypt(number, exponent, modulus): ...
