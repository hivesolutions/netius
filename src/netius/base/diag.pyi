from json import JSONEncoder
from typing import Any

from netius import Base
from netius.mock.appier import APIApp

loaded: bool

class DiagEncoder(JSONEncoder):
    def default(self, obj: Any) -> Any: ...

class DiagApp(APIApp):
    system: Base
    show_logger: Any
    set_logger: Any
    show_environ: Any
    system_info: Any
    list_connections: Any
    list_connections_closed: Any
    show_connection: Any

    def __init__(self, system: Base, *args, **kwargs): ...
