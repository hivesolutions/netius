import netius.auth.base
import netius.auth.base as base
from typing import Literal

class DummyAuth(netius.auth.base.Auth):
    def __init__(self, value: bool = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, value: bool = ..., *args, **kwargs): ...
    @classmethod
    def is_simple(cls) -> Literal[True]: ...
    def auth_i(self, *args, **kwargs) -> bool: ...
