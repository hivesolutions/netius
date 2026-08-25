# Type Hinting

Netius ships type information for its complete public interface, so that static type checkers like [mypy](https://mypy-lang.org) and [Pyright](https://microsoft.github.io/pyright) are able to verify the code that uses it and editors are able to offer accurate completion.

## Usage

There's nothing to install and nothing to enable, the type information travels inside the package itself and every [PEP 561](https://peps.python.org/pep-0561) compliant tool picks it up automatically:

```bash
pip install netius mypy
mypy my_server.py
```

## Type stubs

The types are provided as stub files (`.pyi`) placed next to the module they describe, together with the `py.typed` marker that tells the type checkers that the package is a typed one. The stubs are the only source of type information, the implementation itself carries no annotations.

This separation is deliberate. Netius is meant to run under Python 2.7 as well, where the annotation syntax is a syntax error, and a stub file is never imported at runtime so it's free to use the modern syntax without any compatibility concern.

## Conventions

A stub mirrors the module it describes, declaring every class, every method in source order, every public module level constant and every public attribute assigned in the constructor:

```python
from typing import Any, Mapping
from uuid import UUID

class NetiusError(Exception):
    kwargs: Mapping[str, Any]
    message: str
    code: int

    def __init__(self, *args, **kwargs): ...
    def get_kwarg(self, name: str, default: Any = ...) -> Any: ...
    @property
    def uid(self) -> UUID: ...
```

Note that the return annotation is omitted whenever the value returned is `None`, that default values are always written as `...` and that both `*args` and `**kwargs` are left untyped. Prefer `Mapping` and `Sequence` over `dict` and `list` for values that are only read, and use `Any` whenever the implementation is genuinely dynamic, an honest `Any` is better than an invented type.

## Validation

The stubs are verified against the real objects using `stubtest`, which catches a missing member, a misspelt parameter, a wrong default value and a declaration that no longer exists:

```bash
pip install mypy
PYTHONPATH=src python -m mypy.stubtest --allowlist stubtest.txt \
  --ignore-unused-allowlist \
  netius.adapters netius.auth netius.base netius.clients \
  netius.common netius.extra netius.middleware netius.mock \
  netius.pool netius.servers netius.sh
```

This runs as part of the main workflow, so a stub that drifts away from its implementation fails the build. The test suite additionally verifies that every module has a stub and that no stub has been left behind by a removed module.
