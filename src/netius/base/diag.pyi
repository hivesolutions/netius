import netius as netius
import netius.mock.appier
import netius.mock.appier as appier

loaded: bool

class DiagApp(netius.mock.appier.APIApp):

    def __init__(self, system, *args, **kwargs) -> None: ...
