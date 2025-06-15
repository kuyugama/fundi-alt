import typing
import collections.abc

from fundi import CallableInfo, scan

from fundi_alt.types import TypeCast
from fundi_alt.util import normalize_annotation
from fundi_alt.exceptions import ScopeResolutionError

T = typing.TypeVar("T")
C = typing.TypeVar("C", bound=typing.Callable[..., typing.Any])


class Scope:
    """
    Dependency injection scope. This is alternative realisation
    of FunDIs original scope functionality based on raw Mappings

    It provides simple interface to specify scope values.

    Also, it introduces new object type - resolver. Resolver is the same
    dependency as others, only difference - it is defined in one place and
    reused all over the code automatically, without manually pointing to it.

    Example::

        from contextlib import ExitStack

        from fundi_alt import Scope, scan, inject

        scope = Scope({"name": "value"})


        @scope.resolver
        def require_user() -> User:
            ...


        def application(name: str, user: User):
            ...


        with ExitStack as stack:
            inject(scope, scan(application), stack)
    """

    def __init__(
        self,
        values: collections.abc.Mapping[str, typing.Any] | None = None,
        resolvers: (
            collections.abc.Sequence[typing.Callable[..., typing.Any] | CallableInfo[typing.Any]]
            | None
        ) = None,
        parent: "Scope | None" = None,
    ) -> None:
        super().__init__()
        self._parent: Scope | None = parent

        if values is None:
            values = {}

        if resolvers is None:
            resolvers = []

        self._keyed: dict[str, typing.Any] = {**values}
        self._resolvers: dict[tuple[type, ...], CallableInfo[typing.Any]] = {}

        for resolver in resolvers:
            if isinstance(resolver, CallableInfo):
                annotation = normalize_annotation(resolver.return_annotation)
                self._resolvers[annotation] = resolver
            else:
                info = scan(resolver)
                annotation = normalize_annotation(info.return_annotation)
                self._resolvers[annotation] = info

    def child(self) -> "Scope":
        return Scope(parent=self)

    def resolver(self, resolver: C, resolves_to: typing.Any = ...) -> C:
        info = scan(resolver)
        if resolves_to is ...:
            resolves_to = info.return_annotation

        annotation = normalize_annotation(resolves_to)

        self._resolvers[annotation] = info

        return resolver

    def value(self, name: str, value: typing.Any) -> None:
        self._keyed[name] = value

    def resolve_by_type(self, type_: type[T] | tuple[type[T], ...]) -> T | CallableInfo[T]:
        if not isinstance(type_, tuple):
            type_ = (type_,)

        for value in self._keyed.values():
            if isinstance(value, TypeCast) and value.alias in type_:
                return value.value

            if isinstance(value, type_):
                return typing.cast(T, value)

        for resolves_to, resolver in self._resolvers.items():
            if any(t in resolves_to for t in type_):
                return resolver

        if self._parent is not None:
            return self._parent.resolve_by_type(type_)

        raise ScopeResolutionError(type_)

    def resolve_by_name(self, name: str) -> typing.Any:
        try:
            value = self._keyed[name]
        except KeyError as exc:
            if self._parent is not None:
                try:
                    value = self._parent.resolve_by_name(name)
                except ScopeResolutionError:
                    pass
            raise ScopeResolutionError(name) from exc

        if isinstance(value, TypeCast):
            return value.value

        return value
