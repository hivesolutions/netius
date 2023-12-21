import netius.auth.base
import netius.auth.base as base

from typing import Tuple

class SimpleAuth(netius.auth.base.Auth):
    def __init__(self, username: str | None = ..., password: str | None = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, username: str, password: str, target: Tuple[str:str] | None = ..., *args, **kwargs) -> bool: ...
    def auth_i(self, username:str , password: str, *args, **kwargs) -> bool: ...
