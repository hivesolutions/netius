import netius as netius
import netius.servers.proxy

__version__: str
__revision__: str
__date__: str

class ForwardProxyServer(netius.servers.proxy.ProxyServer):
    def __init__(self, config: str = ..., rules: dict = ..., *args, **kwargs) -> None: ...
    def on_headers(self, connection, parser): ...
    def compile(self): ...
