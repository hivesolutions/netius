import netius as netius
import netius.base.agent
import netius.base.protocol

__version__: str
__revision__: str
__date__: str

class EchoProtocol(netius.base.protocol.StreamProtocol): ...

class EchoServer(netius.base.agent.ServerAgent):
    class protocol(netius.base.protocol.StreamProtocol): ...
