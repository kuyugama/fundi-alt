import typing
import collections.abc
from contextlib import AsyncExitStack, ExitStack

from fundi import CallableInfo
from fundi.util import call_async, call_sync

from fundi_alt.scope import Scope
from fundi_alt.util import normalize_annotation
from fundi_alt.exceptions import DependencyCycleError, ScopeResolutionError


def _cache_status(
    info: CallableInfo[typing.Any], cache: collections.abc.MutableMapping[int, typing.Any]
) -> tuple[int, bool, bool]:
    """
    Cache status helper. Determines whether cache value can be read or set

    returns (cache_id, is_cached, can_be_cached)
    """
    id_ = id(info.call)
    if not info.use_cache:
        return id_, False, False

    if id(info.call) in cache:
        return id_, True, False

    return id_, False, True


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

    for parameter in info.parameters:
        scope.value("__fundi_parameter__", parameter)
        if parameter.from_ is not None:
            dependency = parameter.from_

            id_, cached, can_be_cached = _cache_status(dependency, cache)

            if cached:
                value = cache[id_]
            else:
                value = yield scope, dependency, True

                if can_be_cached:
                    cache[id_] = value

            values[parameter.name] = value
            continue

        if parameter.resolve_by_type:
            type_ = normalize_annotation(parameter.annotation)
            try:
                value = scope.resolve_by_type(type_)  # pyright: ignore[reportUnknownVariableType]
            except ScopeResolutionError:
                if parameter.has_default:
                    value = parameter.default
                else:
                    raise

            if isinstance(value, CallableInfo) and CallableInfo not in type_:
                dependency = typing.cast(CallableInfo[typing.Any], value)
                id_, cached, can_be_cached = _cache_status(dependency, cache)

                if cached:
                    value = cache[id_]
                else:
                    value = yield scope, dependency, True

                    if can_be_cached:
                        cache[id_] = value

            values[parameter.name] = value
            continue

        try:
            values[parameter.name] = scope.resolve_by_name(parameter.name)
        except ScopeResolutionError:
            if parameter.has_default:
                values[parameter.name] = parameter.default
            else:
                raise

    yield values, info, False


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
        raise DependencyCycleError(visited)

    visited.add(info.call)

    if cache is None:
        cache = {}

    gen = injection_impl(scope, info, cache)

    value: typing.Any | None = None

    while True:
        inner_scope, inner_info, more = gen.send(value)

        if more and isinstance(inner_scope, Scope):
            value = inject(inner_scope, inner_info, stack, visited.copy())
            continue

        assert isinstance(inner_scope, collections.abc.Mapping)

        return call_sync(stack, inner_info, inner_scope)


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
        raise DependencyCycleError(visited)

    visited.add(info.call)

    if cache is None:
        cache = {}

    gen = injection_impl(scope, info, cache)

    value: typing.Any | None = None

    while True:
        inner_scope, inner_info, more = gen.send(value)

        if more and isinstance(inner_scope, Scope):
            value = await ainject(inner_scope, inner_info, stack, visited.copy())
            continue

        assert isinstance(inner_scope, collections.abc.Mapping)

        if info.async_:
            return await call_async(stack, inner_info, inner_scope)

        return call_sync(stack, inner_info, inner_scope)
