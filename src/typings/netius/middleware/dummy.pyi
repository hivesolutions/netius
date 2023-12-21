import netius.middleware.base
from netius.middleware.base import Middleware as Middleware

__version__: str
__revision__: str
__date__: str

class DummyMiddleware(netius.middleware.base.Middleware):
    def start(self): ...
    def stop(self): ...
    def on_connection_c(self, owner, connection): ...
