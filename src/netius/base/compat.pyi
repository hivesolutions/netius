from socket import socket
from ssl import SSLContext
from types import ModuleType
from typing import Any, Callable, Generator, NoReturn, Sequence

from netius import Executor, Future, Handle, Task
from netius.base.async_neo import AwaitWrapper
from netius.base.common import AbstractBase

asyncio: ModuleType | None
BaseLoop: type

class CompatLoop:
    def __init__(self, loop: AbstractBase): ...
    def __getattr__(self, name: str) -> Any: ...
    def time(self) -> float: ...
    def call_soon(self, callback: Callable[..., Any], *args) -> Handle: ...
    def call_soon_threadsafe(self, callback: Callable[..., Any], *args) -> Handle: ...
    def call_at(self, when: float, callback: Callable[..., Any], *args) -> Handle: ...
    def call_later(
        self, delay: float, callback: Callable[..., Any], *args
    ) -> Handle: ...
    def create_future(self) -> Future: ...
    def create_task(self, coroutine: Any) -> Task: ...
    def create_server(self, *args, **kwargs) -> AwaitWrapper: ...
    def create_connection(self, *args, **kwargs) -> AwaitWrapper: ...
    def create_datagram_endpoint(self, *args, **kwargs) -> AwaitWrapper: ...
    def getaddrinfo(self, *args, **kwargs) -> AwaitWrapper: ...
    def getnameinfo(self, *args, **kwargs) -> AwaitWrapper: ...
    def run_until_complete(self, future: Any) -> Any: ...
    def run_forever(self): ...
    def run_in_executor(self, *args, **kwargs) -> AwaitWrapper: ...
    def stop(self): ...
    def close(self): ...
    def get_exception_handler(self) -> Callable[[dict[str, Any]], Any] | None: ...
    def set_exception_handler(
        self, handler: Callable[[dict[str, Any]], Any] | None
    ): ...
    def default_exception_handler(self, context: dict[str, Any]): ...
    def call_exception_handler(self, context: dict[str, Any]) -> Any: ...
    def get_debug(self) -> bool: ...
    def set_debug(self, enabled: bool): ...
    def set_default_executor(self, executor: Executor): ...
    def get_task_factory(self) -> Callable[..., Any]: ...
    def set_task_factory(self, factory: Callable[..., Any]): ...
    def is_running(self) -> bool: ...
    def is_closed(self) -> bool: ...
    def _getaddrinfo(
        self,
        host: str | None,
        port: int | str | None,
        family: int = ...,
        type: int = ...,
        proto: int = ...,
        flags: int = ...,
    ) -> Generator[Future, Any, None]: ...
    def _getnameinfo(self, sockaddr: tuple[Any, ...], flags: int = ...) -> NoReturn: ...
    def _run_in_executor(
        self, executor: Executor | None, func: Callable[..., Any], *args
    ) -> Generator[Future, Any, None]: ...
    def _create_server(
        self,
        protocol_factory: Callable[[], Any],
        host: str | None = ...,
        port: int | None = ...,
        family: int = ...,
        flags: int = ...,
        sock: socket | None = ...,
        backlog: int = ...,
        ssl: bool | SSLContext | None = ...,
        reuse_address: bool | None = ...,
        reuse_port: bool | None = ...,
        start_serving: bool = ...,
        *args,
        **kwargs
    ) -> Generator[Future, Any, None]: ...
    def _create_connection(
        self,
        protocol_factory: Callable[[], Any],
        host: str | None = ...,
        port: int | None = ...,
        ssl: bool | SSLContext | None = ...,
        family: int = ...,
        proto: int = ...,
        flags: int = ...,
        sock: socket | None = ...,
        local_addr: tuple[str, int] | None = ...,
        server_hostname: str | None = ...,
        *args,
        **kwargs
    ) -> Generator[Future, Any, None]: ...
    def _create_datagram_endpoint(
        self,
        protocol_factory: Callable[[], Any],
        local_addr: tuple[str, int] | None = ...,
        remote_addr: tuple[str, int] | None = ...,
        family: int = ...,
        proto: int = ...,
        flags: int = ...,
        reuse_address: bool | None = ...,
        reuse_port: bool | None = ...,
        allow_broadcast: bool | None = ...,
        sock: socket | None = ...,
        *args,
        **kwargs
    ) -> Generator[Future, Any, None]: ...
    def _start_serving(
        self,
        protocol_factory: Callable[[], Any],
        sock: socket,
        sslcontext: SSLContext | None = ...,
        server: Any = ...,
        backlog: int = ...,
        ssl_handshake_timeout: float | None = ...,
    ): ...
    def _set_current_task(self, task: Any): ...
    def _unset_current_task(self): ...
    def _call_delay(
        self,
        callback: Callable[..., Any],
        args: Sequence[Any],
        timeout: float | None = ...,
        immediately: bool = ...,
        verify: bool = ...,
        safe: bool = ...,
    ) -> Handle: ...
    def _sleep(self, timeout: float, future: Future | None = ...) -> Future: ...
    def _default_handler(self, context: dict[str, Any]): ...
    @property
    def _thread_id(self) -> int | None: ...
    @property
    def _current_tasks(self) -> dict[Any, Any]: ...

def is_compat() -> bool: ...
def is_asyncio() -> bool: ...
def run(coro: Any): ...
def build_datagram(*args, **kwargs) -> Any: ...
def connect_stream(*args, **kwargs) -> Any: ...
def serve_stream(*args, **kwargs) -> Any: ...
def _build_datagram_native(
    protocol_factory: Callable[[], Any],
    family: int = ...,
    type: int = ...,
    remote_host: str | None = ...,
    remote_port: int | None = ...,
    callback: Callable[[tuple[Any, Any]], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
def _build_datagram_compat(
    protocol_factory: Callable[[], Any],
    family: int = ...,
    type: int = ...,
    remote_host: str | None = ...,
    remote_port: int | None = ...,
    callback: Callable[[tuple[Any, Any]], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
def _connect_stream_native(
    protocol_factory: Callable[[], Any],
    host: str,
    port: int,
    ssl: bool | SSLContext = ...,
    key_file: str | None = ...,
    cer_file: str | None = ...,
    ca_file: str | None = ...,
    ca_root: bool = ...,
    ssl_verify: bool = ...,
    family: int = ...,
    type: int = ...,
    callback: Callable[[tuple[Any, Any]], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
def _connect_stream_compat(
    protocol_factory: Callable[[], Any],
    host: str,
    port: int,
    ssl: bool | SSLContext = ...,
    key_file: str | None = ...,
    cer_file: str | None = ...,
    ca_file: str | None = ...,
    ca_root: bool = ...,
    ssl_verify: bool = ...,
    family: int = ...,
    type: int = ...,
    callback: Callable[[tuple[Any, Any]], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
def _serve_stream_native(
    protocol_factory: Callable[[], Any],
    host: str,
    port: int,
    ssl: bool | SSLContext = ...,
    key_file: str | None = ...,
    cer_file: str | None = ...,
    ca_file: str | None = ...,
    ca_root: bool = ...,
    ssl_verify: bool = ...,
    family: int = ...,
    type: int = ...,
    backlog: int | None = ...,
    reuse_address: bool | None = ...,
    reuse_port: bool | None = ...,
    callback: Callable[[Any], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
def _serve_stream_compat(
    protocol_factory: Callable[[], Any],
    host: str,
    port: int,
    ssl: bool | SSLContext = ...,
    key_file: str | None = ...,
    cer_file: str | None = ...,
    ca_file: str | None = ...,
    ca_root: bool = ...,
    ssl_verify: bool = ...,
    family: int = ...,
    type: int = ...,
    backlog: int | None = ...,
    reuse_address: bool | None = ...,
    reuse_port: bool | None = ...,
    callback: Callable[[Any], Any] | None = ...,
    loop: Any = ...,
    *args,
    **kwargs
) -> Any: ...
