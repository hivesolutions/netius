from typing import Mapping

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
OPTIONS_DHCP: Mapping[str, int]
TYPES_DHCP: Mapping[int, str]
VERBS_DHCP: Mapping[int, str]

class AddressPool:
    start_addr: str
    end_addr: str
    map: dict[str, int]
    owners: dict[str, str | None]
    owners_i: dict[str | None, str]
    addrs: list[tuple[int, str]]

    def __init__(self, start_addr: str, end_addr: str): ...
    @classmethod
    def get_next(cls, current: str) -> str: ...
    def peek(self) -> str: ...
    def reserve(self, owner: str | None = ..., lease: int = ...) -> str: ...
    def touch(self, addr: str, lease: int = ...): ...
    def exists(self, addr: str) -> bool: ...
    def assigned(self, owner: str | None) -> str | None: ...
    def is_valid(self, addr: str) -> bool: ...
    def is_owner(self, owner: str | None, addr: str) -> bool: ...
    def _populate(self): ...
