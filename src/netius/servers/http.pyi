from contextlib import contextmanager
from socket import socket as Socket
from typing import Any, BinaryIO, Callable, Iterator, Sequence

from netius import Auth, Connection, ParserError, StreamServer
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser

Z_PARTIAL_FLUSH: int
GZIP_LEVEL: int
COMPRESS_FLUSH: int
IDLE_TIMEOUT: int
REQUESTS_LIMIT: int
EMPTY_CODES: tuple[int, ...]
COMPRESS_MIN: int
COMPRESS_MAX: int
COMPRESS_TYPES: list[str]
COMPRESS_DENY: tuple[str, ...]
COMPRESS_ENCODINGS: list[str]
ENCODING_MAP: dict[str, int]
CODECS: dict[str, dict[str, Any]]

def register_codec(
    name: str, wbits: int, encoding: int, factory: Callable[..., Any] = ...
): ...

class HTTPConnection(Connection):
    encoding: int
    current: int
    encoding_c: str | None
    encodings_a: Sequence[str] | None
    dynamic: bool | None
    parser: HTTPParser | None
    legacy: bool
    requests: int
    idle_h: tuple[float, int, Callable[[], Any], int, list[bool]] | None
    idle_t: float
    idle_p: bool
    gzip_m: dict[int | None, Any]
    gzip_l: dict[int | None, int]

    def __init__(self, encoding: int = ..., *args, **kwargs): ...
    def open(self, *args, **kwargs): ...
    def close(self, *args, **kwargs): ...
    def set_idle(self): ...
    def unset_idle(self): ...
    def close_idle(self): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def flush(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def flush_s(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def send_base(
        self,
        data: bytes | str | None,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int | None: ...
    def send_plain(
        self,
        data: bytes | str | None,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_chunked(
        self,
        data: bytes | None,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_gzip(
        self,
        data: bytes | None,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
        level: int | None = ...,
    ) -> int: ...
    def send_response(
        self,
        data: bytes | str | None = ...,
        headers: dict[str, str | Sequence[str]] | None = ...,
        version: str | None = ...,
        code: int = ...,
        code_s: str | None = ...,
        apply: bool = ...,
        stream: int | None = ...,
        final: bool = ...,
        flush: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_header(
        self,
        headers: dict[str, str | Sequence[str]] | None = ...,
        version: str | None = ...,
        code: int = ...,
        code_s: str | None = ...,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_part(
        self,
        data: bytes | str | None,
        stream: int | None = ...,
        final: bool = ...,
        flush: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_error(self, error: ParserError): ...
    def parse(self, data: bytes) -> int | None: ...
    def resolve_encoding(self, parser: HTTPParser | HTTP2Stream): ...
    def base_encoding(self) -> int: ...
    def encoding_w(self) -> int: ...
    def encoding_name(self) -> str | None: ...
    def set_encoding(self, encoding: int): ...
    def set_base(self): ...
    def set_uncompressed(self): ...
    def set_plain(self): ...
    def set_chunked(self): ...
    def set_gzip(self): ...
    def set_deflate(self): ...
    def is_plain(self) -> bool: ...
    def is_chunked(self) -> bool: ...
    def is_gzip(self) -> bool: ...
    def is_deflate(self) -> bool: ...
    def is_compressed(self) -> bool: ...
    def is_uncompressed(self) -> bool: ...
    def is_dynamic(self) -> bool: ...
    def is_flushed(self) -> bool: ...
    def is_measurable(self, strict: bool = ...) -> bool: ...
    def on_data(self): ...
    @contextmanager
    def ctx_request(
        self, args: tuple[Any, ...] | None = ..., kwargs: dict[str, Any] | None = ...
    ) -> Iterator[None]: ...
    @property
    def connection_ctx(self) -> HTTPConnection: ...
    @property
    def parser_ctx(self) -> HTTPParser | None: ...
    def _unset_header(self, headers: dict[str, str | Sequence[str]], name: str): ...
    def _flush_plain(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def _flush_chunked(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def _flush_gzip(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def _get_gzip(
        self, stream: int | None, level: int = ..., ensure: bool = ...
    ) -> Any: ...
    def _set_gzip(self, stream: int | None, gzip: Any): ...
    def _unset_gzip(self, stream: int | None): ...
    def _close_gzip(self, safe: bool = ...): ...

class HTTPServer(StreamServer):
    BASE_HEADERS: dict[str, str]
    encoding_s: str
    encoding: int
    common_log: str | None
    compress_min: int
    compress_max: int
    compress_types: Sequence[str]
    compress_encodings: Sequence[str]
    compress_level: int
    compress_flush: int
    compress_vary: bool
    line_limit: int
    headers_limit: int
    headers_count: int
    chunk_limit: int
    requests_limit: int
    idle_timeout: int
    dynamic: bool
    common_file: BinaryIO | None

    def __init__(
        self,
        encoding: str = ...,
        common_log: str | None = ...,
        compress_min: int = ...,
        compress_max: int = ...,
        compress_types: Sequence[str] = ...,
        compress_encodings: Sequence[str] = ...,
        compress_level: int = ...,
        compress_flush: int = ...,
        compress_vary: bool = ...,
        line_limit: int = ...,
        headers_limit: int = ...,
        headers_count: int = ...,
        chunk_limit: int = ...,
        requests_limit: int = ...,
        idle_timeout: int = ...,
        *args,
        **kwargs
    ): ...
    @classmethod
    def build_data(
        cls,
        text: str,
        url: str | None = ...,
        trace: bool = ...,
        style: bool = ...,
        style_urls: Sequence[str] = ...,
        encode: bool = ...,
        encoding: str = ...,
    ) -> str | bytes: ...
    @classmethod
    def build_text(
        cls,
        text: str,
        trace: bool = ...,
        style: bool = ...,
        style_urls: Sequence[str] = ...,
        encode: bool = ...,
        encoding: str = ...,
    ) -> str | bytes: ...
    @classmethod
    def build_iframe(
        cls,
        text: str,
        url: str,
        style: bool = ...,
        style_urls: Sequence[str] = ...,
        encode: bool = ...,
        encoding: str = ...,
    ) -> str | bytes: ...
    @classmethod
    def _gen_text(
        cls,
        text: str,
        trace: bool = ...,
        style: bool = ...,
        style_urls: Sequence[str] = ...,
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_iframe(
        cls, text: str, url: str, style: bool = ..., style_urls: Sequence[str] = ...
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_header(
        cls,
        title: str,
        meta: bool = ...,
        style: bool = ...,
        style_urls: Sequence[str] = ...,
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_footer(cls) -> Iterator[str]: ...
    @classmethod
    def _gen_style(cls) -> Iterator[str]: ...
    def cleanup(self): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def on_data(self, connection: Connection, data: bytes): ...
    def on_serve(self): ...
    def build_connection(  # type: ignore[override]
        self,
        socket: Socket,
        address: tuple[str, int] | str | None,
        ssl: bool = ...,
    ) -> HTTPConnection: ...
    def on_data_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_send_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        headers: dict[str, str | Sequence[str]] | None = ...,
        version: str | None = ...,
        code: int = ...,
        code_s: str | None = ...,
    ): ...
    def on_flush_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        encoding: int | None = ...,
    ): ...
    def is_auto(self) -> bool: ...
    def is_compressible(self, content_type: str | None) -> bool: ...
    def authorize(
        self,
        connection: HTTPConnection,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream,
        auth: type[Auth] | Auth | None = ...,
        **kwargs
    ) -> bool: ...
    def _apply_all(
        self,
        parser: HTTPParser | HTTP2Parser | None,
        connection: HTTPConnection,
        headers: dict[str, str | Sequence[str]],
        upper: bool = ...,
        normalize: bool = ...,
        replace: bool = ...,
    ): ...
    def _apply_base(
        self, headers: dict[str, str | Sequence[str]], replace: bool = ...
    ): ...
    def _apply_parser(
        self,
        parser: HTTPParser | HTTP2Parser | None,
        headers: dict[str, str | Sequence[str]],
        replace: bool = ...,
    ): ...
    def _apply_connection(
        self,
        connection: HTTPConnection,
        headers: dict[str, str | Sequence[str]],
        strict: bool = ...,
    ): ...
    def _apply_weak(self, headers: dict[str, str | Sequence[str]], name: str): ...
    def _apply_vary(self, headers: dict[str, str | Sequence[str]], value: str): ...
    def _headers_upper(self, headers: dict[str, str | Sequence[str]]): ...
    def _headers_normalize(self, headers: dict[str, str | Sequence[str]]): ...
    def _authorization(
        self, parser: HTTPParser | HTTP2Parser | HTTP2Stream
    ) -> tuple[str | None, str | None]: ...
    def _write_common(self, message: str | bytes, encoding: str = ...): ...
    def _log_request(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        *args,
        **kwargs
    ): ...
    def _log_request_basic(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        output: Callable[[str], Any] | None = ...,
    ): ...
    def _log_request_common(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
        headers: dict[str, str | Sequence[str]] | None = ...,
        version: str | None = ...,
        code: int = ...,
        code_s: str | None = ...,
        size_s: str | None = ...,
        username: str = ...,
        output: Callable[[str], Any] | None = ...,
    ): ...
