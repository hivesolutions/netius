from typing import Any

from netius.common import Parser

class POPParser(Parser):
    buffer: list[bytes]

    def __init__(self, owner: Any, store: bool = ...): ...
    def parse(self, data: bytes) -> int: ...
    def _parse_line(self, data: bytes) -> int: ...
