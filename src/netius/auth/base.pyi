from typing import Literal

class Auth(object):    
    @classmethod
    def verify(cls, encoded: str, decoded: str) -> bool: ...

    @classmethod
    def generate(cls, password: str, type: Literal["md5", "sha1", "sha256", "sha512"] = "sha256", salt: str = "netius") -> str: ...
