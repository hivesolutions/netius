"""
This type stub file was generated by pyright.
"""

from . import async_old

__author__ = ...
__version__ = ...
__revision__ = ...
__date__ = ...
__copyright__ = ...
__license__ = ...
class Future(async_old.Future):
    """
    Specialized Future class that supports the async/await
    syntax to be used in a future, so that it becomes compliant
    with the basic Python asyncio strategy for futures.

    Using this future it should be possible to ``await Future()`
    for a simpler usage.
    """
    def __iter__(self): # -> Generator[Self, Any, Any | None]:
        ...
    
    def __await__(self): # -> Generator[Self, Any, Any | None]:
        ...
    


class AwaitWrapper:
    """
    Wrapper class meant to be used to encapsulate "old"
    generator based objects as async generator objects that
    are eligible to be used with the async/await syntax.

    It's also possible to pass simple values instead of
    generator functions and still use the wrapper.
    """
    _is_generator = ...
    def __init__(self, generator, generate=...) -> None:
        ...
    
    def __await__(self): # -> Generator[Any, Any, Any | None] | Generator[None, Any, Generator[Any, Any, None] | Any]:
        ...
    
    def __iter__(self): # -> Self:
        ...
    
    def __next__(self):
        ...
    
    def next(self):
        ...
    
    def generate(self, value): # -> Generator[Any, Any, None]:
        ...
    


class CoroutineWrapper:
    """
    Wrapper class meant to encapsulate a coroutine object
    as a standard iterator sequence to be used in chain/iterator
    like execution environment.

    This is only required for the native coroutine objects
    so that they can comply with the required netius interface.
    """
    def __init__(self, coroutine) -> None:
        ...
    
    def __iter__(self): # -> Self:
        ...
    
    def __next__(self):
        ...
    
    def next(self):
        ...
    
    def restore(self, value): # -> None:
        ...
    


def coroutine(function): # -> _Wrapped[Callable[..., Any], Any, Callable[..., Any], AwaitWrapper]:
    ...

def ensure_generator(value): # -> tuple[Literal[True], Any] | tuple[Literal[True], CoroutineWrapper] | tuple[Literal[False], Any]:
    ...

def get_asyncio(): # -> Any | None:
    ...

def is_coroutine(callable): # -> bool:
    ...

def is_coroutine_object(generator): # -> bool:
    ...

def is_coroutine_native(generator): # -> bool:
    ...

def is_future(future): # -> bool:
    ...

def sleep(*args, **kwargs): # -> AwaitWrapper:
    ...

def wait(*args, **kwargs): # -> AwaitWrapper:
    ...

def coroutine_return(coroutine): # -> AwaitWrapper:
    """
    Allows for the abstraction of the return value of a coroutine
    object to be the result of the future yield as the first element
    of the generator.

    This allows the possibility to provide compatibility with the legacy
    not return allowed generators.

    :type coroutine: CoroutineObject
    :param coroutine: The coroutine object that is going to be yield back
    and have its last future result returned from the generator.
    """
    ...

