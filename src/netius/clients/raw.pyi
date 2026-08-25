from typing import Any

from netius import ClientAgent, Protocol, StreamProtocol

class RawProtocol(StreamProtocol):
    def send_basic(self): ...

class RawClient(ClientAgent):
    protocol: type[RawProtocol]

    @classmethod
    def run_s(
        cls, host: str, port: int = ..., loop: Any = ..., *args, **kwargs
    ) -> tuple[Any, RawProtocol]: ...
    def _relay_protocol_events(self, protocol: Protocol): ...
