from typing import Any, Mapping, Sequence

from netius.clients import SMTPClient
from netius.servers import SMTPConnection, SMTPServer

class RelaySMTPServer(SMTPServer):
    postmaster: str | None
    capture_transcript: bool
    dkim: dict[str, Mapping[str, str]]

    def __init__(
        self,
        postmaster: str | None = ...,
        capture_transcript: bool = ...,
        *args,
        **kwargs
    ): ...
    def on_serve(self): ...
    def on_header_smtp(
        self,
        connection: SMTPConnection,
        from_l: Sequence[str],
        to_l: Sequence[str],
    ): ...
    def on_data_smtp(self, connection: SMTPConnection, data: bytes): ...
    def on_message_smtp(self, connection: SMTPConnection): ...
    def on_relay_smtp(
        self,
        connection: SMTPConnection,
        context: Mapping[str, Any],
        smtp_client: SMTPClient,
        froms: Sequence[str],
        tos: Sequence[str],
        contents: bytes,
    ): ...
    def on_relay_error_smtp(
        self,
        connection: SMTPConnection,
        context: Mapping[str, Any],
        exception: BaseException,
        smtp_client: SMTPClient,
        froms: Sequence[str],
        tos: Sequence[str],
        contents: bytes,
        reply_to: str | None,
    ): ...
    def relay(
        self,
        connection: SMTPConnection,
        froms: Sequence[str],
        tos: Sequence[str],
        contents: bytes,
    ): ...
    def relay_postmaster(
        self,
        reply_to: str | None,
        context: Mapping[str, Any],
        exception: BaseException,
    ): ...
    def date(self) -> str: ...
    def message_id(
        self, connection: SMTPConnection | None = ..., email: str = ...
    ) -> str: ...
    def dkim_contents(
        self, contents: bytes, email: str = ..., creation: float | None = ...
    ) -> bytes: ...
