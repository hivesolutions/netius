from logging.handlers import RotatingFileHandler, SMTPHandler

SILENT: int

def rotating_handler(
    path: str = ...,
    max_bytes: int = ...,
    max_log: int = ...,
    encoding: str | None = ...,
    delay: bool = ...
) -> RotatingFileHandler: ...
def smtp_handler(
    host: str = ...,
    port: int = ...,
    sender: str = ...,
    receivers: list[str] = [],
    subject: str = ...,
    username: str | None = ...,
    password: str | None = ...,
    stls: bool = ...
) -> SMTPHandler: ...
def in_signature(
    callable: object,
    name: str
) -> bool: ...
