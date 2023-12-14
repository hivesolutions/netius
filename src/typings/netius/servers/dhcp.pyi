import netius as netius
import netius.base.server
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class DHCPRequest:
    options_m: ClassVar[None] = ...
    options_l: ClassVar[None] = ...
    def __init__(self, data) -> None: ...
    @classmethod
    def generate(cls): ...
    def get_info(self): ...
    def print_info(self): ...
    def parse(self): ...
    def unpack_options(self): ...
    def get_requested(self): ...
    def get_type(self): ...
    def get_type_s(self): ...
    def get_mac(self): ...
    def response(self, yiaddr, options: dict = ...): ...
    @classmethod
    def _str(cls, data): ...
    @classmethod
    def _pack_m(cls, sequence, format): ...
    @classmethod
    def _option_subnet(cls, subnet: str = ...): ...
    @classmethod
    def _option_router(cls, routers: list = ...): ...
    @classmethod
    def _option_dns(cls, servers: list = ...): ...
    @classmethod
    def _option_name(cls, name: str = ...): ...
    @classmethod
    def _option_broadcast(cls, broadcast: str = ...): ...
    @classmethod
    def _option_requested(cls, ip: str = ...): ...
    @classmethod
    def _option_lease(cls, time: int = ...): ...
    @classmethod
    def _option_discover(cls): ...
    @classmethod
    def _option_offer(cls): ...
    @classmethod
    def _option_request(cls): ...
    @classmethod
    def _option_decline(cls): ...
    @classmethod
    def _option_ack(cls): ...
    @classmethod
    def _option_nak(cls): ...
    @classmethod
    def _option_identifier(cls, identifier: str = ...): ...
    @classmethod
    def _option_renewal(cls, time: int = ...): ...
    @classmethod
    def _option_rebind(cls, time: int = ...): ...
    @classmethod
    def _option_proxy(cls, url: str = ...): ...
    @classmethod
    def _option_end(cls): ...

class DHCPServer(netius.base.server.DatagramServer):
    def serve(self, port: int = ..., type: int = ..., *args, **kwargs): ...
    def on_data(self, address, data): ...
    def on_data_dhcp(self, address, request): ...
    def get_verb(self, type_r): ...
    def send_dhcp(self, data, *args, **kwargs): ...
    def get_type(self, request): ...
    def get_options(self, request): ...
    def get_yiaddr(self, request): ...
