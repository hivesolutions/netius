from typing import Sequence

from netius import Auth

class AddressAuth(Auth):
    def __init__(self, allowed: Sequence[str] = ..., *args, **kwargs) -> None: ...
    @classmethod
    def auth(cls, allowed: Sequence[str] = ..., *args, **kwargs) -> bool: ...
