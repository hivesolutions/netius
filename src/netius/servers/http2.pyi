from socket import socket as Socket
from typing import Any, Callable, Iterator, Mapping, Sequence

from netius import Connection, NetiusError
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTPConnection, HTTPServer

class HTTP2Connection(HTTPConnection):
    legacy: bool
    settings: dict[int, int]
    settings_r: dict[int, int]
    window: int
    window_o: int
    window_l: int
    window_t: int
    preface: bool
    preface_b: bytes
    frames: list[tuple[tuple[Any, ...], dict[str, Any]]]
    unavailable: dict[int, bool]

    def __init__(
        self,
        legacy: bool = ...,
        window: int = ...,
        settings: Mapping[int, int] = ...,
        settings_r: Mapping[int, int] = ...,
        *args,
        **kwargs
    ): ...
    def open(self, *args, **kwargs): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def flush_s(
        self,
        stream: int | None = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def set_h2(self): ...
    def parse(self, data: bytes) -> int | None: ...
    def parse_preface(self, data: bytes) -> bytes | None: ...
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
    def send_fragmented(
        self,
        data: bytes,
        stream: int | None = ...,
        final: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
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
    def send_frame(
        self,
        type: int = ...,
        flags: int = ...,
        payload: bytes = ...,
        stream: int | None = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_data(
        self,
        data: bytes = ...,
        end_stream: bool = ...,
        stream: int | None = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_headers(
        self,
        headers: Sequence[tuple[str, str]] = ...,
        end_stream: bool = ...,
        end_headers: bool = ...,
        stream: int | None = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_rst_stream(
        self,
        error_code: int = ...,
        stream: int | None = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_settings(
        self,
        settings: Sequence[tuple[int, int]] = ...,
        ack: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_ping(
        self,
        opaque: bytes = ...,
        ack: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_goaway(
        self,
        last_stream: int = ...,
        error_code: int = ...,
        message: str = ...,
        close: bool = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_window_update(
        self,
        increment: int = ...,
        stream: int | None = ...,
        delay: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int: ...
    def send_delta(self): ...
    def delay_frame(self, *args, **kwargs) -> int: ...
    def split_frame(
        self, frame: tuple[tuple[Any, ...], dict[str, Any]], size: int
    ) -> int: ...
    def flush_frames(self, all: bool = ...) -> bool: ...
    def flush_available(self): ...
    def set_settings(self, settings: Mapping[int, int]): ...
    def close_stream(
        self,
        stream: int | None,
        final: bool = ...,
        flush: bool = ...,
        reset: bool = ...,
    ): ...
    def available_stream(
        self, stream: int | None, length: int, strict: bool = ...
    ) -> bool: ...
    def partial_stream(self, stream: int | None, length: int) -> int: ...
    def fragment_stream(self, stream: int | None, data: bytes) -> Iterator[bytes]: ...
    def fragmentable_stream(self, stream: int | None, data: bytes) -> bool: ...
    def open_stream(self, stream: int | None) -> bool: ...
    def try_available(self, stream: int | None, strict: bool = ...): ...
    def try_unavailable(self, stream: int | None, strict: bool = ...): ...
    def increment_remote(self, stream: int | None, increment: int, all: bool = ...): ...
    def increment_local(self, stream: int | None, increment: int): ...
    def error_connection(
        self,
        last_stream: int = ...,
        error_code: int = ...,
        message: str = ...,
        close: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ): ...
    def error_stream(
        self,
        stream: int | None,
        last_stream: int = ...,
        error_code: int = ...,
        message: str = ...,
        close: bool = ...,
        callback: Callable[[Connection], Any] | None = ...,
    ) -> int | None: ...
    def on_header(self, header: tuple[int, int, int, int, int]): ...
    def on_payload(self): ...
    def on_frame(self): ...
    def on_data_h2(self, stream: HTTP2Stream | None, contents: bytes): ...
    def on_headers_h2(self, stream: HTTP2Stream): ...
    def on_rst_stream(self, stream: HTTP2Stream | None, error_code: int): ...
    def on_settings(self, settings: Sequence[tuple[int, int]], ack: int): ...
    def on_ping(self, opaque: bytes, ack: int): ...
    def on_goaway(self, last_stream: int, error_code: int, extra: bytes): ...
    def on_window_update(self, stream: HTTP2Stream | None, increment: int): ...
    def on_continuation(self, stream: HTTP2Stream): ...
    def is_throttleable(self) -> bool: ...
    @property
    def connection_ctx(self) -> HTTP2Connection | HTTP2Stream: ...  # type: ignore[override]
    @property
    def parser_ctx(  # type: ignore[override]
        self,
    ) -> HTTPParser | HTTP2Parser | HTTP2Stream | None: ...
    def _build_c(
        self,
        callback: Callable[[Connection], Any] | None,
        stream: int | None,
        data_l: int,
    ) -> Callable[[Connection], Any] | None: ...
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

class HTTP2Server(HTTPServer):
    legacy: bool
    safe: bool
    settings: dict[int, int]
    settings_t: list[tuple[int, int]]
    has_h2: bool
    has_all_h2: bool

    def __init__(
        self,
        legacy: bool = ...,
        safe: bool = ...,
        settings: dict[int, int] = ...,
        *args,
        **kwargs
    ): ...
    @classmethod
    def _has_hpack(cls) -> bool: ...
    @classmethod
    def _has_alpn(cls) -> bool: ...
    @classmethod
    def _has_npn(cls) -> bool: ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def get_protocols(self) -> list[str]: ...
    def build_connection(  # type: ignore[override]
        self,
        socket: Socket,
        address: tuple[str, int] | str | None,
        ssl: bool = ...,
    ) -> HTTP2Connection: ...
    def on_exception(self, exception: BaseException, connection: Connection): ...
    def on_ssl(self, connection: Connection): ...
    def on_serve(self): ...
    def on_preface_http2(self, connection: HTTP2Connection, parser: HTTP2Parser): ...
    def on_header_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        header: tuple[int, int, int, int, int],
    ): ...
    def on_payload_http2(self, connection: HTTP2Connection, parser: HTTP2Parser): ...
    def on_frame_http2(self, connection: HTTP2Connection, parser: HTTP2Parser): ...
    def on_data_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        stream: HTTP2Stream | None,
        contents: bytes,
    ): ...
    def on_headers_http2(
        self, connection: HTTP2Connection, parser: HTTP2Parser, stream: HTTP2Stream
    ): ...
    def on_rst_stream_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        stream: HTTP2Stream | None,
        error_code: int,
    ): ...
    def on_settings_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        settings: Sequence[tuple[int, int]],
        ack: int,
    ): ...
    def on_ping_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        opaque: bytes,
        ack: int,
    ): ...
    def on_goaway_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        last_stream: int,
        error_code: int,
        extra: bytes,
    ): ...
    def on_window_update_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        stream: HTTP2Stream | None,
        increment: int,
    ): ...
    def on_continuation_http2(
        self, connection: HTTP2Connection, parser: HTTP2Parser, stream: HTTP2Stream
    ): ...
    def on_send_http2(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        type: int,
        flags: int,
        payload: bytes,
        stream: int | None,
    ): ...
    def _has_h2(self) -> bool: ...
    def _has_all_h2(self) -> bool: ...
    def _handle_exception(
        self, exception: NetiusError, connection: HTTP2Connection
    ): ...
    def _log_frame(self, connection: HTTP2Connection, parser: HTTP2Parser): ...
    def _log_error(self, error_code: int, extra: bytes): ...
    def _log_send(
        self,
        connection: HTTP2Connection,
        parser: HTTP2Parser,
        type: int,
        flags: int,
        payload: bytes,
        stream: int | None,
    ): ...
    def _log_window(
        self, parser: HTTP2Parser, stream: int | None, remote: bool = ...
    ): ...
    def _log_frame_details(
        self,
        parser: HTTP2Parser,
        type_s: str,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _log_frame_flags(self, type_s: str, *args): ...
    def _log_frame_data(
        self,
        parser: HTTP2Parser,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _log_frame_headers(
        self,
        parser: HTTP2Parser,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _log_frame_rst_stream(
        self,
        parser: HTTP2Parser,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _log_frame_goaway(
        self,
        parser: HTTP2Parser,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _log_frame_window_update(
        self,
        parser: HTTP2Parser,
        flags: int,
        payload: bytes,
        stream: int | None,
        out: bool,
    ): ...
    def _flags_l(
        self, flags: int, definition: Sequence[tuple[str, int]]
    ) -> list[str]: ...
