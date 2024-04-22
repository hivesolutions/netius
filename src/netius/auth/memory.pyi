from typing import Any, Mapping

from netius import Auth

class MemoryAuth(Auth):
    def __init__(self, registry: Mapping[str, Any] | None = ..., *args, **kwargs): ...
    @classmethod
    def auth(
        cls,
        username: str,
        password: str,
        registry: Mapping[str, Any] | None = ...,
        *args,
        **kwargs
    ) -> bool: ...
    @classmethod
    def meta(
        cls, username: str, registry: Mapping[str, Any] | None = ..., *args, **kwargs
    ) -> Mapping[str, Any]: ...
    @classmethod
    def get_registry(cls) -> Mapping[str, Any]: ...
    @classmethod
    def load_registry(cls) -> Mapping[str, Any]: ...
