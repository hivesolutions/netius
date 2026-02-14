from typing import Any

from .observer import Observable
from .client import Client

class Agent(Observable):
    @classmethod
    def cleanup_s(cls) -> None: ...
    def cleanup(self, destroy: bool = ...) -> None: ...
    def destroy(self) -> None: ...

class ClientAgent(Agent):
    _clients: dict[int, Client]

    @classmethod
    def cleanup_s(cls) -> None: ...
    @classmethod
    def get_client_s(cls, *args, **kwargs) -> Client: ...

class ServerAgent(Agent):
    pass
