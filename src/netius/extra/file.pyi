from re import Pattern
from typing import Any, Callable, Iterator, Mapping, Sequence

from netius import Connection, Stream
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser
from netius.servers import HTTP2Server, HTTPConnection

BUFFER_SIZE: int
FOLDER_SVG: str
FILE_SVG: str
EMPTY_GIF: str

class FileServer(HTTP2Server):
    base_path: str
    style_urls: Sequence[str]
    index_files: Sequence[str]
    path_regex: Sequence[tuple[str | Pattern[str], str]]
    list_dirs: bool
    list_engine: str
    cors: bool
    cache: int
    follow_links: bool

    def __init__(
        self,
        base_path: str = ...,
        style_urls: Sequence[str] = ...,
        index_files: Sequence[str] = ...,
        path_regex: Sequence[tuple[str, str]] = ...,
        list_dirs: bool = ...,
        list_engine: str = ...,
        cors: bool = ...,
        cache: int = ...,
        follow_links: bool = ...,
        *args,
        **kwargs
    ): ...
    @classmethod
    def _sorter_build(
        cls, name: str | None = ...
    ) -> Callable[[Mapping[str, Any]], tuple[Any, Any]]: ...
    @classmethod
    def _items_normalize(
        cls,
        items: Sequence[str],
        path: str,
        pad: bool = ...,
        space: bool = ...,
        simplified: bool = ...,
    ) -> list[dict[str, Any]]: ...
    @classmethod
    def _gen_dir(
        cls,
        engine: str,
        path: str,
        path_v: str,
        query_m: Mapping[str, Sequence[str]],
        style: bool = ...,
        style_urls: Sequence[str] = ...,
        **kwargs
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_dir_base(
        cls,
        path: str,
        path_v: str,
        query_m: Mapping[str, Sequence[str]],
        style: bool = ...,
        style_urls: Sequence[str] = ...,
        **kwargs
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_dir_apache(
        cls, path: str, path_v: str, query_m: Mapping[str, Sequence[str]], **kwargs
    ) -> Iterator[str]: ...
    @classmethod
    def _gen_dir_legacy(
        cls, path: str, path_v: str, query_m: Mapping[str, Sequence[str]], **kwargs
    ) -> Iterator[str]: ...
    def on_connection_d(self, connection: Connection): ...
    def on_stream_d(self, stream: Stream): ...
    def on_serve(self): ...
    def on_data_http(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def on_dir_file(
        self,
        connection: HTTPConnection,
        parser: HTTPParser,
        path: str,
        style: bool = ...,
    ): ...
    def on_normal_file(
        self, connection: HTTPConnection, parser: HTTPParser, path: str
    ): ...
    def on_no_file(self, connection: HTTPConnection): ...
    def on_exception_file(
        self, connection: HTTPConnection, exception: BaseException
    ): ...
    def on_not_modified(self, connection: HTTPConnection, path: str): ...
    def _next_queue(self, connection: HTTPConnection): ...
    def _file_send(self, connection: HTTPConnection): ...
    def _file_finish(self, connection: HTTPConnection): ...
    def _file_close(self, connection: HTTPConnection): ...
    def _file_check_close(self, connection: HTTPConnection): ...
    def _resolve(self, path: str) -> str: ...
    def _build_regex(self): ...
    def _resolve_regex(self, path: str) -> tuple[str, bool]: ...
