from collections import deque
from logging import Handler, LogRecord, Logger
from logging.handlers import RotatingFileHandler, SMTPHandler
from typing import Any, Callable

SILENT: int
TRACE: int
MAX_LENGTH_LOGSTASH: int
TIMEOUT_LOGSTASH: float

class LogstashHandler(Handler):
    messages: deque[dict[str, Any]]
    max_length: int
    timeout: float
    api: Any

    def __init__(
        self,
        level: int = ...,
        max_length: int = ...,
        timeout: float = ...,
        api: Any = ...,
    ): ...
    @classmethod
    def is_ready(cls) -> bool: ...
    def emit(self, record: LogRecord, raise_e: bool = ...) -> None: ...
    def flush(self, force: bool = ..., raise_e: bool = ...) -> None: ...
    def _build_api(self) -> Any: ...

def rotating_handler(
    path: str = ...,
    max_bytes: int = ...,
    max_log: int = ...,
    encoding: str | None = ...,
    delay: bool = ...,
) -> RotatingFileHandler: ...
def smtp_handler(
    host: str = ...,
    port: int = ...,
    sender: str = ...,
    receivers: list[str] = ...,
    subject: str = ...,
    username: str | None = ...,
    password: str | None = ...,
    stls: bool = ...,
) -> SMTPHandler: ...
def patch_logging() -> None: ...
def in_signature(callable: Callable[..., Any], name: str) -> bool: ...
def _trace(self: Logger, message: Any, *args: Any, **kwargs: Any) -> None: ...
