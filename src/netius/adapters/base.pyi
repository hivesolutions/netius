from typing import Any, BinaryIO, Sequence

class BaseAdapter:
    def set(self, value: Any, owner: str = ...): ...
    def get(self, key: str) -> bytes | None: ...
    def get_file(self, key: str, mode: str = ...) -> BinaryIO: ...
    def delete(self, key: str, owner: str = ...): ...
    def append(self, key: str, value: Any): ...
    def truncate(self, key: str, count: int): ...
    def size(self, key: str) -> int: ...
    def sizes(self, owner: str | None = ...) -> list[int]: ...
    def total(self, owner: str | None = ...) -> int: ...
    def reserve(self, owner: str = ...): ...
    def count(self, owner: str | None = ...) -> int: ...
    def list(self, owner: str | None = ...) -> Sequence[str]: ...
    def generate(self) -> str: ...