"""
This type stub file was generated by pyright.
"""

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
REQUEST_TIMEOUT = ...
class Request:
    """
    Abstract request structure used to represent
    a request in a server/client model, this allows
    for easy identification and response (callback).
    """
    IDENTIFIER = ...
    def __init__(self, timeout=..., callback=...) -> None:
        ...
    


class Response:
    """
    Top level abstract representation of a response to
    be sent based on a previously created request, the
    input of this object should be raw data and a relation
    between the request and the response is required.

    The association/relation between the response and the
    request should be done using the original request
    generated identifier.
    """
    def __init__(self, data, request=...) -> None:
        ...
    
    def parse(self): # -> None:
        ...
    
    def get_request(self): # -> None:
        ...
    
    def get_id(self):
        ...
    


