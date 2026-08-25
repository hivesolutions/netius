from netius.servers import HTTPConnection, MJPGServer

class DesktopServer(MJPGServer):
    def get_delay(self, connection: HTTPConnection) -> int: ...
    def get_image(  # type: ignore[override]
        self, connection: HTTPConnection
    ) -> bytes | None: ...
