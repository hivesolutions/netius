"""
This type stub file was generated by pyright.
"""

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
def upnp_map(ext_port, int_port, host, protocol=..., description=...): # -> None:
    """
    Defines a router port forwarding rule using an UPnP based
    request that tries to find the first available router.

    In case there's no available router with UPnP features the
    client may become idle, leaking memory.

    :see: http://www.upnp.org/specs/gw/UPnP-gw-WANIPConnection-v1-Service.pdf
    """
    ...

