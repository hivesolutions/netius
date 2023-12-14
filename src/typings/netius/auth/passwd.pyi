import netius.auth.base
import netius.auth.base as base
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class PasswdAuth(netius.auth.base.Auth):
    def __init__(self, path: Incomplete | None = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, username, password, path: str = ..., *args, **kwargs): ...
    @classmethod
    def get_passwd(cls, path, cache: bool = ...): ...
    def auth_i(self, username, password, *args, **kwargs): ...
