import netius as netius
import netius.base.agent
import netius.base.protocol
from _typeshed import Incomplete
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class APNProtocol(netius.base.protocol.StreamProtocol):
    HOST: ClassVar[str] = ...
    PORT: ClassVar[int] = ...
    SANDBOX_HOST: ClassVar[str] = ...
    SANDBOX_PORT: ClassVar[int] = ...
    def __init__(self, *args, **kwargs) -> None: ...
    def connection_made(self, transport): ...
    def send_notification(self, token, message, sound: str = ..., badge: int = ..., close: bool = ...): ...
    def set(self, token, message, sound: str = ..., badge: int = ..., sandbox: bool = ..., key_file: Incomplete | None = ..., cer_file: Incomplete | None = ..., _close: bool = ...): ...
    def notify(self, token, loop: Incomplete | None = ..., **kwargs): ...

class APNClient(netius.base.agent.ClientAgent):
    class protocol(netius.base.protocol.StreamProtocol):
        HOST: ClassVar[str] = ...
        PORT: ClassVar[int] = ...
        SANDBOX_HOST: ClassVar[str] = ...
        SANDBOX_PORT: ClassVar[int] = ...
        def __init__(self, *args, **kwargs) -> None: ...
        def connection_made(self, transport): ...
        def send_notification(self, token, message, sound: str = ..., badge: int = ..., close: bool = ...): ...
        def set(self, token, message, sound: str = ..., badge: int = ..., sandbox: bool = ..., key_file: Incomplete | None = ..., cer_file: Incomplete | None = ..., _close: bool = ...): ...
        def notify(self, token, loop: Incomplete | None = ..., **kwargs): ...
    @classmethod
    def notify_s(cls, token, loop: Incomplete | None = ..., **kwargs): ...
