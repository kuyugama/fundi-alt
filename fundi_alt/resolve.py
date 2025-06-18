import typing
import collections.abc

from fundi import normalize_annotation
from fundi.types import ParameterResult
from fundi import CallableInfo, Parameter

from fundi_alt.scope import Scope
from fundi_alt.exceptions import ScopeResolutionError


def resolve_by_info(
    info: CallableInfo[typing.Any],
    parameter: Parameter,
    cache: collections.abc.Mapping[int, typing.Any],
    override: collections.abc.Mapping[typing.Callable[..., typing.Any], CallableInfo[typing.Any]],
) -> ParameterResult:
    if info.call in override:
        info = override[info.call]

    id_ = id(info.call)
    if id_ in cache:
        return ParameterResult(parameter, cache[id_], info, True)

    return ParameterResult(parameter, None, info, False)


def resolve_by_type(
    scope: Scope,
    parameter: Parameter,
    cache: collections.abc.Mapping[int, typing.Any],
    override: collections.abc.Mapping[typing.Callable[..., typing.Any], CallableInfo[typing.Any]],
) -> ParameterResult:
    annotation = normalize_annotation(parameter.annotation)
    try:
        value = scope.resolve_by_type(annotation)
    except ScopeResolutionError:
        if parameter.has_default:
            return ParameterResult(parameter, parameter.default, None, True)
        raise

    if not isinstance(value, CallableInfo):
        return ParameterResult(parameter, value, None, True)

    info = typing.cast(CallableInfo[typing.Any], value)

    if CallableInfo in annotation:
        return ParameterResult(parameter, info, None, True)

    return resolve_by_info(info, parameter, cache, override)


def resolve(
    scope: Scope,
    info: CallableInfo[typing.Any],
    cache: collections.abc.Mapping[int, typing.Any],
    override: collections.abc.Mapping[typing.Callable[..., typing.Any], CallableInfo[typing.Any]],
) -> collections.abc.Generator[ParameterResult, None, None]:
    for parameter in info.parameters:
        if parameter.from_ is not None:
            yield resolve_by_info(parameter.from_, parameter, cache, override)
            continue

        if parameter.resolve_by_type:
            yield resolve_by_type(scope, parameter, cache, override)
            continue

        try:
            yield ParameterResult(parameter, scope.resolve_by_name(parameter.name), None, True)
        except ScopeResolutionError:
            if parameter.has_default:
                yield ParameterResult(parameter, parameter.default, None, True)
                continue

            raise
