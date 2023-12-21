import netius as netius
import netius.base.client
import netius.base.conn
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str
HANDSHAKE_STATE: int
NORMAL_STATE: int
CHOKED: int
UNCHOKED: int
ALIVE_TIMEOUT: float
SPEED_LIMIT: int
BLOCK_SIZE: int

class TorrentConnection(netius.base.conn.BaseConnection):
    def __init__(self, max_requests: int = ..., *args, **kwargs) -> None: ...
    def open(self, *args, **kwargs): ...
    def close(self, *args, **kwargs): ...
    def on_close(self, connection): ...
    def on_handshake(self, protocol, reserved, info_hash, peer_id): ...
    def on_message(self, length, type, data): ...
    def parse(self, data): ...
    def handle(self, type, data): ...
    def bitfield_t(self, data): ...
    def choke_t(self, data): ...
    def unchoke_t(self, data): ...
    def piece_t(self, data): ...
    def port_t(self, data): ...
    def next(self, count: Incomplete | None = ...): ...
    def add_request(self, block): ...
    def remove_request(self, block): ...
    def reset(self): ...
    def release(self): ...
    def handshake(self): ...
    def keep_alive(self): ...
    def choke(self): ...
    def unchoke(self): ...
    def interested(self): ...
    def not_interested(self): ...
    def have(self, index): ...
    def request(self, index, begin: int = ..., length: int = ...): ...
    def is_alive(self, timeout: float = ..., schedule: bool = ...): ...

class TorrentClient(netius.base.client.StreamClient):
    def peer(self, task, host, port, ssl: bool = ..., connection: Incomplete | None = ...): ...
    def on_connect(self, connection): ...
    def on_acquire(self, connection): ...
    def on_data(self, connection, data): ...
    def build_connection(self, socket, address, ssl: bool = ...): ...
