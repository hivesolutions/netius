from typing import Sequence

from netius import Auth

class SimpleAuth(Auth):
    def __init__(
        self, username: str | None = ..., password: str | None = ..., *args, **kwargs
    ): ...
    @classmethod
    def auth(
        cls,
        username: str,
        password: str,
        target: Sequence[str, str] | None = ...,
        *args,
        **kwargs
    ) -> bool: ...
    def auth_i(self, username: str, password: str, *args, **kwargs) -> bool: ...
