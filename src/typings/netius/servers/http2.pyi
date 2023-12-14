"""
This type stub file was generated by pyright.
"""

from . import http

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class HTTP2Connection(http.HTTPConnection):
    def __init__(self, legacy=..., window=..., settings=..., settings_r=..., *args, **kwargs) -> None:
        ...
    
    def open(self, *args, **kwargs): # -> None:
        ...
    
    def info_dict(self, full=...): # -> dict[str, Any | None]:
        ...
    
    def flush_s(self, stream=..., callback=...): # -> int | None:
        ...
    
    def set_h2(self): # -> None:
        ...
    
    def parse(self, data): # -> int | Any | None:
        ...
    
    def parse_preface(self, data): # -> None:
        """
        Tries to run the parsing on the preface part of the
        connection establishment using the provided data
        note that the data is buffered in case the proper size
        has not been reached for proper validation.

        This should be the first step when trying to establish
        a proper HTTP 2 connection.

        :type data: String
        :param data: The data buffer that is going to be used to
        try to parse the connection preface.
        :rtype: String
        :return: The resulting data after the preface has been
        parsed, this should be empty or invalid in case no data
        is pending to be parsed.
        """
        ...
    
    def send_plain(self, data, stream=..., final=..., delay=..., callback=...): # -> int:
        ...
    
    def send_chunked(self, data, stream=..., final=..., delay=..., callback=...): # -> int:
        ...
    
    def send_fragmented(self, data, stream=..., final=..., delay=..., callback=...): # -> int:
        ...
    
    def send_response(self, data=..., headers=..., version=..., code=..., code_s=..., apply=..., stream=..., final=..., flush=..., delay=..., callback=...):
        ...
    
    def send_header(self, headers=..., version=..., code=..., code_s=..., stream=..., final=..., delay=..., callback=...): # -> int:
        ...
    
    def send_part(self, data, stream=..., final=..., flush=..., delay=..., callback=...): # -> int | None:
        ...
    
    def send_frame(self, type=..., flags=..., payload=..., stream=..., delay=..., callback=...): # -> int:
        ...
    
    def send_data(self, data=..., end_stream=..., stream=..., delay=..., callback=...): # -> int:
        ...
    
    def send_headers(self, headers=..., end_stream=..., end_headers=..., stream=..., delay=..., callback=...): # -> int:
        ...
    
    def send_rst_stream(self, error_code=..., stream=..., delay=..., callback=...): # -> int:
        ...
    
    def send_settings(self, settings=..., ack=..., delay=..., callback=...): # -> int:
        ...
    
    def send_ping(self, opaque=..., ack=..., delay=..., callback=...): # -> int:
        ...
    
    def send_goaway(self, last_stream=..., error_code=..., message=..., close=..., delay=..., callback=...): # -> int:
        ...
    
    def send_window_update(self, increment=..., stream=..., delay=..., callback=...): # -> int:
        ...
    
    def send_delta(self): # -> None:
        ...
    
    def delay_frame(self, *args, **kwargs): # -> Literal[0]:
        ...
    
    def flush_frames(self, all=...): # -> bool:
        """
        Runs the flush operation on the delayed/pending frames, meaning
        that the window/availability tests are going to be run, checking
        if the various streams and connection are ready for sending the
        frames.

        In case the all flag is active the complete set of frames are going
        to be tested for sending, this operation implies more resource usage.

        This method should be called after a window update frame is
        received so that the pending frames may be sent.

        :type all: bool
        :param all: If the complete set of frames should be tested, or
        if instead at the first testing fail the control flow should be
        returned immediately.
        :rtype: bool
        :return: If all the pending frames have been successfully flushed.
        """
        ...
    
    def flush_available(self): # -> None:
        """
        Runs the (became) available flush operation that tries to determine
        all the streams that were under the "blocked" state and became
        "unblocked", notifying them about that "edge" operation.

        This operation must be performed after any of the blocking constraints
        is changed (eg: connection window, stream window, etc.).
        """
        ...
    
    def set_settings(self, settings): # -> None:
        ...
    
    def close_stream(self, stream, final=..., flush=..., reset=...): # -> None:
        ...
    
    def available_stream(self, stream, length, strict=...): # -> bool:
        ...
    
    def fragment_stream(self, stream, data):
        ...
    
    def fragmentable_stream(self, stream, data):
        ...
    
    def open_stream(self, stream): # -> bool:
        ...
    
    def try_available(self, stream, strict=...): # -> None:
        """
        Tries to determine if the stream with the provided identifier
        has just became available (unblocked from blocked state), this
        happens when the required window value (either connection or
        stream is increased properly).

        :type stream: int
        :param stream: The identifier of the stream that is going to
        be tested from proper connection availability.
        :type strict: bool
        :param strict: If the strict mode should be used in the availability
        testing, this implies extra verifications.
        """
        ...
    
    def try_unavailable(self, stream, strict=...): # -> None:
        """
        Runs the unavailability test on the stream with the provided identifier
        meaning that a series of validation will be performed to try to determine
        if for some reason is not possible to send any more data frames to the
        stream until some window changes. A stream that is under the unavailable
        state is considered "blocked".

        :type stream: int
        :param stream: The identifier of the stream that is going to
        be tested from proper connection unavailability.
        :type strict: bool
        :param strict: If the strict mode should be used in the availability
        testing, this implies extra verifications.
        """
        ...
    
    def increment_remote(self, stream, increment, all=...): # -> None:
        """
        Increments the size of the remove window associated with
        the stream passed by argument by the size defined in the
        increment field (in bytes).

        If the stream is not provided or invalid the global window
        is updated instead of the stream one.

        :type stream: int
        :param stream: The identifier of the stream that is going
        to have its window incremented, or invalid if the global
        connection window is meant to be updated.
        :type increment: int
        :param increment: The increment in bytes for the window,
        this value may be negative for decrement operations.
        :type all: bool
        :param all: If all the resources (connection and stream)
        should be updated by the increment operation.
        """
        ...
    
    def increment_local(self, stream, increment): # -> None:
        ...
    
    def error_connection(self, last_stream=..., error_code=..., message=..., close=..., callback=...): # -> None:
        ...
    
    def error_stream(self, stream, last_stream=..., error_code=..., message=..., close=..., callback=...): # -> None:
        ...
    
    def on_header(self, header): # -> None:
        ...
    
    def on_payload(self): # -> None:
        ...
    
    def on_frame(self): # -> None:
        ...
    
    def on_data_h2(self, stream, contents): # -> None:
        ...
    
    def on_headers_h2(self, stream): # -> None:
        ...
    
    def on_rst_stream(self, stream, error_code): # -> None:
        ...
    
    def on_settings(self, settings, ack): # -> None:
        ...
    
    def on_ping(self, opaque, ack): # -> None:
        ...
    
    def on_goaway(self, last_stream, error_code, extra): # -> None:
        ...
    
    def on_window_update(self, stream, increment): # -> None:
        ...
    
    def on_continuation(self, stream): # -> None:
        ...
    
    def is_throttleable(self): # -> bool:
        ...
    
    @property
    def connection_ctx(self): # -> Self:
        ...
    
    @property
    def parser_ctx(self): # -> HTTPParser | HTTP2Parser | None:
        ...
    


class HTTP2Server(http.HTTPServer):
    def __init__(self, legacy=..., safe=..., settings=..., *args, **kwargs) -> None:
        ...
    
    def info_dict(self, full=...): # -> dict[str, str | Any]:
        ...
    
    def get_protocols(self): # -> list[Any]:
        ...
    
    def build_connection(self, socket, address, ssl=...): # -> HTTP2Connection:
        ...
    
    def on_exception(self, exception, connection): # -> None:
        ...
    
    def on_ssl(self, connection): # -> None:
        ...
    
    def on_serve(self): # -> None:
        ...
    
    def on_preface_http2(self, connection, parser): # -> None:
        ...
    
    def on_header_http2(self, connection, parser, header): # -> None:
        ...
    
    def on_payload_http2(self, connection, parser): # -> None:
        ...
    
    def on_frame_http2(self, connection, parser): # -> None:
        ...
    
    def on_data_http2(self, connection, parser, stream, contents): # -> None:
        ...
    
    def on_headers_http2(self, connection, parser, stream): # -> None:
        ...
    
    def on_rst_stream_http2(self, connection, parser, stream, error_code): # -> None:
        ...
    
    def on_settings_http2(self, connection, parser, settings, ack): # -> None:
        ...
    
    def on_ping_http2(self, connection, parser, opaque, ack): # -> None:
        ...
    
    def on_goaway_http2(self, connection, parser, last_stream, error_code, extra): # -> None:
        ...
    
    def on_window_update_http2(self, connection, parser, stream, increment): # -> None:
        ...
    
    def on_continuation_http2(self, connection, parser, stream): # -> None:
        ...
    
    def on_send_http2(self, connection, parser, type, flags, payload, stream): # -> None:
        ...
    


