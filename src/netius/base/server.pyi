from typing import Any, Mapping

from .common import Base

class Server(Base):
    socket: Any
    host: str | None
    port: int | str | None
    type: int | None
    ssl: bool
    key_file: str | None
    cer_file: str | None
    ca_file: str | None
    env: bool

    def __init__(self, *args, **kwargs): ...
    def welcome(self) -> None: ...
    def cleanup(self) -> None: ...
    def info_dict(self, full: bool = ...) -> Mapping[str, Any]: ...
    def serve(
        self,
        host: str | None = ...,
        port: int | str | None = ...,
        type: int = ...,
        ipv6: bool = ...,
        ssl: bool = ...,
        key_file: str | None = ...,
        cer_file: str | None = ...,
        ca_file: str | None = ...,
        ca_root: bool = ...,
        ssl_verify: bool = ...,
        ssl_host: str | None = ...,
        ssl_fingerprint: str | None = ...,
        ssl_dump: bool = ...,
        setuid: int | None = ...,
        backlog: int = ...,
        load: bool = ...,
        start: bool = ...,
        env: bool = ...,
    ) -> None: ...

class DatagramServer(Server):
    def __init__(self, *args, **kwargs): ...
    def reads(self, reads: list[Any], state: bool = ...) -> None: ...
    def writes(self, writes: list[Any], state: bool = ...) -> None: ...
    def errors(self, errors: list[Any], state: bool = ...) -> None: ...
    def serve(self, type: int = ..., *args, **kwargs) -> None: ...
    def on_read(self, _socket: Any) -> None: ...
