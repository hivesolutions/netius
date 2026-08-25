from typing import Any, Sequence

class GeoResolver:
    DB_NAME: str
    DOWNLOAD_URL: str
    VALID: tuple[str, ...]
    PREFIXES: tuple[str, ...]
    _db: Any

    @classmethod
    def resolve(cls, address: str, simplified: bool = ...) -> dict[str, Any] | None: ...
    @classmethod
    def _simplify(
        cls,
        result: dict[str, Any] | None,
        locale: str = ...,
        valid: Sequence[str] = ...,
    ) -> dict[str, Any] | None: ...
    @classmethod
    def _get_db(cls) -> Any: ...
    @classmethod
    def _try_all(cls, prefixes: Sequence[str] = ...) -> str | None: ...
    @classmethod
    def _try_db(cls, path: str = ..., download: bool = ...) -> str | None: ...
    @classmethod
    def _download_db(cls, path: str = ...): ...
    @classmethod
    def _store_db(cls, contents: bytes, path: str = ...) -> str: ...
