import netius as netius
import netius.clients.http
import netius.clients.http as http
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class MJPGProtocol(netius.clients.http.HTTPProtocol):
    MAGIC_JPEG: ClassVar[bytes] = ...
    EOI_JPEG: ClassVar[bytes] = ...
    def __init__(self, *args, **kwargs) -> None: ...
    def add_buffer(self, data): ...
    def get_buffer(self, delete: bool = ...): ...
    def on_partial(self, data): ...
    def on_frame_mjpg(self, data): ...

class MJPGClient(netius.clients.http.HTTPClient):
    class protocol(netius.clients.http.HTTPProtocol):
        MAGIC_JPEG: ClassVar[bytes] = ...
        EOI_JPEG: ClassVar[bytes] = ...
        def __init__(self, *args, **kwargs) -> None: ...
        def add_buffer(self, data): ...
        def get_buffer(self, delete: bool = ...): ...
        def on_partial(self, data): ...
        def on_frame_mjpg(self, data): ...
