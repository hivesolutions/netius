from typing import Any, Callable, Iterable, Sequence

from netius import Connection
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTP2Server, HTTPConnection

SERVER_SOFTWARE: str
COMPRESSED_LIMIT: int

class WSGIServer(HTTP2Server):
    app: Callable[
        [dict[str, Any], Callable[[str, Sequence[tuple[str, Any]]], Any]],
        Iterable[Any],
    ]
    mount: str
    mount_l: int
    decode: bool
    compressed_limit: int

    def __init__(
        self,
        app: Callable[
            [dict[str, Any], Callable[[str, Sequence[tuple[str, Any]]], Any]],
            Iterable[Any],
        ],
        mount: str = ...,
        decode: bool = ...,
        compressed_limit: int = ...,
        *args,
        **kwargs
    ): ...
    def on_connection_d(self, connection: Connection): ...
    def on_serve(self): ...
    def on_data_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_environ(
        self, connection: HTTPConnection | HTTP2Stream, environ: dict[str, Any]
    ): ...
    def _next_queue(self, connection: HTTPConnection | HTTP2Stream): ...
    def _start_response(
        self,
        connection: HTTPConnection | HTTP2Stream,
        status: str,
        headers: Sequence[tuple[str, Any]],
    ): ...
    def _send_part(self, connection: HTTPConnection | HTTP2Stream): ...
    def _final(self, connection: HTTPConnection | HTTP2Stream): ...
    def _close(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release_future(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release_iterator(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release_environ(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release_parser(self, connection: HTTPConnection | HTTP2Stream): ...
    def _release_queue(self, connection: HTTPConnection | HTTP2Stream): ...
    def _decode(self, value: str) -> str: ...
