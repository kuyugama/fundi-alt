import typing

from fundi.util import callable_str


class ScopeResolutionError(KeyError):
    """Cannot resolve value for provided name or type"""

    def __init__(self, nt: str | type | tuple[type, ...]):
        msg = f"Scope does not contain value for provided name or type {nt!r}"
        super().__init__(msg)
        self.nt: str | type | tuple[type, ...] = nt


class DependencyCycleError(Exception):
    def __init__(
        self,
        visiting: typing.Callable[..., typing.Any],
        visited: set[typing.Callable[..., typing.Any]],
    ) -> None:
        message = (
            f"Dependency cycle found when visiting {callable_str(visiting)}. "
            f"Visited dependencies: {', '.join(callable_str(c) for c in visited)}"
        )

        super().__init__(message)

        self.visited: set[typing.Callable[..., typing.Any]] = visited
