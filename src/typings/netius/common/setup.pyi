__version__: str
__revision__: str
__date__: str
CA_URL: str
COMMON_PATH: str
BASE_PATH: str
EXTRAS_PATH: str
SSL_CA_PATH: str
def ensure_setup(): ...
def ensure_ca(path: str = ...): ...
def _download_ca(path: str = ..., raise_e: bool = ...): ...
def _store_contents(contents, path): ...
