import netius as netius
import unittest.case
from typing import ClassVar

__version__: str
__revision__: str
__date__: str
PRIVATE_KEY: bytes
PUBLIC_KEY: bytes
DNS_LABEL: bytes
MESSAGE: bytes
RESULT: bytes

class DKIMTest(unittest.case.TestCase):
    _classSetupFailed: ClassVar[bool] = ...
    _class_cleanups: ClassVar[list] = ...
    def test_simple(self): ...
