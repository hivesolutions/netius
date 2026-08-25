from typing import Any, Mapping, Sequence
from uuid import UUID

class NetiusError(Exception):
    kwargs: Mapping[str, Any]
    message: str
    code: int
    details: Sequence[Any]

    def __init__(self, *args, **kwargs): ...
    def get_kwarg(self, name: str, default: Any = ...) -> Any: ...
    @property
    def uid(self) -> UUID: ...

class RuntimeError(NetiusError):
    pass

class StopError(RuntimeError):
    pass

class PauseError(RuntimeError):
    pass

class WakeupError(RuntimeError):
    pass

class DataError(RuntimeError):
    pass

class ParserError(RuntimeError):
    def __init__(self, *args, **kwargs): ...

class GeneratorError(RuntimeError):
    pass

class SecurityError(RuntimeError):
    pass

class NotImplemented(RuntimeError):
    pass

class AssertionError(RuntimeError):
    pass
