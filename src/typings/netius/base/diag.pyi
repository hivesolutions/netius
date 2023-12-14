"""
This type stub file was generated by pyright.
"""

import appier

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
loaded = ...
class DiagApp(appier.APIApp):
    def __init__(self, system, *args, **kwargs) -> None:
        ...
    
    @appier.route("/logger", "GET")
    def show_logger(self): # -> dict[str, Any]:
        ...
    
    @appier.route("/logger/set", ("GET", "POST"))
    def set_logger(self): # -> dict[str, Any]:
        ...
    
    @appier.route("/environ", "GET")
    def show_environ(self):
        ...
    
    @appier.route("/info", "GET")
    def system_info(self):
        ...
    
    @appier.route("/connections", "GET")
    def list_connections(self):
        ...
    
    @appier.route("/connections/<str:id>", "GET")
    def show_connection(self, id):
        ...
    


