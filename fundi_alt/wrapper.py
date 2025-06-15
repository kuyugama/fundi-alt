import inspect
import typing
import functools

from fundi import from_

T = typing.TypeVar("T")
Self = typing.TypeVar("Self")

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


class ObjectWrapper(typing.Generic[T]):
    """
    Wrapper for objects, useful when need distinguish two instances of the same class by their type

    Usage::
        class SubjectUser(User, ObjectWrapper[User]): ...

        class ObjectUser(User, ObjectWrapper[User]): ...

        subject = SubjectUser.by(user)

        object = ObjectUser.by(user)

        if isinstance(subject, SubjectUser):
            print("This is a subject user")
        if isinstance(object, ObjectUser):
            print("subject user appears to be object user")

        if isinstance(object, ObjectUser):
            print("This is a object user")
        if isinstance(object, SubjectUser):
            print("object user appears to be subject user")
    """

    def __init_subclass__(cls) -> None:
        for base in type.mro(cls):
            if base is not object and base.__module__ == "builtins":
                raise ValueError("Cannot wrap builtin type")

        return super().__init_subclass__()

    @classmethod
    def by(cls: type[Self], object_: T) -> Self:
        instance = cls.__new__(cls)

        if hasattr(object_, "__getstate__"):
            state = getattr(object_, "__getstate__")()
        else:
            state = object_.__dict__

        if hasattr(instance, "__setstate__"):
            getattr(instance, "__setstate__")(state)
        else:
            instance.__dict__.update(state)

        return instance
