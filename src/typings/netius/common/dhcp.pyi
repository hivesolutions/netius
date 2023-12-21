import netius as netius
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str
SUBNET_DHCP: int
ROUTER_DHCP: int
DNS_DHCP: int
NAME_DHCP: int
BROADCAST_DHCP: int
REQUESTED_DHCP: int
LEASE_DHCP: int
DISCOVER_DHCP: int
OFFER_DHCP: int
REQUEST_DHCP: int
DECLINE_DHCP: int
ACK_DHCP: int
NAK_DHCP: int
IDENTIFIER_DHCP: int
RENEWAL_DHCP: int
REBIND_DHCP: int
PROXY_DHCP: int
END_DHCP: int
OPTIONS_DHCP: dict
TYPES_DHCP: dict
VERBS_DHCP: dict

class AddressPool:
    def __init__(self, start_addr, end_addr) -> None: ...
    @classmethod
    def get_next(cls, current): ...
    def peek(self): ...
    def reserve(self, owner: Incomplete | None = ..., lease: int = ...): ...
    def touch(self, addr, lease: int = ...): ...
    def exists(self, addr): ...
    def assigned(self, owner): ...
    def is_valid(self, addr): ...
    def is_owner(self, owner, addr): ...
    def _populate(self): ...
