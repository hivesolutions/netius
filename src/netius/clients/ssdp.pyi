from typing import Any, Callable, Mapping, Sequence

from netius import ClientAgent, DatagramProtocol

class SSDPProtocol(DatagramProtocol):
    def on_data(self, address: tuple[str, int], data: bytes): ...
    def on_headers_parser(self): ...
    def discover(self, target: str, *args, **kwargs): ...
    def method(
        self,
        method: str,
        target: str,
        namespace: str,
        mx: int = ...,
        path: str = ...,
        params: Mapping[str, Any] | None = ...,
        headers: dict[str, str | Sequence[str]] | None = ...,
        data: bytes | str | None = ...,
        host: str = ...,
        port: int = ...,
        version: str = ...,
        callback: Callable[..., Any] | None = ...,
    ): ...

class SSDPClient(ClientAgent):
    protocol: type[SSDPProtocol]

    @classmethod
    def discover_s(cls, target: str, *args, **kwargs) -> tuple[Any, SSDPProtocol]: ...
    @classmethod
    def method_s(
        cls,
        method: str,
        target: str,
        namespace: str,
        mx: int = ...,
        path: str = ...,
        params: Mapping[str, Any] | None = ...,
        headers: dict[str, str | Sequence[str]] | None = ...,
        data: bytes | str | None = ...,
        host: str = ...,
        port: int = ...,
        version: str = ...,
        callback: Callable[..., Any] | None = ...,
        loop: Any = ...,
    ) -> tuple[Any, SSDPProtocol]: ...
