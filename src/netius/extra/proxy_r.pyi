from re import Match, Pattern
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import ParseResult

from netius import Connection, Protocol
from netius.clients import DNSResponse, HTTPClient
from netius.common import HTTP2Parser, HTTP2Stream, HTTPParser, PriorityDict
from netius.servers import HTTPConnection, ProxyServer

DEFAULT_NAME: str

class ReverseProxyServer(ProxyServer):
    hosts_o: dict[str, tuple[Sequence[str], list[list[str]]]] | None
    busy_conn: int

    def __init__(
        self,
        config: str = ...,
        regex: (
            Mapping[Pattern[str], str | Sequence[str]]
            | Sequence[tuple[Pattern[str], str | Sequence[str]]]
        ) = ...,
        hosts: Mapping[str, str | Sequence[str]] = ...,
        alias: Mapping[str, str] = ...,
        auth: Mapping[str, Any] = ...,
        auth_regex: (
            Mapping[Pattern[str], Any] | Sequence[tuple[Pattern[str], Any]]
        ) = ...,
        redirect: Mapping[str, str | Sequence[str]] = ...,
        redirect_regex: (
            Mapping[Pattern[str], str | Sequence[str]]
            | Sequence[tuple[Pattern[str], str | Sequence[str]]]
        ) = ...,
        error_urls: Mapping[str, str] = ...,
        forward: str | Sequence[str] | None = ...,
        strategy: str = ...,
        reuse: bool = ...,
        sts: int = ...,
        resolve: bool = ...,
        resolve_t: float = ...,
        host_f: bool = ...,
        echo: bool = ...,
        x_forwarded_port: str | None = ...,
        x_forwarded_proto: str | None = ...,
        *args,
        **kwargs
    ): ...
    def info_dict(self, full: bool = ...) -> dict[str, Any]: ...
    def proxy_r_dict(self) -> dict[str, Any]: ...
    def on_diag(self): ...
    def on_start(self): ...
    def on_serve(self): ...
    def on_headers(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Parser | HTTP2Stream | None,
    ): ...
    def rules(
        self,
        url: str,
        parser: HTTPParser | HTTP2Stream,
        url_o: str | None = ...,
    ) -> tuple[str | None, tuple[str, PriorityDict] | None]: ...
    def rules_regex(
        self, url: str, parser: HTTPParser | HTTP2Stream
    ) -> tuple[str | None, tuple[str, PriorityDict] | None]: ...
    def rules_host(
        self, url: str, parser: HTTPParser | HTTP2Stream
    ) -> tuple[str | None, tuple[str, PriorityDict] | None]: ...
    def rules_forward(
        self, url: str, parser: HTTPParser | HTTP2Stream
    ) -> tuple[str | None, tuple[str, PriorityDict] | None]: ...
    def balancer(
        self, values: str | Sequence[str] | None
    ) -> tuple[str | None, tuple[str, PriorityDict] | None]: ...
    def balancer_robin(self, values: Sequence[str]) -> tuple[str, None]: ...
    def balancer_smart(
        self, values: Sequence[str]
    ) -> tuple[str, tuple[str, PriorityDict]]: ...
    def acquirer(self, state: tuple[str, PriorityDict] | None): ...
    def acquirer_robin(self, state: tuple[str, PriorityDict] | None): ...
    def acquirer_smart(self, state: tuple[str, PriorityDict] | None): ...
    def releaser(self, state: tuple[str, PriorityDict] | None): ...
    def releaser_robin(self, state: tuple[str, PriorityDict] | None): ...
    def releaser_smart(self, state: tuple[str, PriorityDict] | None): ...
    def dns_start(self, timeout: float = ...): ...
    def dns_tick(self, timeout: float = ...): ...
    def dns_callback(
        self,
        host: str,
        hostname: str,
        parsed: ParseResult,
        index: int = ...,
        resolved: list[list[str]] = ...,
    ) -> Callable[[DNSResponse], None]: ...
    def _on_prx_message(
        self, client: HTTPClient, parser: HTTPParser, message: bytes
    ): ...
    def _on_prx_close(self, client: HTTPClient, _connection: Connection | Protocol): ...
    def _upgrade(
        self,
        connection: HTTPConnection | HTTP2Stream,
        parser: HTTPParser | HTTP2Stream,
        prefix: str,
        path: str,
        headers: dict[str, str | Sequence[str]],
        state: tuple[str, PriorityDict] | None = ...,
    ): ...
    def _apply_all(
        self,
        parser: HTTPParser | HTTP2Parser | None,
        connection: HTTPConnection,
        headers: dict[str, str | Sequence[str]],
        upper: bool = ...,
        normalize: bool = ...,
        replace: bool = ...,
    ): ...
    def _apply_headers(
        self,
        parser: HTTPParser | HTTP2Stream | None,
        connection: HTTPConnection | HTTP2Stream,
        parser_prx: HTTPParser,
        headers: dict[str, str | Sequence[str]],
        upper: bool = ...,
    ): ...
    def _set_strategy(self): ...
    def _resolve_regex(
        self,
        value: str,
        regexes: Sequence[tuple[Pattern[str], Any]],
        default: Any = ...,
    ) -> tuple[Any, Match[str] | None]: ...
    def _echo(self, sort: bool = ...): ...
    def _echo_regex(self, sort: bool = ...): ...
    def _echo_hosts(self, sort: bool = ...): ...
    def _echo_alias(self, sort: bool = ...): ...
    def _echo_redirect(self, sort: bool = ...): ...
    def _echo_error_urls(self, sort: bool = ...): ...
