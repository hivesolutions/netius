from typing import Any, Callable, Iterator, Mapping, Sequence

def app(
    environ: Mapping[str, Any],
    start_response: Callable[[str, Sequence[tuple[str, Any]]], Any],
) -> Iterator[str]: ...
