from netius import Auth

class DummyAuth(Auth):
    value: bool

    def __init__(self, value: bool = ..., *args, **kwargs): ...
    @classmethod
    def auth(cls, value: bool = ..., *args, **kwargs) -> bool: ...
