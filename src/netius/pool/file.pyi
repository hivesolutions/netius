from os import PathLike
from typing import IO, Any, Callable

from netius.pool import EventPool, Thread

FILE_WORK: int
ERROR_ACTION: int
OPEN_ACTION: int
CLOSE_ACTION: int
READ_ACTION: int
WRITE_ACTION: int

class FileThread(Thread):
    def execute(self, work: tuple[Any, ...]): ...
    def open(self, path: PathLike[str], mode: str, data: Callable[..., Any] | None): ...
    def close(self, file: IO[Any], data: Callable[..., Any] | None): ...
    def read(self, file: IO[Any], count: int, data: Callable[..., Any] | None): ...
    def write(
        self, file: IO[Any], buffer: bytes | str, data: Callable[..., Any] | None
    ): ...
    def _execute(self, work: tuple[Any, ...]): ...

class FilePool(EventPool):
    def __init__(self, base: type[Thread] = ..., count: int = ...): ...
    def open(
        self,
        path: PathLike[str],
        mode: str = ...,
        data: Callable[..., Any] | None = ...,
    ): ...
    def close(self, file: IO[Any], data: Callable[..., Any] | None = ...): ...
    def read(
        self, file: IO[Any], count: int = ..., data: Callable[..., Any] | None = ...
    ): ...
    def write(
        self,
        file: IO[Any],
        buffer: bytes | str,
        data: Callable[..., Any] | None = ...,
    ): ...
