import netius.adapters.base
import netius.adapters.base as base

__version__: str
__revision__: str
__date__: str

class MongoAdapter(netius.adapters.base.BaseAdapter):
    def set(self, value, owner: str = ...): ...
    def get(self, key): ...
