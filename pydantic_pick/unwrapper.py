import types
import typing
from typing import Any, List, Set, Tuple, Dict, Union, Callable, get_origin, get_args
from pydantic import BaseModel


def unwrap_and_rebuild_type(
        annotation: Any,
        inc_val: dict[str, Any],
        new_name: str,
        extract_fn: Callable
) -> Any:
    """
    Recursively traverses complex generic types from both the standard library
    and typing_extensions to find and rebuild inner Pydantic BaseModels.
    """
    # Base Case: Direct BaseModel
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        # We call the dynamically passed core extractor function here
        return extract_fn(annotation, inc_val, new_name)

    origin = get_origin(annotation)
    if origin is None:
        return annotation  # Primitives, Enums, Literals, Any

    args = get_args(annotation)
    if not args:
        return annotation

    # 1. Lists
    if origin is list or origin is List:
        new_inner = unwrap_and_rebuild_type(args[0], inc_val, new_name, extract_fn)
        return list[new_inner]

    # 2. Sets
    if origin is set or origin is Set:
        new_inner = unwrap_and_rebuild_type(args[0], inc_val, new_name, extract_fn)
        return set[new_inner]

    # 3. Tuples
    if origin is tuple or origin is Tuple:
        new_args = tuple(unwrap_and_rebuild_type(arg, inc_val, new_name, extract_fn) for arg in args)
        return tuple[new_args]

    # 4. Dictionaries
    if origin is dict or origin is Dict:
        key_type = args[0]
        val_type = unwrap_and_rebuild_type(args[1], inc_val, new_name, extract_fn)
        return dict[key_type, val_type]

    # 5. Unions and Optionals
    if origin is Union or origin is types.UnionType:
        new_args = tuple(unwrap_and_rebuild_type(arg, inc_val, new_name, extract_fn) for arg in args)
        return Union[new_args]

    # 6. Annotated
    if origin is getattr(typing, 'Annotated', None) or str(origin) == "typing.Annotated":
        base_type = unwrap_and_rebuild_type(args[0], inc_val, new_name, extract_fn)
        metadata = args[1:]
        return typing.Annotated[(base_type,) + metadata]

    return annotation
