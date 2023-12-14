import netius as netius
import netius.servers.mjpg

__version__: str
__revision__: str
__date__: str
PIL: None

class DesktopServer(netius.servers.mjpg.MJPGServer):
    def get_delay(self, connection): ...
    def get_image(self, connection): ...
