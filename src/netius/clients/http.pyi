from asyncio import AbstractEventLoop, BaseTransport
from typing import IO, Any, Callable, Iterator, Mapping, Self, Sequence

from netius import ClientAgent, CompatLoop, Protocol, StreamProtocol, Transport
from netius.base.common import AbstractBase
from netius.common import HTTPParser, HTTPResponse

Z_PARTIAL_FLUSH: int
DECODINGS: tuple[str, ...]

class HTTPProtocol(StreamProtocol):
    BASE_HEADERS: dict[str, str]
    parser: HTTPParser | None

    def __init__(
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = ...,
        headers: dict[str, Any] | None = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        version: str = ...,
        encoding: int = ...,
        encodings: str | None = ...,
        safe: bool = ...,
        request: bool = ...,
        asynchronous: bool = ...,
        timeout: float | None = ...,
        use_file: bool = ...,
        callback: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_init: Callable[[HTTPProtocol], Any] | None = ...,
        on_open: Callable[[HTTPProtocol], Any] | None = ...,
        on_close: Callable[[HTTPProtocol], Any] | None = ...,
        on_headers: Callable[[HTTPProtocol, HTTPParser], Any] | None = ...,
        on_data: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_result: (
            Callable[[HTTPProtocol, HTTPParser, dict[str, Any]], Any] | None
        ) = ...,
        *args,
        **kwargs
    ): ...
    def __repr__(self) -> str: ...
    @classmethod
    def key_g(cls, url: str) -> tuple[str | None, int, bool]: ...
    @classmethod
    def decode_gzip(cls, data: bytes) -> bytes: ...
    @classmethod
    def decode_deflate(cls, data: bytes) -> bytes: ...
    @classmethod
    def decode_zlib_file(
        cls,
        input: IO[bytes],
        output: IO[bytes],
        buffer_size: int = ...,
        wbits: int = ...,
    ) -> IO[bytes]: ...
    @classmethod
    def decode_gzip_file(
        cls,
        input: IO[bytes],
        output: IO[bytes],
        buffer_size: int = ...,
        wbits: int = ...,
    ) -> IO[bytes]: ...
    @classmethod
    def decode_deflate_file(
        cls,
        input: IO[bytes],
        output: IO[bytes],
        buffer_size: int = ...,
        wbits: int = ...,
    ) -> IO[bytes]: ...
    @classmethod
    def set_request(
        cls,
        parser: HTTPParser,
        buffer: Sequence[bytes],
        request: dict[str, Any] | None = ...,
    ) -> dict[str, Any]: ...
    @classmethod
    def set_request_file(
        cls,
        parser: HTTPParser,
        input: IO[bytes],
        request: dict[str, Any] | None = ...,
        output: IO[bytes] | None = ...,
        buffer_size: int = ...,
    ) -> dict[str, Any]: ...
    @classmethod
    def set_error(
        cls,
        error: str,
        message: str | None = ...,
        request: dict[str, Any] | None = ...,
        force: bool = ...,
    ) -> dict[str, Any] | None: ...
    def open_c(self, *args, **kwargs): ...
    def close_c(self, *args, **kwargs): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def connection_made(self, transport: Transport | BaseTransport): ...
    def loop_set(self, loop: Any): ...
    def flush(self, force: bool = ..., callback: Callable[..., Any] | None = ...): ...
    def send_base(
        self,
        data: bytes | str | None,
        stream: Any = ...,
        final: bool = ...,
        delay: bool = ...,
        force: bool = ...,
        callback: Callable[..., Any] | None = ...,
    ) -> int | None: ...
    def send_plain(
        self,
        data: bytes | str | None,
        stream: Any = ...,
        final: bool = ...,
        delay: bool = ...,
        force: bool = ...,
        callback: Callable[..., Any] | None = ...,
    ) -> int: ...
    def send_chunked(
        self,
        data: bytes | str | None,
        stream: Any = ...,
        final: bool = ...,
        delay: bool = ...,
        force: bool = ...,
        callback: Callable[..., Any] | None = ...,
    ) -> int: ...
    def send_gzip(
        self,
        data: bytes | str | None,
        stream: Any = ...,
        final: bool = ...,
        delay: bool = ...,
        force: bool = ...,
        callback: Callable[..., Any] | None = ...,
        level: int = ...,
    ) -> int: ...
    def set(
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = ...,
        headers: dict[str, Any] | None = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        version: str = ...,
        encoding: int = ...,
        encodings: str | None = ...,
        safe: bool = ...,
        request: bool = ...,
        asynchronous: bool = ...,
        timeout: float | None = ...,
        use_file: bool = ...,
        callback: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_init: Callable[[HTTPProtocol], Any] | None = ...,
        on_open: Callable[[HTTPProtocol], Any] | None = ...,
        on_close: Callable[[HTTPProtocol], Any] | None = ...,
        on_headers: Callable[[HTTPProtocol, HTTPParser], Any] | None = ...,
        on_data: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_result: (
            Callable[[HTTPProtocol, HTTPParser, dict[str, Any]], Any] | None
        ) = ...,
    ) -> Self: ...
    def set_all(self): ...
    def set_static(self): ...
    def set_timeout(self, callable: Callable[[], Any]): ...
    def unset_timeout(self): ...
    def set_dynamic(self): ...
    def run_request(self): ...
    def send_request(self, callback: Callable[..., Any] | None = ...) -> int | None: ...
    def wrap_request(
        self,
        use_file: bool = ...,
        callback: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_close: Callable[[HTTPProtocol], Any] | None = ...,
        on_data: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_result: (
            Callable[[HTTPProtocol, HTTPParser, dict[str, Any]], Any] | None
        ) = ...,
    ) -> tuple[
        dict[str, Any],
        Callable[[HTTPProtocol], Any],
        Callable[[HTTPProtocol, HTTPParser, bytes], Any],
        Callable[[HTTPProtocol, HTTPParser, bytes], Any],
    ]: ...
    def set_headers(self, headers: dict[str, Any], normalize: bool = ...): ...
    def normalize_headers(self): ...
    def parse(self, data: bytes) -> int: ...
    def raw_data(self, data: bytes) -> bytes: ...
    def is_plain(self) -> bool: ...
    def is_chunked(self) -> bool: ...
    def is_gzip(self) -> bool: ...
    def is_deflate(self) -> bool: ...
    def is_compressed(self) -> bool: ...
    def is_uncompressed(self) -> bool: ...
    def is_flushed(self) -> bool: ...
    def is_measurable(self, strict: bool = ...) -> bool: ...
    def on_data(self, data: bytes): ...
    def _on_data(self): ...
    def on_partial(self, data: bytes): ...
    def on_headers(self): ...
    def on_chunk(self, range: tuple[int, int]): ...
    def _flush_plain(
        self, force: bool = ..., callback: Callable[..., Any] | None = ...
    ): ...
    def _flush_chunked(
        self, force: bool = ..., callback: Callable[..., Any] | None = ...
    ): ...
    def _flush_gzip(
        self, force: bool = ..., callback: Callable[..., Any] | None = ...
    ): ...
    def _close_gzip(self, safe: bool = ...): ...
    def _apply_base(self, headers: dict[str, Any], replace: bool = ...): ...
    def _apply_dynamic(self, headers: dict[str, Any]): ...
    def _apply_connection(self, headers: dict[str, Any], strict: bool = ...): ...
    def _headers_normalize(self, headers: dict[str, Any]): ...

class HTTPClient(ClientAgent):
    protocol: type[HTTPProtocol]
    auto_release: bool
    available: dict[tuple[str | None, int, bool], HTTPProtocol]

    def __init__(self, auto_release: bool = ..., *args, **kwargs): ...
    @classmethod
    def get_s(
        cls,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    @classmethod
    def post_s(
        cls,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    @classmethod
    def put_s(
        cls,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    @classmethod
    def delete_s(
        cls,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    @classmethod
    def method_s(
        cls,
        method: str,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        version: str = ...,
        safe: bool = ...,
        asynchronous: bool = ...,
        daemon: bool = ...,
        timeout: float | None = ...,
        ssl_verify: bool = ...,
        use_file: bool = ...,
        callback: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_init: Callable[[HTTPProtocol], Any] | None = ...,
        on_open: Callable[[HTTPProtocol], Any] | None = ...,
        on_close: Callable[[HTTPProtocol], Any] | None = ...,
        on_headers: Callable[[HTTPProtocol, HTTPParser], Any] | None = ...,
        on_data: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_result: (
            Callable[[HTTPProtocol, HTTPParser, dict[str, Any]], Any] | None
        ) = ...,
        http_client: HTTPClient | None = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    @classmethod
    def to_response(
        cls, map: Mapping[str, Any], raise_e: bool = ...
    ) -> HTTPResponse: ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def cleanup(self): ...
    def get(
        self,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    def post(
        self,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    def put(
        self,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    def delete(
        self,
        url: str,
        params: Mapping[str, Any] = ...,
        headers: dict[str, Any] = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    def method(
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] | None = ...,
        headers: dict[str, Any] | None = ...,
        data: bytes | str | IO[bytes] | Iterator[int | bytes] | None = ...,
        version: str = ...,
        encoding: int = ...,
        encodings: str | None = ...,
        safe: bool = ...,
        request: bool = ...,
        close: bool = ...,
        asynchronous: bool = ...,
        protocol: HTTPProtocol | None = ...,
        timeout: float | None = ...,
        ssl_verify: bool = ...,
        use_file: bool = ...,
        callback: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_init: Callable[[HTTPProtocol], Any] | None = ...,
        on_open: Callable[[HTTPProtocol], Any] | None = ...,
        on_close: Callable[[HTTPProtocol], Any] | None = ...,
        on_headers: Callable[[HTTPProtocol, HTTPParser], Any] | None = ...,
        on_data: Callable[[HTTPProtocol, HTTPParser, bytes], Any] | None = ...,
        on_result: (
            Callable[[HTTPProtocol, HTTPParser, dict[str, Any]], Any] | None
        ) = ...,
        loop: Any = ...,
        **kwargs
    ) -> tuple[Any, HTTPProtocol] | dict[str, Any] | None: ...
    def _relay_protocol_events(self, protocol: Protocol): ...
    def _get_loop(
        self, **kwargs
    ) -> AbstractBase | CompatLoop | AbstractEventLoop | None: ...
    def _close_loop(self): ...

def deflate_wbits(data: bytes) -> int: ...
