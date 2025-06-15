from dataclasses import dataclass
import typing


@dataclass
class TypeCast:
    """
    Alias for type. Use to make resolver thing `value` has type of `alias`
    """

    alias: type
    value: typing.Any
