import netius.servers.ws
import netius.servers.ws as ws

__version__: str
__revision__: str
__date__: str

class EchoWSServer(netius.servers.ws.WSServer):
    def on_data_ws(self, connection, data): ...
