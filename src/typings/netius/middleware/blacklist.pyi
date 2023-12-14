import netius as netius
import netius.middleware.base
from _typeshed import Incomplete
from netius.middleware.base import Middleware as Middleware

__version__: str
__revision__: str
__date__: str

class BlacklistMiddleware(netius.middleware.base.Middleware):
    def __init__(self, owner, blacklist: Incomplete | None = ..., whitelist: Incomplete | None = ...) -> None: ...
    def start(self): ...
    def stop(self): ...
    def on_connection_c(self, owner, connection): ...
