import typing
import collections.abc
from contextlib import AsyncExitStack, ExitStack

from fundi import CallableInfo
from fundi.util import add_injection_trace, call_async, call_sync

from fundi_alt.scope import Scope
from fundi_alt.resolve import resolve
from fundi_alt.exceptions import DependencyCycleError


def injection_impl(
    scope: Scope,
    info: CallableInfo[typing.Any],
    cache: collections.abc.MutableMapping[int, typing.Any],
) -> collections.abc.Generator[
    tuple[Scope | dict[str, typing.Any], CallableInfo[typing.Any], bool], typing.Any, None
]:
    """
    Injection brain.

    This creepy thing does the following:

    - Iterates over function parameters and resolves their values one by one:

      - If the parameter comes from a dependency (`from_`):
        - Checks the cache:
          - If value is cached — uses it.
          - Otherwise — yields `(scope, dependency, True)` to request the caller to resolve it.
        - Once the value is received — stores it in cache if needed.

      - If the parameter should be resolved by type:
        - Calls `scope.resolve_by_type(annotation)`.
          - If the result is a regular value — stores it.
          - If the result is a `CallableInfo` and it's not compatible with the desired type:
            - Yields `(scope, dependency, True)` to let the caller resolve it.
        - Once the value is received — stores it (and optionally caches it).

      - If the parameter should be resolved by name:
        - Calls `scope.resolve_by_name(parameter.name)`.
        - If resolution fails and the parameter has a default — uses it.

    - Finally, yields `(values, info, False)` — the fully resolved parameter dictionary,
      along with the original callable info.
    """
    values: dict[str, typing.Any] = {}
    try:
        for result in resolve(scope, info, cache):
            if result.resolved:
                values[result.parameter.name] = result.value
                continue

            assert result.dependency is not None
            dependency = result.dependency

            # Set current parameter for nested injections
            # this is implementation of Parameter-aware dependencies support
            child = scope.child()
            child.value("__fundi_parameter__", result.parameter)

            value = yield child, dependency, True

            if dependency.use_cache:
                cache[id(dependency.call)] = value

            values[result.parameter.name] = value

        yield values, info, False
    except Exception as exc:
        add_injection_trace(exc, info, values)
        raise


def inject(
    scope: Scope,
    info: CallableInfo[typing.Any],
    stack: ExitStack,
    visited: set[typing.Callable[..., typing.Any]] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
) -> typing.Any:
    if info.async_:
        raise ValueError("Non-async injection support only non-async dependencies")

    if visited is None:
        visited = set()

    if info.call in visited:
        raise DependencyCycleError(info.call, visited)

    visited.add(info.call)

    if cache is None:
        cache = {}

    gen = injection_impl(scope, info, cache)

    try:
        value: typing.Any | None = None
        while True:
            inner_scope, inner_info, more = gen.send(value)

            if more and isinstance(inner_scope, Scope):
                value = inject(inner_scope, inner_info, stack, visited.copy())
                continue

            assert isinstance(inner_scope, collections.abc.Mapping)

            return call_sync(stack, inner_info, inner_scope)
    except Exception as exc:
        # Add injection trace to exception
        _ = gen.throw(type(exc), exc, exc.__traceback__)


async def ainject(
    scope: Scope,
    info: CallableInfo[typing.Any],
    stack: AsyncExitStack,
    visited: set[typing.Callable[..., typing.Any]] | None = None,
    cache: collections.abc.MutableMapping[int, typing.Any] | None = None,
) -> typing.Any:
    if visited is None:
        visited = set()

    if info.call in visited:
        raise DependencyCycleError(info.call, visited)

    visited.add(info.call)

    if cache is None:
        cache = {}

    gen = injection_impl(scope, info, cache)

    value: typing.Any | None = None

    try:
        while True:
            inner_scope, inner_info, more = gen.send(value)

            if more and isinstance(inner_scope, Scope):
                value = await ainject(inner_scope, inner_info, stack, visited.copy())
                continue

            assert isinstance(inner_scope, collections.abc.Mapping)

            if info.async_:
                return await call_async(stack, inner_info, inner_scope)

            return call_sync(stack, inner_info, inner_scope)
    except Exception as exc:
        # Add injection trace to exception
        _ = gen.throw(type(exc), exc, exc.__traceback__)
