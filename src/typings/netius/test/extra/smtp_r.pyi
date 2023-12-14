import netius as netius
import unittest.case
from typing import ClassVar

__version__: str
__revision__: str
__date__: str
PRIVATE_KEY: bytes
MESSAGE: bytes
RESULT: bytes
REGISTRY: dict

class RelaySMTPServerTest(unittest.case.TestCase):
    _classSetupFailed: ClassVar[bool] = ...
    _class_cleanups: ClassVar[list] = ...
    def setUp(self): ...
    def tearDown(self): ...
    def test_dkim(self): ...
