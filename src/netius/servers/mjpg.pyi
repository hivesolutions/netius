from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTP2Server, HTTPConnection

BOUNDARY: str

class MJPGServer(HTTP2Server):
    boundary: str

    def __init__(self, boundary: str = ..., *args, **kwargs): ...
    def on_data_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_send_mjpg(self, connection: HTTPConnection): ...
    def get_delay(self, connection: HTTPConnection) -> float: ...
    def get_image(self, connection: HTTPConnection) -> bytes: ...
