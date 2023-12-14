import netius.auth.base
import netius.auth.base as base

__version__: str
__revision__: str
__date__: str

class DummyAuth(netius.auth.base.Auth):
    def __init__(self, value: bool = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, value: bool = ..., *args, **kwargs): ...
    @classmethod
    def is_simple(cls): ...
    def auth_i(self, *args, **kwargs): ...
