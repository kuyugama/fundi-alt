import inspect
import typing
import functools

from fundi import from_

T = typing.TypeVar("T")


@typing.overload
def resolver_wrapper(
    dt: type[T],
) -> typing.Callable[[typing.Callable[..., typing.Any]], T]: ...
@typing.overload
def resolver_wrapper(
    dt: typing.Callable[..., typing.Any], type_: type[T]
) -> typing.Callable[..., T]: ...
def resolver_wrapper(
    dt: type[T] | typing.Callable[..., typing.Any], type_: type[T] | None = None
) -> (
    typing.Callable[..., T]
    | typing.Callable[[typing.Callable[..., typing.Any]], typing.Callable[..., T]]
):
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

        def decorator(
            dt: typing.Callable[..., typing.Any],
        ) -> typing.Callable[..., T]:
            return resolver_wrapper(dt, type_)

        return decorator

    @functools.wraps(
        dt,
        assigned=(
            "__module__",
            "__name__",
            "__qualname__",
            "__doc__",
            "__annotations__",
            "__fundi_configuration__",
        ),
    )
    def dependency(result: typing.Any) -> T:
        return result

    dependency.__annotations__["return"] = type_

    signature = inspect.signature(dt).replace(
        parameters=[
            inspect.Parameter("result", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=from_(dt))
        ],
        return_annotation=type_,
    )

    dependency.__signature__ = signature  # pyright: ignore[reportAttributeAccessIssue]

    return dependency
