import netius.base.legacy as legacy
import netius.base.observer
import netius.base.observer as observer
import netius.base.request as request
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class Protocol(netius.base.observer.Observable):
    def __init__(self, owner: Incomplete | None = ...) -> None: ...
    def open(self): ...
    def close(self): ...
    def finish(self): ...
    def open_c(self): ...
    def close_c(self): ...
    def finish_c(self): ...
    def info_dict(self, full: bool = ...): ...
    def connection_made(self, transport): ...
    def connection_lost(self, exception): ...
    def transport(self): ...
    def loop(self): ...
    def loop_set(self, loop): ...
    def loop_unset(self): ...
    def pause_writing(self): ...
    def resume_writing(self): ...
    def delay(self, callable, timeout: Incomplete | None = ...): ...
    def debug(self, object): ...
    def info(self, object): ...
    def warning(self, object): ...
    def error(self, object): ...
    def critical(self, object): ...
    def is_pending(self): ...
    def is_open(self): ...
    def is_closed(self): ...
    def is_closing(self): ...
    def is_closed_or_closing(self): ...
    def is_devel(self): ...
    def _close_transport(self, force: bool = ...): ...
    def _delay_send(self, data, address: Incomplete | None = ..., callback: Incomplete | None = ...): ...
    def _flush_callbacks(self): ...
    def _flush_send(self): ...

class DatagramProtocol(Protocol):
    def __init__(self) -> None: ...
    def datagram_received(self, data, address): ...
    def error_received(self, exception): ...
    def on_data(self, address, data): ...
    def send(self, data, address, delay: bool = ..., force: bool = ..., callback: Incomplete | None = ...): ...
    def send_to(self, data, address, delay: bool = ..., force: bool = ..., callback: Incomplete | None = ...): ...
    def add_request(self, request): ...
    def remove_request(self, request): ...
    def get_request(self, id): ...

class StreamProtocol(Protocol):
    def data_received(self, data): ...
    def eof_received(self): ...
    def on_data(self, data): ...
    def send(self, data, delay: bool = ..., force: bool = ..., callback: Incomplete | None = ...): ...
