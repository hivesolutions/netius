"""
This type stub file was generated by pyright.
"""

from . import observer

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class Protocol(observer.Observable):
    """
    Abstract class from which concrete implementation of
    protocol logic should inherit.

    The logic of a protocol should implement both a reaction
    to the arrival of information (receive) and the sending
    of processed data (send).
    """
    def __init__(self, owner=...) -> None:
        ...
    
    def open(self): # -> None:
        ...
    
    def close(self): # -> None:
        ...
    
    def finish(self): # -> None:
        ...
    
    def open_c(self): # -> None:
        ...
    
    def close_c(self): # -> None:
        ...
    
    def finish_c(self): # -> None:
        ...
    
    def info_dict(self, full=...): # -> dict[Any, Any]:
        ...
    
    def connection_made(self, transport): # -> None:
        ...
    
    def connection_lost(self, exception): # -> None:
        ...
    
    def transport(self): # -> None:
        ...
    
    def loop(self): # -> None:
        ...
    
    def loop_set(self, loop): # -> None:
        ...
    
    def loop_unset(self): # -> None:
        ...
    
    def pause_writing(self): # -> None:
        ...
    
    def resume_writing(self): # -> None:
        ...
    
    def delay(self, callable, timeout=...):
        ...
    
    def debug(self, object): # -> None:
        ...
    
    def info(self, object): # -> None:
        ...
    
    def warning(self, object): # -> None:
        ...
    
    def error(self, object): # -> None:
        ...
    
    def critical(self, object): # -> None:
        ...
    
    def is_pending(self): # -> bool:
        ...
    
    def is_open(self): # -> bool:
        ...
    
    def is_closed(self): # -> bool:
        ...
    
    def is_closing(self): # -> bool:
        ...
    
    def is_closed_or_closing(self): # -> bool:
        ...
    
    def is_devel(self): # -> Literal[False]:
        ...
    


class DatagramProtocol(Protocol):
    def __init__(self) -> None:
        ...
    
    def datagram_received(self, data, address): # -> None:
        ...
    
    def error_received(self, exception): # -> None:
        ...
    
    def on_data(self, address, data): # -> None:
        ...
    
    def send(self, data, address, delay=..., force=..., callback=...): # -> int:
        ...
    
    def send_to(self, data, address, delay=..., force=..., callback=...): # -> int:
        ...
    
    def add_request(self, request): # -> None:
        ...
    
    def remove_request(self, request): # -> None:
        ...
    
    def get_request(self, id):
        ...
    


class StreamProtocol(Protocol):
    def data_received(self, data): # -> None:
        ...
    
    def eof_received(self): # -> None:
        ...
    
    def on_data(self, data): # -> None:
        ...
    
    def send(self, data, delay=..., force=..., callback=...): # -> int:
        ...
    


