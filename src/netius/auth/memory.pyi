from typing import Any

from netius import Auth

class MemoryAuth(Auth):
    def __init__(
        self, registry: dict[str, Any] | None = ..., *args, **kwargs
    ): ...
    @classmethod
    def auth(
        cls,
        username: str,
        password: str,
        registry: dict[str, Any] | None = ...,
        *args,
        **kwargs
    ) -> bool: ...
    @classmethod
    def meta(
        cls, username: str, registry: dict[str, Any] | None = ..., *args, **kwargs
    ) -> dict[str, Any]: ...
    @classmethod
    def get_registry(cls) -> dict[str, Any]: ...
    @classmethod
    def load_registry(cls) -> dict[str, Any]: ...
