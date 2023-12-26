import netius as netius
import netius.base.async_old as async_old
import netius.base.asynchronous as asynchronous
import netius.base.common
import netius.base.compat as compat
import netius.base.config as config
import netius.base.errors as errors
import netius.base.legacy as legacy
import netius.base.log as log
import netius.base.observer as observer
import netius.base.server
import netius.base.server as server
import netius.base.tls as tls
import netius.base.util as util
import netius.middleware as middleware
from netius.base.async_neo import (
    AwaitWrapper as AwaitWrapper,
    CoroutineWrapper as CoroutineWrapper,
    Future as Future,
    coroutine as coroutine,
    coroutine_return as coroutine_return,
    ensure_generator as ensure_generator,
    get_asyncio as get_asyncio,
    is_coroutine as is_coroutine,
    is_coroutine_native as is_coroutine_native,
    is_coroutine_object as is_coroutine_object,
    is_future as is_future,
    sleep as sleep,
    wait as wait,
)
from netius.base.async_old import (
    Executor as Executor,
    Handle as Handle,
    Task as Task,
    ThreadPoolExecutor as ThreadPoolExecutor,
    async_test as async_test,
    async_test_all as async_test_all,
    is_asynclib as is_asynclib,
    is_await as is_await,
    is_neo as is_neo,
    notify as notify,
    wakeup as wakeup,
)
from netius.base.common import (
    AbstractBase as AbstractBase,
    Base as Base,
    BaseThread as BaseThread,
    DiagBase as DiagBase,
    build_future as build_future,
    compat_loop as compat_loop,
    ensure as ensure,
    ensure_asyncio as ensure_asyncio,
    ensure_loop as ensure_loop,
    ensure_main as ensure_main,
    ensure_pool as ensure_pool,
    get_event_loop as get_event_loop,
    get_loop as get_loop,
    get_main as get_main,
    get_poll as get_poll,
    new_loop as new_loop,
    new_loop_asyncio as new_loop_asyncio,
    new_loop_main as new_loop_main,
    stop_loop as stop_loop,
)
from netius.base.conn import (
    BaseConnection as BaseConnection,
    Connection as Connection,
    DiagConnection as DiagConnection,
)
from netius.base.poll import (
    EpollPoll as EpollPoll,
    KqueuePoll as KqueuePoll,
    Poll as Poll,
    PollPoll as PollPoll,
    SelectPoll as SelectPoll,
)

from typing import Any

OPEN: int
CLOSED: int
PENDING: int
CHUNK_SIZE: int
is_diag: bool
POLL_TIMEOUT: float
NAME: str
VERSION: str
PLATFORM: str
IDENTIFIER_TINY: str
IDENTIFIER_SHORT: str
IDENTIFIER_LONG: str
IDENTIFIER: str
WSAEWOULDBLOCK: int
WSAECONNABORTED: int
WSAECONNRESET: int
SSL_ERROR_CERT_ALREADY_IN_HASH_TABLE: int
POLL_ORDER: tuple
SILENT_ERRORS: tuple
VALID_ERRORS: tuple
SSL_SILENT_ERRORS: tuple
SSL_VALID_ERRORS: tuple
SSL_ERROR_NAMES: dict
SSL_VALID_REASONS: tuple
TCP_TYPE: int
UDP_TYPE: int
STATE_STOP: int
STATE_START: int
STATE_PAUSE: int
STATE_CONFIG: int
STATE_POLL: int
STATE_TICK: int
STATE_READ: int
STATE_WRITE: int
STATE_ERRROR: int
STATE_STRINGS: tuple
KEEPALIVE_TIMEOUT: int
KEEPALIVE_INTERVAL: int
KEEPALIVE_COUNT: int
ALLOW_BLOCK: bool
LOG_FORMAT: str
BASE_PATH: str
EXTRAS_PATH: str
SSL_KEY_PATH: str
SSL_CER_PATH: str
SSL_CA_PATH: None
SSL_DH_PATH: str

class Container(netius.base.common.AbstractBase):
    def __init__(self, *args, **kwargs) -> None: ...
    def start(self, owner: Any) -> None: ...
    def cleanup(self) -> None: ...
    def loop(self) -> None: ...
    def ticks(self) -> None: ...
    def connections_dict(self, full: bool = ...) -> dict: ...
    def connection_dict(self, id, full: bool = ...) -> dict | None: ...
    def on_start(self) -> None: ...
    def on_stop(self) -> None: ...
    def add_base(self, base: Any) -> None: ...
    def remove_base(self, base: Any) -> None: ...
    def start_base(self, base: Any): ...
    def start_all(self) -> None: ...
    def apply_all(self) -> None: ...
    def apply_base(self, base: Any) -> None: ...
    def call_all(self, name: str, *args, **kwargs) -> None: ...
    def trigger_all(self, name: str, *args, **kwargs) -> None: ...

class ContainerServer(netius.base.server.StreamServer):
    def __init__(self, *args, **kwargs) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def cleanup(self) -> None: ...
    def add_base(self, base: str) -> None: ...
