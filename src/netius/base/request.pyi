from typing import Any, Callable, NoReturn

REQUEST_TIMEOUT: float

class Request:
    IDENTIFIER: int
    id: int
    timeout: float
    callback: Callable[..., Any] | None

    def __init__(
        self, timeout: float = ..., callback: Callable[..., Any] | None = ...
    ): ...
    @classmethod
    def _generate_id(cls) -> int: ...

class Response:
    data: bytes
    request: Request | None

    def __init__(self, data: bytes, request: Request | None = ...): ...
    def parse(self): ...
    def get_request(self) -> Request | None: ...
    def get_id(self) -> NoReturn: ...
