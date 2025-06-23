import typing
import collections.abc
from contextlib import AsyncExitStack, ExitStack

from fundi import CallableInfo

from fundi_alt.scope import Scope

R = typing.TypeVar("R")

AnyCallable = typing.Callable[..., typing.Any]

def injection_impl(
    scope: Scope,
    info: CallableInfo[typing.Any],
    cache: collections.abc.MutableMapping[int, typing.Any],
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]],
) -> collections.abc.Generator[
    tuple[Scope | dict[str, typing.Any], CallableInfo[typing.Any], bool], typing.Any, None
]: ...
@typing.overload
def inject(
    scope: Scope,
    info: CallableInfo[collections.abc.Iterable[R]],
    stack: ExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
def inject(
    scope: Scope,
    info: CallableInfo[collections.abc.AsyncIterable[R]],
    stack: ExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
def inject(
    scope: Scope,
    info: CallableInfo[R],
    stack: ExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
async def ainject(
    scope: Scope,
    info: CallableInfo[collections.abc.Iterable[R]],
    stack: AsyncExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
async def ainject(
    scope: Scope,
    info: CallableInfo[collections.abc.AsyncIterable[R]],
    stack: AsyncExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
async def ainject(
    scope: Scope,
    info: CallableInfo[collections.abc.Awaitable[R]],
    stack: AsyncExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
@typing.overload
async def ainject(
    scope: Scope,
    info: CallableInfo[R],
    stack: AsyncExitStack,
    visited: set[AnyCallable] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
    override: collections.abc.Mapping[AnyCallable, CallableInfo[typing.Any]] | None = None,
) -> R: ...
