import netius as netius
import netius.auth.base
import netius.auth.base as base
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class MemoryAuth(netius.auth.base.Auth):
    def __init__(self, registry: Incomplete | None = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, username, password, registry: Incomplete | None = ..., *args, **kwargs): ...
    @classmethod
    def meta(cls, username, registry: Incomplete | None = ..., *args, **kwargs): ...
    @classmethod
    def get_registry(cls): ...
    @classmethod
    def load_registry(cls): ...
    def auth_i(self, username, password, *args, **kwargs): ...
