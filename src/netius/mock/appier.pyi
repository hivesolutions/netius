from typing import Any, Callable

class APIApp:
    pass

def route(*args, **kwargs) -> Callable[..., None]: ...
