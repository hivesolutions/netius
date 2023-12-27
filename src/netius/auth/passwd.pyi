from typing import Mapping, PathLike

from netius import Auth

class PasswdAuth(Auth):
    def __init__(self, path: PathLike[str] | None = ..., *args, **kwargs): ...
    @classmethod
    def auth(
        cls, username: str, password: str, path: str = ..., *args, **kwargs
    ) -> bool: ...
    @classmethod
    def get_passwd(
        cls, path: PathLike[str], cache: bool = ...
    ) -> Mapping[str, str]: ...
    def auth_i(self, username: str, password: str, *args, **kwargs) -> bool: ...
