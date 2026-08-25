from netius import Auth

class SimpleAuth(Auth):
    username: str | None
    password: str | None

    def __init__(
        self, username: str | None = ..., password: str | None = ..., *args, **kwargs
    ): ...
    @classmethod
    def auth(
        cls,
        username: str,
        password: str,
        target: tuple[str, str] | None = ...,
        *args,
        **kwargs
    ) -> bool: ...
    def auth_i(self, username: str, password: str, *args, **kwargs) -> bool: ...
