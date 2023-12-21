import netius as netius
import netius.common.parser
import netius.common.parser as parser

__version__: str
__revision__: str
__date__: str

class SMTPParser(netius.common.parser.Parser):
    def __init__(self, owner, store: bool = ...) -> None: ...
    def parse(self, data): ...
    def _parse_line(self, data): ...
