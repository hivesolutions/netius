from typing import Sequence

from netius import Connection
from netius.base.common import AbstractBase
from netius.middleware import Middleware

class FloodMiddleware(Middleware):
    blacklist: list[str] | int
    whitelist: Sequence[str]

    def __init__(
        self,
        owner: AbstractBase,
        conns_per_min: int = ...,
        whitelist: Sequence[str] | None = ...,
    ): ...
    def start(self): ...
    def stop(self): ...
    def on_connection_c(self, owner: AbstractBase, connection: Connection): ...
    def _update_flood(self, host: str): ...
