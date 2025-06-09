from typing import Any

from .observer import Observable
from .transport import Transport

class Service(Observable):
    owner: Any | None
    transport: Transport | None
    socket: Any | None
    host: str | None
    port: Any | None
    ssl: bool
    receive_buffer_s: int | None
    send_buffer_s: int | None
    receive_buffer_c: int | None
    send_buffer_c: int | None

    def __init__(
        self,
        owner: Any | None = ...,
        transport: Transport | None = ...,
        socket: Any | None = ...,
        host: str | None = ...,
        port: Any | None = ...,
        ssl: bool = ...,
        receive_buffer_s: int | None = ...,
        send_buffer_s: int | None = ...,
        receive_buffer_c: int | None = ...,
        send_buffer_c: int | None = ...,
    ): ...
    def on_socket_c(self, socket_c: Any, address: Any) -> None: ...
