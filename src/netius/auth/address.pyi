import netius.auth.base
import netius.auth.base as base

from typing import Literal

class AddressAuth(netius.auth.base.Auth):
    def __init__(self, allowed: list = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, allowed: list = ..., *args, **kwargs) -> bool: ...
    @classmethod
    def is_simple(cls) -> Literal[True]: ...
    def auth_i(self, *args, **kwargs) -> bool: ...
