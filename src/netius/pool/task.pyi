from typing import Any, Callable, Mapping, Sequence

from netius.pool import EventPool, Thread

TASK_WORK: int

class TaskThread(Thread):
    def execute(self, work: tuple[Any, ...]): ...

class TaskPool(EventPool):
    def __init__(self, base: type[Thread] = ..., count: int = ...): ...
    def execute(
        self,
        callable: Callable[..., Any],
        args: Sequence[Any] = ...,
        kwargs: Mapping[str, Any] = ...,
        callback: Callable[..., Any] | None = ...,
    ): ...
