from asyncio import BaseTransport
from typing import Any

from netius import ClientAgent, StreamProtocol, Transport

class APNProtocol(StreamProtocol):
    HOST: str
    PORT: int
    SANDBOX_HOST: str
    SANDBOX_PORT: int
    host: str | None
    port: int | None
    token: str | bytes | None
    message: str | None
    sound: str | None
    badge: int
    sandbox: bool

    def __init__(self, *args, **kwargs): ...
    def connection_made(self, transport: Transport | BaseTransport): ...
    def send_notification(
        self,
        token: str | bytes,
        message: str | None,
        sound: str | None = ...,
        badge: int = ...,
        close: bool = ...,
    ): ...
    def set(
        self,
        token: str | bytes,
        message: str | None,
        sound: str | None = ...,
        badge: int = ...,
        sandbox: bool = ...,
        key_file: str | None = ...,
        cer_file: str | None = ...,
        _close: bool = ...,
    ): ...
    def notify(
        self, token: str | bytes, loop: Any = ..., **kwargs
    ) -> tuple[Any, APNProtocol]: ...

class APNClient(ClientAgent):
    protocol: type[APNProtocol]

    @classmethod
    def notify_s(
        cls, token: str | bytes, loop: Any = ..., **kwargs
    ) -> tuple[Any, APNProtocol]: ...
