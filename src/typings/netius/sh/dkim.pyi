import netius as netius
import netius.sh.base as base
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str
def generate(domain, suffix: Incomplete | None = ..., number_bits: int = ...): ...
def sign(email_path, key_path, selector, domain): ...
