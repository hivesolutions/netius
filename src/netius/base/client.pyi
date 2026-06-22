from typing import Any

from .common import Base, BaseThread

class Client(Base):
    _client: "Client | None" = None

    def __init__(self, thread: bool = ..., daemon: bool = ..., *args, **kwargs): ...
    @classmethod
    def get_client_s(cls, *args, **kwargs) -> "Client": ...
    @classmethod
    def cleanup_s(cls) -> None: ...
    def ensure_loop(self, env: bool = ...) -> None: ...
    def join(self, timeout: float | None = ...) -> None: ...
    def connect(
        self,
        host: str,
        port: int,
        ssl: bool = ...,
        key_file: str | None = ...,
        cer_file: str | None = ...,
        ca_file: str | None = ...,
        ca_root: bool = ...,
        ssl_verify: bool = ...,
        family: int = ...,
        type: int = ...,
        ensure_loop: bool = ...,
        env: bool = ...,
    ) -> bool: ...

class DatagramClient(Client):
    def __init__(self, *args, **kwargs): ...
