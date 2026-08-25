from typing import Any, Mapping

from netius.common import AddressPool
from netius.servers import DHCPRequest, DHCPServer

class DHCPServerS(DHCPServer):
    pool: AddressPool
    options: dict[int, Mapping[str, Any] | None]
    lease: int

    def __init__(
        self,
        pool: AddressPool | None = ...,
        options: Mapping[str, Mapping[str, Any]] = ...,
        *args,
        **kwargs
    ): ...
    def get_type(self, request: DHCPRequest) -> int: ...
    def get_options(
        self, request: DHCPRequest
    ) -> dict[int, Mapping[str, Any] | None]: ...
    def get_yiaddr(self, request: DHCPRequest) -> str: ...
    def _build(self, options: Mapping[str, Mapping[str, Any]]): ...
    def _reserve(self, request: DHCPRequest) -> str: ...
    def _confirm(self, request: DHCPRequest) -> str: ...
