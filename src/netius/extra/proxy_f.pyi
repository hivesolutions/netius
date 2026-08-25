from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTPConnection, ProxyServer

class ForwardProxyServer(ProxyServer):
    def __init__(
        self, config: str = ..., rules: dict[str, str] = ..., *args, **kwargs
    ): ...
    def on_headers(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def compile(self): ...
