import ast
import inspect
import textwrap
import types
import typing
import functools
from typing import Any, ClassVar, List, Set, Tuple, Dict, Type, Union, get_args, get_origin
from pydantic import BaseModel, create_model, field_validator, computed_field

from .utils import build_include_dict


def _unwrap_and_rebuild_type(annotation: Any, inc_val: dict[str, Any], new_name: str) -> Any:
    """
    Recursively traverses complex generic types from both the standard library
    and typing_extensions to find and rebuild inner Pydantic BaseModels.
    """
    # Base Case: Direct BaseModel
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _extract_dto(annotation, inc_val, new_name)

    origin = get_origin(annotation)
    if origin is None:
        return annotation  # Primitives, Enums, Literals, Any

    args = get_args(annotation)
    if not args:
        return annotation

    # 1. Lists
    if origin is list or origin is List:
        new_inner = _unwrap_and_rebuild_type(args[0], inc_val, new_name)
        return list[new_inner]

    # 2. Sets
    if origin is set or origin is Set:
        new_inner = _unwrap_and_rebuild_type(args[0], inc_val, new_name)
        return set[new_inner]

    # 3. Tuples (Can have multiple distinct types: tuple[int, str, Model])
    if origin is tuple or origin is Tuple:
        new_args = tuple(_unwrap_and_rebuild_type(arg, inc_val, new_name) for arg in args)
        return tuple[new_args]

    # 4. Dictionaries (e.g., dict[str, NestedModel])
    if origin is dict or origin is Dict:
        key_type = args[0]  # Keys are usually primitives
        val_type = _unwrap_and_rebuild_type(args[1], inc_val, new_name)
        return dict[key_type, val_type]

    # 5. Unions and Optionals (including PEP 604 A | B syntax)
    if origin is Union or origin is types.UnionType:
        new_args = tuple(_unwrap_and_rebuild_type(arg, inc_val, new_name) for arg in args)
        return Union[new_args]

    # 6. Annotated (Extremely important for Pydantic V2)
    if origin is getattr(typing, 'Annotated', None) or str(origin) == "typing.Annotated":
        base_type = _unwrap_and_rebuild_type(args[0], inc_val, new_name)
        metadata = args[1:]
        return typing.Annotated[(base_type,) + metadata]

    # Fallback for completely unknown generic types
    return annotation


# --- AST Validation Tools ---

def _get_accessed_self_attributes(func) -> set[str]:
    """
    Parses the AST of a function to find all attributes accessed via 'self'.
    Automatically tunnels through function wrappers and class-based decorators.
    """
    # Hard unwrap layers of custom decorators and class-based wrappers
    while True:
        if hasattr(func, '__wrapped__'):
            func = func.__wrapped__  # Standard functools.wraps
        elif hasattr(func, 'func'):
            func = func.func  # Common in class-decorators and functools.partial
        elif hasattr(func, 'fget'):
            func = func.fget  # Properties and custom descriptors
        elif isinstance(func, property):
            func = func.fget
        else:
            break

    try:
        source = textwrap.dedent(inspect.getsource(func))
        tree = ast.parse(source)
    except (TypeError, OSError, IndentationError, Exception):
        return set()

    accessed = set()

    class AttributeVisitor(ast.NodeVisitor):
        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == 'self':
                accessed.add(node.attr)
            self.generic_visit(node)

    AttributeVisitor().visit(tree)
    return accessed


def _validate_method_dependencies(func, base: Type[BaseModel], new_fields: dict) -> list[str]:
    """
    Returns a list of missing field names that this function relies on.
    """
    accessed_fields = _get_accessed_self_attributes(func)
    missing_fields = [
        f for f in accessed_fields
        if f not in new_fields and f in base.model_fields
    ]
    return missing_fields


def make_getattr(omitted_set):
    """
    Generates a dynamic __getattr__ method to provide developer-friendly errors
    when omitted methods or fields are accessed.
    """

    def custom_getattr(self, name):
        if name in omitted_set:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'.\n"
                f"-> This field/method was intentionally omitted by pydantic-pick during extraction."
            )
        # Standard Python fallback
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    return custom_getattr


# --- Core Logic ---

def _extract_dto(base: Type[BaseModel], include: dict[str, Any], new_name: str) -> Type[BaseModel]:
    new_fields = {}

    # 1. Extract Fields & Rebuild Types
    for field_name, field_info in base.model_fields.items():
        if field_name not in include:
            continue

        inc_val = include[field_name]
        annotation = field_info.annotation

        if isinstance(inc_val, dict):
            new_type = _unwrap_and_rebuild_type(annotation, inc_val, f"{new_name}_{field_name}")
            new_fields[field_name] = (new_type, field_info)
        else:
            new_fields[field_name] = (annotation, field_info)

    # 2. Extract Class-Level Validators
    new_validators = {}
    if hasattr(base, '__pydantic_decorators__'):
        for val_name, decorator in getattr(base.__pydantic_decorators__, 'field_validators', {}).items():
            target_fields = getattr(decorator.info, 'fields', tuple())
            kept_fields = [f for f in target_fields if f in new_fields]
            if kept_fields:
                original_func = decorator.func.__func__ if hasattr(decorator.func, '__func__') else decorator.func
                new_validators[val_name] = field_validator(*kept_fields)(original_func)

    # -------------------------------------------------------------
    # 3. Extract User-Defined Methods, Properties, and @computed_field
    # -------------------------------------------------------------
    custom_namespace = {}
    omitted_attributes = set()

    # Track purely omitted data fields first
    for field_name in base.model_fields.keys():
        if field_name not in new_fields:
            omitted_attributes.add(field_name)

    # A. Rebuild @computed_field properties safely
    for comp_name, comp_info in getattr(base, 'model_computed_fields', {}).items():
        raw_property = base.__dict__[comp_name]
        actual_property = getattr(raw_property, 'wrapped', raw_property)

        # Validation: If missing fields, omit the computed field entirely
        if isinstance(actual_property, property) and actual_property.fget:
            if _validate_method_dependencies(actual_property.fget, base, new_fields):
                omitted_attributes.add(comp_name)
                continue

        custom_namespace[comp_name] = computed_field(
            alias=comp_info.alias,
            title=comp_info.title,
            description=comp_info.description,
            repr=comp_info.repr
        )(actual_property)

    # B. Extract standard methods and CUSTOM WRAPPERS safely
    for attr_name, attr_val in vars(base).items():
        if attr_name.startswith('__') and attr_name.endswith('__'):
            continue
        if attr_name.startswith('model_') or attr_name in ('Config', '_abc_impl'):
            continue
        if attr_name in custom_namespace:
            continue

        if (
                inspect.isroutine(attr_val)
                or callable(attr_val)
                or isinstance(attr_val, (property, classmethod, staticmethod))
        ):
            # Validation: Validate ALL callables (functions AND class-wrappers)
            if _validate_method_dependencies(attr_val, base, new_fields):
                omitted_attributes.add(attr_name)
                continue

            custom_namespace[attr_name] = attr_val

    # Inject custom error handler into the mixin
    custom_namespace['__getattr__'] = make_getattr(omitted_attributes)

    MethodMixin = type(f"{new_name}Mixin", (object,), custom_namespace)
    # -------------------------------------------------------------

    # 4. Create Model inherited from both the Mixin and BaseModel
    NewModel = create_model(
        new_name,
        __base__=(MethodMixin, BaseModel),
        __config__=getattr(base, "model_config", {}),
        __validators__=new_validators,
        **new_fields
    )

    # 5. Restore ClassVars
    if not hasattr(NewModel, '__annotations__'):
        NewModel.__annotations__ = {}

    for cvar_name in getattr(base, '__class_vars__', set()):
        cvar_value = getattr(base, cvar_name)
        setattr(NewModel, cvar_name, cvar_value)
        NewModel.__annotations__[cvar_name] = ClassVar[type(cvar_value)]

    return NewModel


@functools.lru_cache(maxsize=128)
def create_subset(base: Type[BaseModel], paths: tuple[str, ...], new_name: str) -> Type[BaseModel]:
    """
    Dynamically creates a subset of a Pydantic BaseModel based on a list of dot-notation paths.
    Results are cached via LRU cache to ensure high performance in API endpoints.
    """
    include_map = build_include_dict(list(paths))
    return _extract_dto(base, include_map, new_name)
