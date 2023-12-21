import netius.auth.base
import netius.auth.base as base

from typing import Literal

class AllowAuth(netius.auth.base.Auth):
    @classmethod
    def auth(cls, *args, **kwargs) -> Literal[True]: ...
    @classmethod
    def is_simple(cls) -> Literal[True]: ...
