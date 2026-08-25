from socket import socket as _socket
from typing import Any

from netius import Base, Observable, TransportStream

BUFFER_SIZE_S: int | None
BUFFER_SIZE_C: int | None

class Service(Observable):
    id: str
    owner: Base | None
    transport: TransportStream | None
    socket: _socket | None
    host: str | None
    port: int | None
    ssl: bool
    receive_buffer_s: int | None
    send_buffer_s: int | None
    receive_buffer_c: int | None
    send_buffer_c: int | None

    def __init__(
        self,
        owner: Base | None = ...,
        transport: TransportStream | None = ...,
        socket: _socket | None = ...,
        host: str | None = ...,
        port: int | None = ...,
        ssl: bool = ...,
        receive_buffer_s: int | None = ...,
        send_buffer_s: int | None = ...,
        receive_buffer_c: int | None = ...,
        send_buffer_c: int | None = ...,
    ): ...
    def on_socket_c(self, socket_c: _socket, address: Any): ...
