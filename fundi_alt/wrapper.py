import typing
import inspect
import functools

from fundi import from_

T = typing.TypeVar("T")

Returns = typing.Callable[..., T]
Decorator = typing.Callable[[Returns[T]], Returns[T]]


@typing.overload
def resolver_wrapper(
    dt: type[T],
) -> Decorator[T]: ...
@typing.overload
def resolver_wrapper(dt: Returns[typing.Any], type_: type[T]) -> Returns[T]: ...
def resolver_wrapper(
    dt: type[T] | Returns[T], type_: type[T] | None = None
) -> Returns[T] | Decorator[T]:
    """
    Little hack to deceive `fundi.scan.scan` into thinking
    that dependency actually returns other type.

    Very useful for context related resolvers.

    For example, to distinguish actor from his "victim"::

        class Actor(User):
            ...


        class Victim(User):
            ...


        scope.resolver(resolver_wrapper(require_user(resolver=resolvers.token_user), Actor))
        scope.resolver(resolver_wrapper(require_user(resolver=resolvers.body_user), Victim))
    """
    if type_ is None and isinstance(dt, type):
        type_ = dt
        return typing.cast(
            Decorator[T],
            functools.partial(resolver_wrapper, type_=dt),
        )

    @functools.wraps(dt, assigned=("__fundi_configuration__",), updated=())
    def dependency(result: typing.Any) -> T:
        return result

    signature = inspect.signature(dt).replace(
        parameters=[
            inspect.Parameter("result", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=from_(dt))
        ],
        return_annotation=type_,
    )
    setattr(dependency, "__signature__", signature)

    return dependency
