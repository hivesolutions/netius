import netius as netius
import netius.base.stream
import netius.common.http as http
import netius.common.parser
import netius.common.parser as parser
from _typeshed import Incomplete
from typing import ClassVar

__version__: str
__revision__: str
__date__: str
HEADER_SIZE: int
SETTING_SIZE: int
DATA: int
HEADERS: int
PRIORITY: int
RST_STREAM: int
SETTINGS: int
PUSH_PROMISE: int
PING: int
GOAWAY: int
WINDOW_UPDATE: int
CONTINUATION: int
PROTOCOL_ERROR: int
INTERNAL_ERROR: int
FLOW_CONTROL_ERROR: int
SETTINGS_TIMEOUT: int
STREAM_CLOSED: int
FRAME_SIZE_ERROR: int
REFUSED_STREAM: int
CANCEL: int
COMPRESSION_ERROR: int
CONNECT_ERROR: int
ENHANCE_YOUR_CALM: int
INADEQUATE_SECURITY: int
HTTP_1_1_REQUIRED: int
SETTINGS_HEADER_TABLE_SIZE: int
SETTINGS_ENABLE_PUSH: int
SETTINGS_MAX_CONCURRENT_STREAMS: int
SETTINGS_INITIAL_WINDOW_SIZE: int
SETTINGS_MAX_FRAME_SIZE: int
SETTINGS_MAX_HEADER_LIST_SIZE: int
HTTP_20: int
HEADER_STATE: int
PAYLOAD_STATE: int
FINISH_STATE: int
HTTP2_WINDOW: int
HTTP2_FRAME_SIZE: int
HTTP2_PREFACE: bytes
HTTP2_PSEUDO: tuple
HTTP2_TUPLES: tuple
HTTP2_NAMES: dict
HTTP2_SETTINGS: dict
HTTP2_SETTINGS_OPTIMAL: dict
HTTP2_SETTINGS_T: list
HTTP2_SETTINGS_OPTIMAL_T: list

class HTTP2Parser(netius.common.parser.Parser):
    FIELDS: ClassVar[tuple] = ...
    def __init__(self, owner, store: bool = ..., file_limit: int = ...) -> None: ...
    def build(self): ...
    def destroy(self): ...
    def info_dict(self): ...
    def info_streams(self): ...
    def reset(self, store: bool = ..., file_limit: int = ...): ...
    def clear(self, force: bool = ..., save: bool = ...): ...
    def close(self): ...
    def parse(self, data): ...
    def get_type_s(self, type): ...
    def assert_header(self): ...
    def assert_stream(self, stream): ...
    def assert_data(self, stream, end_stream): ...
    def assert_headers(self, stream, end_stream): ...
    def assert_priority(self, stream, dependency): ...
    def assert_rst_stream(self, stream): ...
    def assert_settings(self, settings, ack, extended: bool = ...): ...
    def assert_push_promise(self, promised_stream): ...
    def assert_ping(self): ...
    def assert_goaway(self): ...
    def assert_window_update(self, stream, increment): ...
    def assert_continuation(self, stream): ...
    def _parse_header(self, data): ...
    def _parse_payload(self, data): ...
    def _parse_data(self, data): ...
    def _parse_headers(self, data): ...
    def _parse_priority(self, data): ...
    def _parse_rst_stream(self, data): ...
    def _parse_settings(self, data): ...
    def _parse_push_promise(self, data): ...
    def _parse_ping(self, data): ...
    def _parse_goaway(self, data): ...
    def _parse_window_update(self, data): ...
    def _parse_continuation(self, data): ...
    def _has_stream(self, stream): ...
    def _get_stream(self, stream: Incomplete | None = ..., default: Incomplete | None = ..., strict: bool = ..., closed_s: bool = ..., unopened_s: bool = ..., exists_s: bool = ...): ...
    def _set_stream(self, stream): ...
    def _del_stream(self, stream): ...
    def _invalid_type(self): ...
    @property
    def type_s(self): ...
    @property
    def buffer_size(self): ...
    @property
    def buffer_data(self): ...
    @property
    def encoder(self): ...
    @property
    def decoder(self): ...

class HTTP2Stream(netius.base.stream.Stream):
    def __init__(self, identifier: Incomplete | None = ..., header_b: Incomplete | None = ..., dependency: int = ..., weight: int = ..., exclusive: bool = ..., end_headers: bool = ..., end_stream: bool = ..., end_stream_l: bool = ..., store: bool = ..., file_limit: int = ..., window: int = ..., frame_size: int = ..., *args, **kwargs) -> None: ...
    def __getattr__(self, name): ...
    def reset(self, store: bool = ..., file_limit: int = ..., window: int = ..., frame_size: int = ...): ...
    def open(self): ...
    def close(self, flush: bool = ..., destroy: bool = ..., reset: bool = ...): ...
    def info_dict(self, full: bool = ...): ...
    def available(self): ...
    def unavailable(self): ...
    def set_encoding(self, encoding): ...
    def set_uncompressed(self): ...
    def set_plain(self): ...
    def set_chunked(self): ...
    def set_gzip(self): ...
    def set_deflate(self): ...
    def is_plain(self): ...
    def is_chunked(self): ...
    def is_gzip(self): ...
    def is_deflate(self): ...
    def is_compressed(self): ...
    def is_uncompressed(self): ...
    def is_flushed(self): ...
    def is_measurable(self, strict: bool = ...): ...
    def is_exhausted(self): ...
    def is_restored(self): ...
    def decode_headers(self, force: bool = ..., assert_h: bool = ...): ...
    def extend_headers(self, fragment): ...
    def extend_data(self, data): ...
    def remote_update(self, increment): ...
    def local_update(self, increment): ...
    def get_path(self, normalize: bool = ...): ...
    def get_query(self): ...
    def get_message_b(self, copy: bool = ..., size: int = ...): ...
    def get_encodings(self): ...
    def fragment(self, data): ...
    def fragmentable(self, data): ...
    def flush(self, *args, **kwargs): ...
    def flush_s(self, *args, **kwargs): ...
    def send_response(self, *args, **kwargs): ...
    def send_header(self, *args, **kwargs): ...
    def send_part(self, *args, **kwargs): ...
    def send_reset(self, *args, **kwargs): ...
    def assert_headers(self): ...
    def assert_ready(self): ...
    def ctx_request(self, *args, **kwds): ...
    def _calculate(self): ...
    def _calculate_headers(self): ...
    def _build_b(self): ...
    def _build_c(self, callback, validate: bool = ...): ...
    def _parse_query(self, query): ...
    def _decode_params(self, params): ...
    @property
    def parser(self): ...
    @property
    def is_ready(self): ...
    @property
    def is_headers(self): ...
