import netius as netius
import netius.common.parser
import netius.common.parser as parser
import netius.common.util as util

__version__: str
__revision__: str
__date__: str
IPV4: int
IPV6: int
DOMAIN: int
VERSION_STATE: int
HEADER_STATE: int
USER_ID_STATE: int
DOMAIN_STATE: int
AUTH_COUNT_STATE: int
AUTH_METHODS_STATE: int
HEADER_EXTRA_STATE: int
SIZE_STATE: int
ADDRESS_STATE: int
PORT_STATE: int
FINISH_STATE: int

class SOCKSParser(netius.common.parser.Parser):
    def __init__(self, owner) -> None: ...
    def build(self): ...
    def destroy(self): ...
    def reset(self): ...
    def clear(self, force: bool = ...): ...
    def parse(self, data): ...
    def get_host(self): ...
    def get_address(self): ...
    def _parse_version(self, data): ...
    def _parse_header(self, data): ...
    def _parse_user_id(self, data): ...
    def _parse_domain(self, data): ...
    def _parse_auth_count(self, data): ...
    def _parse_auth_methods(self, data): ...
    def _parse_header_extra(self, data): ...
    def _parse_size(self, data): ...
    def _parse_address(self, data): ...
    def _parse_port(self, data): ...
