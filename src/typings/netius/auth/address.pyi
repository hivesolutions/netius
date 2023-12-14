import netius.auth.base
import netius.auth.base as base

__version__: str
__revision__: str
__date__: str

class AddressAuth(netius.auth.base.Auth):
    def __init__(self, allowed: list = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, allowed: list = ..., *args, **kwargs): ...
    @classmethod
    def is_simple(cls): ...
    def auth_i(self, *args, **kwargs): ...
