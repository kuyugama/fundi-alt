import types
import typing


def normalize_annotation(annotation: typing.Any) -> tuple[type, ...]:
    type_options: tuple[type, ...] = (annotation,)

    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is typing.Annotated:
        annotation = args[0]
        type_options = (annotation,)
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)

    if origin is types.UnionType:
        type_options = tuple(t for t in args if t is not types.NoneType)
    elif origin is not None:
        type_options = (origin,)

    return type_options
