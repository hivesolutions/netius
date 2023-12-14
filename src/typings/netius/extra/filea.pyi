import netius.extra.file
import netius.extra.file as _file

__version__: str
__revision__: str
__date__: str
BUFFER_SIZE: int

class FileAsyncServer(netius.extra.file.FileServer):
    def on_connection_d(self, connection): ...
    def on_stream_d(self, stream): ...
    def _file_send(self, connection): ...
