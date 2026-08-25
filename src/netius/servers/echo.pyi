from typing import Any

from netius import ServerAgent, StreamProtocol

class EchoProtocol(StreamProtocol):
    def on_data(self, data: bytes): ...
    def serve(
        self,
        host: str = ...,
        port: int = ...,
        ssl: bool = ...,
        env: bool = ...,
        loop: Any = ...,
    ) -> tuple[Any, EchoProtocol]: ...

class EchoServer(ServerAgent):
    protocol: type[EchoProtocol]

    @classmethod
    def serve_s(cls, **kwargs) -> tuple[Any, EchoProtocol]: ...
