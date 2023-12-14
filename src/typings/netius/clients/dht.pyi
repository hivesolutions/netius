"""
This type stub file was generated by pyright.
"""

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class DHTRequest(netius.Request):
    def __init__(self, peer_id, host=..., port=..., type=..., callback=..., *args, **kwargs) -> None:
        ...
    
    @classmethod
    def contact(cls, host, port): # -> bytes:
        ...
    
    def request(self): # -> bytes:
        ...
    
    def ping(self): # -> dict[str, Any | bytes]:
        ...
    
    def find_node(self): # -> dict[str, Any | bytes]:
        ...
    
    def get_peers(self): # -> dict[str, Any | bytes]:
        ...
    
    def announce_peer(self): # -> dict[str, Any | bytes]:
        ...
    


class DHTResponse(netius.Response):
    def __init__(self, data) -> None:
        ...
    
    def parse(self): # -> None:
        ...
    
    def get_id(self): # -> int:
        ...
    
    def get_payload(self):
        ...
    
    def is_error(self):
        ...
    
    def is_response(self):
        ...
    


class DHTClient(netius.DatagramClient):
    """
    Implementation of the DHT (Distributed hash table) for the torrent
    protocol as the defined in the official specification.

    This implementation is meant to be used in an asynchronous environment
    for maximum performance.

    :see: http://www.bittorrent.org/beps/bep_0005.html
    """
    def ping(self, host, port, peer_id, *args, **kwargs): # -> None:
        ...
    
    def find_node(self, *args, **kwargs): # -> None:
        ...
    
    def get_peers(self, *args, **kwargs): # -> None:
        ...
    
    def query(self, host=..., port=..., peer_id=..., type=..., callback=..., *args, **kwargs): # -> None:
        ...
    
    def on_data(self, address, data): # -> None:
        ...
    
    def on_data_dht(self, address, response): # -> None:
        ...
    


