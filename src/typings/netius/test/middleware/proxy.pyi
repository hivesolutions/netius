import netius as netius
import unittest.case
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class ProxyMiddlewareTest(unittest.case.TestCase):
    _classSetupFailed: ClassVar[bool] = ...
    _class_cleanups: ClassVar[list] = ...
    def setUp(self): ...
    def tearDown(self): ...
    def test_ipv4_v1(self): ...
    def test_ipv6_v1(self): ...
    def test_starter_v1(self): ...
    def test_starter_v2(self): ...
