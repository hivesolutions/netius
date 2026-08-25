from netius import Connection, Stream
from netius.extra import FileServer
from netius.servers import HTTPConnection

BUFFER_SIZE: int

class FileAsyncServer(FileServer):
    def on_connection_d(self, connection: Connection): ...
    def on_stream_d(self, stream: Stream): ...
    def _file_send(self, connection: HTTPConnection): ...
