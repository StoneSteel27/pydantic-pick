import inspect
import functools
from typing import Any, ClassVar, Type
from pydantic import BaseModel, create_model, field_validator, computed_field

from .utils import build_include_dict
from .unwrapper import unwrap_and_rebuild_type


def _extract_dto(base: Type[BaseModel], include: dict[str, Any], new_name: str) -> Type[BaseModel]:
    new_fields = {}

    # 1. Extract Fields & Rebuild Types
    for field_name, field_info in base.model_fields.items():
        if field_name not in include:
            continue

        inc_val = include[field_name]
        annotation = field_info.annotation

        if isinstance(inc_val, dict):
            # Pass _extract_dto itself into the unwrapper to handle infinite recursion depth securely
            new_type = unwrap_and_rebuild_type(
                annotation, inc_val, f"{new_name}_{field_name}", _extract_dto
            )
            new_fields[field_name] = (new_type, field_info)
        else:
            new_fields[field_name] = (annotation, field_info)

    # 2. Extract Class-Level Validators (@field_validator)
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

    # A. Rebuild @computed_field properties safely
    for comp_name, comp_info in getattr(base, 'model_computed_fields', {}).items():
        # Get the wrapped property from the class dict
        raw_property = base.__dict__[comp_name]

        # In Pydantic V2, it's often a PydanticDescriptorProxy. We need the actual underlying function/property
        actual_property = getattr(raw_property, 'wrapped', raw_property)

        # Re-apply the computed_field decorator to force Pydantic to register it on the new model
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

        # isroutine covers built-in functions, user functions, and bound methods.
        # callable catches custom class-based decorators (objects with __call__).
        # property/classmethod/staticmethod catch standard descriptors.
        if (
                inspect.isroutine(attr_val)
                or callable(attr_val)
                or isinstance(attr_val, (property, classmethod, staticmethod))
        ):
            custom_namespace[attr_name] = attr_val

    MethodMixin = type(f"{new_name}Mixin", (object,), custom_namespace)
    # -------------------------------------------------------------

    MethodMixin = type(f"{new_name}Mixin", (object,), custom_namespace)

    # 4. Create Model inheriting from both the Methods Mixin and BaseModel
    NewModel = create_model(
        new_name,
        __base__=(MethodMixin, BaseModel),
        __config__=getattr(base, "model_config", {}),
        __validators__=new_validators,
        **new_fields
    )

    # 5. ClassVars
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
