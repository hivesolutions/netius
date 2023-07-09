from typing import Literal

HashType = Literal["plain", "md5", "sha1", "sha256", "sha512"] 

class Auth(object):    
    @classmethod
    def verify(cls, encoded: str, decoded: str) -> bool: ...

    @classmethod
    def generate(cls, password: str, type: HashType = "sha256", salt: str = "netius") -> str: ...

    @classmethod
    def unpack(cls, password: str) -> tuple[HashType, str, str, str]: ...
