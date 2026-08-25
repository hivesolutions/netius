from typing import Any, BinaryIO, Callable, Mapping

from netius import BaseAdapter

class MemoryAdapter(BaseAdapter):
    map: dict[str, bytes]
    owners: dict[str, list[str]]

    def __init__(self): ...
    def _ensure(self, owner: str) -> Mapping[str, Any]: ...
    def _build_close(self, file: BinaryIO, key: str) -> Callable[[], None]: ...
