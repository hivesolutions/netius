from typing import Any, Mapping, Sequence

from netius.clients import SMTPClient
from netius.extra import RelaySMTPServer
from netius.servers import SMTPConnection

class ActivityRelaySMTPServer(RelaySMTPServer):
    activity_url: str | None
    activity_secret: str | None

    def __init__(
        self,
        activity_url: str | None = ...,
        activity_secret: str | None = ...,
        *args,
        **kwargs
    ): ...
    def on_serve(self): ...
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
    def _post_activity(
        self,
        smtp_client: SMTPClient,
        connection: SMTPConnection,
        context: Mapping[str, Any],
        froms: Sequence[str],
        tos: Sequence[str],
        contents: bytes,
        status: str,
        error: str | None = ...,
    ): ...
    def _decode_header(self, value: str) -> str: ...
