from re import Pattern
from socket import socket as Socket
from typing import Any, Mapping, Sequence

from netius import Connection, Container, Protocol, Stream
from netius.clients import HTTPClient, RawClient
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTP2Server, HTTPConnection
from netius.servers.http2 import HTTP2Connection

BUFFER_RATIO: float
MIN_RATIO: float
MAX_PENDING: int
CONNECT_PORTS: tuple[int, ...]
PORT_REGEX: Pattern[str]
HOP_HEADERS: tuple[str, ...]
COMPRESS_TIMEOUT: float

class ProxyConnection(HTTP2Connection):
    def open(self, *args, **kwargs): ...
    def resolve_encoding(self, parser: HTTPParser | HTTP2Stream): ...
    def set_h2(self): ...
    def on_headers(self): ...
    def on_partial(self, data: bytes): ...
    def on_available(self): ...
    def on_unavailable(self): ...

class ProxyServer(HTTP2Server):
    dynamic: bool
    throttle: bool
    trust_origin: bool
    max_pending: int
    min_pending: int
    compress_forward_accept: bool
    compress_buffer: bool
    compress_timeout: float
    connect_ports: Sequence[int]
    conn_map: dict[Any, Any]
    http_client: HTTPClient | None
    raw_client: RawClient | None
    container: Container | None

    def __init__(
        self,
        dynamic: bool = ...,
        throttle: bool = ...,
        trust_origin: bool = ...,
        max_pending: int = ...,
        compress_forward_accept: bool = ...,
        compress_buffer: bool = ...,
        compress_timeout: float = ...,
        connect_ports: Sequence[int] = ...,
        *args,
        **kwargs
    ): ...
    def start(self): ...
    def stop(self): ...
    def cleanup(self): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def connections_dict(  # type: ignore[override]
        self, full: bool = ..., parent: bool = ...
    ) -> dict[str, Any] | list[dict[str, Any]]: ...
    def connection_dict(self, id: str, full: bool = ...) -> dict[str, Any] | None: ...
    def tunnel(
        self,
        connection: HTTPConnection | HTTP2Stream,
        host: str,
        port: int,
        ssl: bool = ...,
        data: bytes | None = ...,
        response: tuple[int, str] | None = ...,
    ) -> Connection | Protocol: ...
    def reason_connection(self, _connection: Connection | Protocol, reason: str): ...
    def pair_connection(self, _connection: Connection | Protocol): ...
    def is_upgrade(self, parser: HTTPParser | HTTP2Stream) -> bool: ...
    def on_data(self, connection: Connection, data: bytes): ...
    def on_connection_d(self, connection: Connection): ...
    def on_stream_d(self, stream: Stream): ...
    def on_serve(self): ...
    def on_data_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_headers(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_partial(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        data: bytes,
    ): ...
    def on_available(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_unavailable(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def build_connection(  # type: ignore[override]
        self,
        socket: Socket,
        address: tuple[str, int] | str | None,
        ssl: bool = ...,
    ) -> ProxyConnection: ...
    def _throttle(self, _connection: Any): ...
    def _prx_close(self, connection: Connection | HTTP2Stream): ...
    def _prx_keep(self, connection: Connection | HTTP2Stream): ...
    def _prx_throttle(self, connection: Connection | HTTP2Stream | None): ...
    def _prx_encoding(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser,
        headers: dict[str, str | Sequence[str]],
        content_encoding: str | None,
    ) -> dict[str, Any] | None: ...
    def _prx_header(
        self,
        headers: Mapping[str, str | Sequence[str]],
        name: str,
        join: bool = ...,
    ) -> str | None: ...
    def _prx_authority(self, path: str) -> tuple[str | None, int | None]: ...
    def _prx_decodable(self, content_encoding: str) -> bool: ...
    def _prx_codec(self, encodings: Sequence[str]) -> dict[str, Any] | None: ...
    def _prx_compress(
        self, connection: HTTPConnection | HTTP2Stream, codec: dict[str, Any]
    ): ...
    def _prx_hold(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser,
        headers: dict[str, str | Sequence[str]],
        codec: dict[str, Any],
        version_s: str,
        code_s: str,
        status_s: str,
    ): ...
    def _prx_release(
        self,
        connection: HTTPConnection | HTTP2Stream,
        codec: dict[str, Any] | None = ...,
        length: int | None = ...,
    ): ...
    def _raw_throttle(self, connection: Connection | None): ...
    def _on_prx_headers(
        self,
        client: HTTPClient,
        parser: HTTPParser,
        headers: Mapping[str, str | Sequence[str]],
    ): ...
    def _on_prx_message(
        self, client: HTTPClient, parser: HTTPParser, message: bytes
    ): ...
    def _on_prx_partial(self, client: HTTPClient, parser: HTTPParser, data: bytes): ...
    def _on_prx_connect(
        self, client: HTTPClient, _connection: Connection | Protocol
    ): ...
    def _on_prx_acquire(
        self, client: HTTPClient, _connection: Connection | Protocol
    ): ...
    def _on_prx_close(self, client: HTTPClient, _connection: Connection | Protocol): ...
    def _on_prx_error(
        self,
        client: HTTPClient,
        _connection: Connection | Protocol,
        error: BaseException,
    ): ...
    def _on_raw_connect(
        self, client: RawClient, _connection: Connection | Protocol
    ): ...
    def _on_raw_data(
        self, client: RawClient, _connection: Connection | Protocol, data: bytes
    ): ...
    def _on_raw_close(self, client: RawClient, _connection: Connection | Protocol): ...
    def _apply_headers(
        self,
        parser: HTTPParser | HTTP2Stream | None,
        connection: HTTPConnection | HTTP2Stream,
        parser_prx: HTTPParser,
        headers: dict[str, str | Sequence[str]],
        upper: bool = ...,
    ): ...
    def _apply_accept(self, headers: dict[str, str | Sequence[str]]): ...
    def _apply_hop(self, headers: dict[str, str | Sequence[str]]): ...
    def _apply_via(
        self, parser_prx: HTTPParser, headers: dict[str, str | Sequence[str]]
    ): ...
