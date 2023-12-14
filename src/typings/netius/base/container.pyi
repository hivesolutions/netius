"""
This type stub file was generated by pyright.
"""

from . import server
from .common import *

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class Container(Base):
    def __init__(self, *args, **kwargs) -> None:
        ...
    
    def start(self, owner): # -> None:
        ...
    
    def cleanup(self): # -> None:
        ...
    
    def loop(self): # -> None:
        ...
    
    def ticks(self): # -> None:
        ...
    
    def connections_dict(self, full=...): # -> dict[Any, Any]:
        ...
    
    def connection_dict(self, id, full=...): # -> None:
        ...
    
    def on_start(self): # -> None:
        ...
    
    def on_stop(self): # -> None:
        ...
    
    def add_base(self, base): # -> None:
        ...
    
    def remove_base(self, base): # -> None:
        ...
    
    def start_base(self, base): # -> None:
        ...
    
    def start_all(self): # -> None:
        ...
    
    def apply_all(self): # -> None:
        ...
    
    def apply_base(self, base): # -> None:
        ...
    
    def call_all(self, name, *args, **kwargs): # -> None:
        ...
    
    def trigger_all(self, name, *args, **kwargs): # -> None:
        ...
    


class ContainerServer(server.StreamServer):
    def __init__(self, *args, **kwargs) -> None:
        ...
    
    def start(self): # -> None:
        ...
    
    def stop(self): # -> None:
        ...
    
    def cleanup(self): # -> None:
        ...
    
    def add_base(self, base): # -> None:
        ...
    


