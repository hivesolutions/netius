import netius as netius
import unittest.case
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class SimpleAuthTest(unittest.case.TestCase):
    _classSetupFailed: ClassVar[bool] = ...
    _class_cleanups: ClassVar[list] = ...
    def test_simple(self): ...
