"""
This type stub file was generated by pyright.
"""

import netius

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class EchoProtocol(netius.StreamProtocol):
    ...


class EchoServer(netius.ServerAgent):
    protocol = EchoProtocol


if __name__ == "__main__":
    server = ...
else:
    __path__ = ...
