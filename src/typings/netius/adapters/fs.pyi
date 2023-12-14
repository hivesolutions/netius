import netius as netius
import netius.adapters.base
import netius.adapters.base as base
from _typeshed import Incomplete

__version__: str
__revision__: str
__date__: str

class FsAdapter(netius.adapters.base.BaseAdapter):
    def __init__(self, base_path: Incomplete | None = ...) -> None: ...
    def set(self, value, owner: str = ...): ...
    def get_file(self, key, mode: str = ...): ...
    def delete(self, key, owner: str = ...): ...
    def size(self, key): ...
    def count(self, owner: Incomplete | None = ...): ...
    def list(self, owner: Incomplete | None = ...): ...
    def _path(self, owner: Incomplete | None = ...): ...
    def _ensure(self, owner): ...
    def _symlink(self, source, target): ...
