"""
This type stub file was generated by pyright.
"""

from . import base

__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class SimpleAuth(base.Auth):
    def __init__(self, username=..., password=..., *args, **kwargs) -> None:
        ...
    
    @classmethod
    def auth(cls, username, password, target=..., *args, **kwargs): # -> bool:
        ...
    
    def auth_i(self, username, password, *args, **kwargs): # -> bool:
        ...
    


