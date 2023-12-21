import netius.auth.base
import netius.auth.base as base

from typing import Literal

class DenyAuth(netius.auth.base.Auth):
    @classmethod
    def auth(cls, *args, **kwargs) -> Literal[False]: ...
    @classmethod
    def is_simple(cls) -> Literal[True]: ...
