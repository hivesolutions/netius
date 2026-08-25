from netius import Connection
from netius.servers import WSServer

class EchoWSServer(WSServer):
    def on_data_ws(self, connection: Connection, data: bytes): ...
