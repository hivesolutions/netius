import netius.base.async_old
import netius.base.async_old as async_old
import netius.base.errors as errors
import netius.base.legacy as legacy
from typing import ClassVar, Any, Generator, Tuple, Union, Callable, Optional, Type, ModuleType

class Future(netius.base.async_old.Future):
    def __iter__(self) -> Future: ...
    def __await__(self) -> Generator[None, None, Any]:  ...

class Future:
    def __iter__(self) -> Future: ...
    def __await__(self) -> Generator[None, None, Any]: ...

class AwaitWrapper:
    _is_generator: ClassVar[bool] = ...
    def __init__(self, generator: Generator, generate: bool = ...) -> None: ...
    def __await__(self)-> (Generator[Any, Any, Any | None] | Generator[None, Any, Generator[Any, Any, None] | Any]): ...
    def __iter__(self) -> AwaitWrapper: ...
    def __next__(self) -> Any: ...
    def next(self) -> Any: ...
    def generate(self, value: Any) -> Generator[Any, Any, None]: ...
    def _await_generator(self) -> Generator[Any, Any, Any | None]: ...
    def _await_basic(self) -> Generator[None, Any, Generator[Any, Any, None] | Any]: ...

class CoroutineWrapper:
    def __init__(self, coroutine: Generator) -> None: ...
    def __iter__(self) -> CoroutineWrapper: ...
    def __next__(self) -> Any: ...
    def next(self) -> Any: ...
    def restore(self, value: Any) -> None: ...

def coroutine(function: Callable) -> Callable: ...
def ensure_generator(value: Any) -> Tuple[bool, Union[Generator, CoroutineWrapper, Any]]: ...
def get_asyncio() -> Optional[Type[ModuleType]]: ...
def is_coroutine(callable: Callable) -> bool: ...
def is_coroutine_object(generator: Any) -> bool: ...
def is_coroutine_native(generator: Any) -> bool: ...
def is_future(future: Any) -> bool: ...
def _sleep(timeout: float, compat: bool = ...) -> Generator: ...
def _wait(event: Any, timeout: Optional[float] = ..., future: Any = ...) -> AwaitWrapper: ...
def sleep(*args, **kwargs) -> AwaitWrapper: ...
def wait(*args, **kwargs) -> AwaitWrapper: ...
def coroutine_return(coroutine: CoroutineWrapper) -> AwaitWrapper: ...
def _coroutine_return(coroutine: CoroutineWrapper) -> Generator[Any, None, Any]: ...
