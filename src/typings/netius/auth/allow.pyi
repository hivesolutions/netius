import netius.auth.base
import netius.auth.base as base

__version__: str
__revision__: str
__date__: str

class AllowAuth(netius.auth.base.Auth):
    @classmethod
    def auth(cls, *args, **kwargs): ...
    @classmethod
    def is_simple(cls): ...
