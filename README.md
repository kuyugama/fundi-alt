# Work In Progress
# _# FunDI Alternative_
This library provides alternative injection scope realisation that can be more convenient for some people

Basic example of what you can do with that:
```python

from contextlib import ExitStack

from fundi_alt import FromType, from_, scan, Scope, inject, TypeCast


class Multiplier(int): ...


class Username(str): ...


app_scope = Scope()


def dependency(multiplier: FromType[Multiplier] = Multiplier(1)):
    print("calculating...")
    return 123 * multiplier


def app(
    username: FromType[Username],
    value: int = from_(dependency),
    _: int = from_(dependency),  # Check if dependency is called twice
):
    print("Got value:", value)

    print("Logged in as", username)


# Or app_scope.resolver(lambda: 2, Multiplier)
@app_scope.resolver
def resolve_multiplier() -> Multiplier:
    return Multiplier(2)


app_scope.value("username", TypeCast(Username, "Kuyugama"))

with ExitStack() as stack:
    inject(app_scope, scan(app), stack)
```


