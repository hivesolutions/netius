from _typeshed import Incomplete
from typing import ClassVar

__version__: str
__revision__: str
__date__: str

class ArgSpec(tuple):
    _fields: ClassVar[tuple] = ...
    _field_defaults: ClassVar[dict] = ...
    __match_args__: ClassVar[tuple] = ...
    args: Incomplete
    varargs: Incomplete
    keywords: Incomplete
    defaults: Incomplete
    def __init__(self, _cls, args, varargs, keywords, defaults) -> None: ...
    @classmethod
    def _make(cls, iterable): ...
    def _replace(self, **kwds): ...
    def _asdict(self): ...
    def __getnewargs__(self): ...
def ctx_absolute(*args, **kwds): ...

urllib2: None
httplib: None
PYTHON_3: bool
PYTHON_35: bool
PYTHON_36: bool
PYTHON_39: bool
PYTHON_ASYNC: bool
PYTHON_ASYNC_GEN: bool
PYTHON_V: int
OLD_UNICODE: None
STRINGS: tuple
ALL_STRINGS: tuple
INTEGERS: tuple
_xrange: None
_execfile: None
_reduce: None
_reload: None
_unichr: None
def with_meta(meta, *bases): ...
def eager(iterable): ...
def iteritems(associative): ...
def iterkeys(associative): ...
def itervalues(associative): ...
def items(associative): ...
def keys(associative): ...
def values(associative): ...
def xrange(start, stop: Incomplete | None = ..., step: int = ...): ...
def range(start, stop: Incomplete | None = ..., step: Incomplete | None = ...): ...
def ord(value): ...
def chr(value): ...
def chri(value): ...
def bytes(value, encoding: str = ..., errors: str = ..., force: bool = ...): ...
def str(value, encoding: str = ..., errors: str = ..., force: bool = ...): ...
def u(value, encoding: str = ..., errors: str = ..., force: bool = ...): ...
def ascii(value, encoding: str = ..., errors: str = ...): ...
def orderable(value): ...
def is_str(value): ...
def is_unicode(value): ...
def is_bytes(value): ...
def is_string(value, all: bool = ...): ...
def is_generator(value): ...
def is_async_generator(value): ...
def is_unittest(name: str = ...): ...
def execfile(path, global_vars, local_vars: Incomplete | None = ..., encoding: str = ...): ...
def walk(path, visit, arg): ...
def getargspec(func): ...
def has_module(name): ...
def new_module(name): ...
def reduce(*args, **kwargs): ...
def reload(*args, **kwargs): ...
def unichr(*args, **kwargs): ...
def urlopen(*args, **kwargs): ...
def build_opener(*args, **kwargs): ...
def urlparse(*args, **kwargs): ...
def urlunparse(*args, **kwargs): ...
def parse_qs(*args, **kwargs): ...
def urlencode(*args, **kwargs): ...
def quote(*args, **kwargs): ...
def quote_plus(*args, **kwargs): ...
def unquote(*args, **kwargs): ...
def unquote_plus(*args, **kwargs): ...
def cmp_to_key(*args, **kwargs): ...
def tobytes(self, *args, **kwargs): ...
def tostring(self, *args, **kwargs): ...
def StringIO(*args, **kwargs): ...
def BytesIO(*args, **kwargs): ...

class Orderable(tuple):
    def __cmp__(self, value): ...
    def __lt__(self, value) -> bool: ...
