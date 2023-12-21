import netius as netius
import netius.pool.common
import netius.pool.common as common
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str
TASK_WORK: int

class TaskThread(netius.pool.common.Thread):
    def execute(self, work): ...

class TaskPool(netius.pool.common.EventPool):
    def __init__(self, base: type[TaskThread] = ..., count: int = ...) -> None: ...
    def execute(self, callable, args: list = ..., kwargs: dict = ..., callback: Incomplete | None = ...): ...
