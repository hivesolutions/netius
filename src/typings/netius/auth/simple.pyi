import netius.auth.base
import netius.auth.base as base
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class SimpleAuth(netius.auth.base.Auth):
    def __init__(self, username: Incomplete | None = ..., password: Incomplete | None = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, username, password, target: Incomplete | None = ..., *args, **kwargs): ...
    def auth_i(self, username, password, *args, **kwargs): ...
