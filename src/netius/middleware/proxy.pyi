from netius import Connection
from netius.base.common import AbstractBase
from netius.middleware import Middleware

class ProxyMiddleware(Middleware):
    MAX_LENGTH: int
    HEADER_LENGTH_V2: int
    HEADER_MAGIC_V2: bytes
    TYPE_LOCAL_V2: int
    TYPE_PROXY_V2: int
    AF_UNSPEC_v2: int
    AF_INET_v2: int
    AF_INET6_v2: int
    AF_UNIX_v2: int
    PROTO_UNSPEC_v2: int
    PROTO_STREAM_v2: int
    PROTO_DGRAM_v2: int
    HANDSHAKE_TIMEOUT: int
    version: int
    handshake_timeout: int

    def __init__(
        self, owner: AbstractBase, version: int = ..., handshake_timeout: int = ...
    ): ...
    def start(self): ...
    def stop(self): ...
    def on_connection_c(self, owner: AbstractBase, connection: Connection): ...
    def _proxy_timeout(self, connection: Connection): ...
    def _proxy_handshake_v1(self, connection: Connection): ...
    def _proxy_handshake_v2(self, connection: Connection): ...
    def _read_safe(
        self, connection: Connection, buffer: bytearray, count: int
    ) -> bytes | None: ...
