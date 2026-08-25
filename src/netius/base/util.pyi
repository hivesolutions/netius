from re import Pattern
from typing import Any

FIRST_CAP_REGEX: Pattern[str]
ALL_CAP_REGEX: Pattern[str]

def camel_to_underscore(camel: str, separator: str = ...) -> str: ...
def verify(
    condition: Any, message: str | None = ..., exception: type[Exception] | None = ...
): ...
