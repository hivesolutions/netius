from asyncio import BaseTransport
from typing import Any, Callable, Self

from netius import ClientAgent, StreamProtocol, Transport

class WSProtocol(StreamProtocol):
    MAGIC_VALUE: str
    host: str | None
    port: int | None
    ssl: bool
    path: str | None
    key: str | None
    version: str | None
    code: str | None
    code_s: str | None
    handshake: bool
    buffer_l: list[bytes]
    headers: dict[str, str]

    @classmethod
    def _key(cls, size: int = ...) -> str: ...
    def __init__(self, *args, **kwargs): ...
    def connection_made(self, transport: Transport | BaseTransport): ...
    def on_data(self, data: bytes): ...
    def on_data_ws(self, data: bytes): ...
    def on_handshake(self): ...
    def connect_ws(
        self,
        url: str,
        callback: Callable[[WSProtocol], Any] | None = ...,
        loop: Any = ...,
    ) -> tuple[Any, Self]: ...
    def send_ws(
        self, data: bytes | str, callback: Callable[..., Any] | None = ...
    ) -> int: ...
    def receive_ws(self, decoded: bytes): ...
    def add_buffer(self, data: bytes): ...
    def get_buffer(self, delete: bool = ...) -> bytes: ...
    def do_handshake(self): ...
    def validate_key(self): ...

class WSClient(ClientAgent):
    protocol: type[WSProtocol]

    @classmethod
    def connect_ws_s(
        cls,
        url: str,
        callback: Callable[[WSProtocol], Any] | None = ...,
        loop: Any = ...,
    ) -> tuple[Any, WSProtocol]: ...
