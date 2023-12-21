import netius as netius
import netius.base.agent
import netius.base.protocol
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class RawProtocol(netius.base.protocol.StreamProtocol):
    def send_basic(self): ...

class RawClient(netius.base.agent.ClientAgent):
    class protocol(netius.base.protocol.StreamProtocol):
        def send_basic(self): ...
    @classmethod
    def run_s(cls, host, port: int = ..., loop: Incomplete | None = ..., *args, **kwargs): ...
