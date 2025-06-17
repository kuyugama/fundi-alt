import typing
import collections.abc

from fundi import CallableInfo
from fundi.types import ParameterResult

from fundi_alt.scope import Scope
from fundi_alt.util import normalize_annotation
from fundi_alt.exceptions import ScopeResolutionError


def resolve(
    scope: Scope, info: CallableInfo[typing.Any], cache: collections.abc.Mapping[int, typing.Any]
) -> collections.abc.Generator[ParameterResult, None, None]:
    for parameter in info.parameters:
        if parameter.from_ is not None:
            info = parameter.from_
            id_ = id(info.call)
            if id_ in cache:
                yield ParameterResult(parameter, cache[id_], info, True)
                continue

            yield ParameterResult(parameter, None, info, False)
            continue

        if parameter.resolve_by_type:
            annotation = normalize_annotation(parameter.annotation)
            try:
                value = scope.resolve_by_type(annotation)
            except ScopeResolutionError:
                if parameter.has_default:
                    yield ParameterResult(parameter, parameter.default, None, True)
                    continue
                raise

            if not isinstance(value, CallableInfo):
                yield ParameterResult(parameter, value, None, True)
                continue

            info = typing.cast(CallableInfo[typing.Any], value)

            if CallableInfo in annotation:
                yield ParameterResult(parameter, info, None, True)
                continue

            id_ = id(info.call)

            if id_ in cache:
                yield ParameterResult(parameter, cache[id_], info, True)
                continue

            yield ParameterResult(parameter, None, info, False)
            continue

        try:
            yield ParameterResult(parameter, scope.resolve_by_name(parameter.name), None, True)
        except ScopeResolutionError:
            if parameter.has_default:
                yield ParameterResult(parameter, parameter.default, None, True)
                continue

            raise
