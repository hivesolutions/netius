from typing import Sequence

from netius import Connection
from netius.base.common import AbstractBase
from netius.middleware import Middleware

class BlacklistMiddleware(Middleware):
    blacklist: Sequence[str]
    whitelist: Sequence[str]

    def __init__(
        self,
        owner: AbstractBase,
        blacklist: Sequence[str] | None = ...,
        whitelist: Sequence[str] | None = ...,
    ): ...
    def start(self): ...
    def stop(self): ...
    def on_connection_c(self, owner: AbstractBase, connection: Connection): ...
