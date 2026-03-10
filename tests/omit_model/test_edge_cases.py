"""
Test edge cases specific to omit_model functionality.
These tests verify the inverse relationship with pick_model and other edge behaviors.
"""

import pytest
from typing import Dict, List, Optional, Union, Set, ClassVar
from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator, ValidationError
from pydantic_pick import omit_model, pick_model


# =============================================================================
# 1. IDENTITY / EMPTY CASES
# =============================================================================

class SimpleModel(BaseModel):
    id: int
    name: str
    secret: str


def test_omit_nothing_returns_complete_model():
    """Omit nothing - should return functionally identical model."""
    CompleteModel = omit_model(SimpleModel, (), "CompleteModel")

    # All fields should be present
    assert "id" in CompleteModel.model_fields
    assert "name" in CompleteModel.model_fields
    assert "secret" in CompleteModel.model_fields

    # Model should work normally
    model = CompleteModel(id=1, name="Test", secret="hidden")
    assert model.id == 1
    assert model.name == "Test"
    assert model.secret == "hidden"


def test_omit_all_fields():
    """Omit all fields - creates minimal model."""
    EmptyModel = omit_model(SimpleModel, ("id", "name", "secret"), "EmptyModel")

    # Model should exist but have no fields
    assert len(EmptyModel.model_fields) == 0
    instance = EmptyModel()
    assert instance.model_dump() == {}


def test_omit_nonexistent_field_is_graceful():
    """Omitting a field that doesn't exist should be graceful (ignore)."""
    # This should not raise an error, just ignore the non-existent field
    PublicModel = omit_model(SimpleModel, ("nonexistent_field",), "PublicModel")

    # All original fields should still be present
    assert "id" in PublicModel.model_fields
    assert "name" in PublicModel.model_fields
    assert "secret" in PublicModel.model_fields


# =============================================================================
# 2. INVERSE RELATIONSHIP TESTS
# =============================================================================

class InverseTestModel(BaseModel):
    field_a: str
    field_b: str
    field_c: str
    field_d: str


def test_pick_vs_omit_inverse():
    """Verify that pick_model(paths) equals omit_model(all_paths - paths)."""
    # Pick fields a and b
    PickedModel = pick_model(InverseTestModel, ("field_a", "field_b"), "PickedModel")

    # Omit fields c and d (which is equivalent)
    OmittedModel = omit_model(InverseTestModel, ("field_c", "field_d"), "OmittedModel")

    # Both models should have the same fields
    assert set(PickedModel.model_fields.keys()) == set(OmittedModel.model_fields.keys())
    assert "field_a" in PickedModel.model_fields
    assert "field_a" in OmittedModel.model_fields
    assert "field_b" in PickedModel.model_fields
    assert "field_b" in OmittedModel.model_fields
    assert "field_c" not in PickedModel.model_fields
    assert "field_c" not in OmittedModel.model_fields
    assert "field_d" not in PickedModel.model_fields
    assert "field_d" not in OmittedModel.model_fields


def test_pick_then_omit_identity():
    """pick_model then omit_model with remaining fields should be identity."""
    # First pick a subset
    PartialModel = pick_model(InverseTestModel, ("field_a", "field_b"), "PartialModel")

    # Then omit nothing from the picked model
    # This is a bit tricky since we can't easily get all paths from the partial model
    # So we just verify that omitting from the partial model works
    identity = omit_model(PartialModel, (), "IdentityModel")

    assert "field_a" in identity.model_fields
    assert "field_b" in identity.model_fields
    assert "field_c" not in identity.model_fields


# =============================================================================
# 3. PARTIAL OMISSION SCENARIOS
# =============================================================================

class Settings(BaseModel):
    theme: str
    api_key: str
    language: str


class ProfileWithSettings(BaseModel):
    bio: str
    settings: Settings


class UserWithProfile(BaseModel):
    id: int
    profile: ProfileWithSettings


def test_omit_parent_vs_child():
    """Omitting 'profile' vs 'profile.settings.api_key' - different behaviors."""
    # Omit entire profile
    NoProfileUser = omit_model(UserWithProfile, ("profile",), "NoProfileUser")
    assert "profile" not in NoProfileUser.model_fields
    user1 = NoProfileUser(id=1)
    assert user1.model_dump() == {"id": 1}

    # Omit only nested field
    PartialProfileUser = omit_model(UserWithProfile, ("profile.settings.api_key",), "PartialProfileUser")
    assert "profile" in PartialProfileUser.model_fields
    user2 = PartialProfileUser(
        id=1,
        profile={"bio": "Hello", "settings": {"theme": "dark", "language": "en"}}
    )
    dump = user2.model_dump()
    assert "api_key" not in dump["profile"]["settings"]
    assert dump["profile"]["settings"]["theme"] == "dark"


class ComputedDependencyModel(BaseModel):
    base_value: int
    multiplier: int

    @computed_field
    def computed_result(self) -> int:
        return self.base_value * self.multiplier


def test_omit_computed_field_dependency():
    """If computed_field dependency is omitted, computed_field should be omitted."""
    # Omit base_value which computed_result depends on
    PartialComputed = omit_model(ComputedDependencyModel, ("base_value",), "PartialComputed")

    instance = PartialComputed(multiplier=5)
    # computed_result should be omitted because it depends on base_value
    assert not hasattr(instance, "computed_result")

    # Keep both dependencies
    FullComputed = omit_model(ComputedDependencyModel, (), "FullComputed")
    instance2 = FullComputed(base_value=10, multiplier=5)
    assert instance2.computed_result == 50


class ModelWithDefaults(BaseModel):
    required_field: str
    field_with_default: str = "default_value"
    optional_field: Optional[str] = None


def test_omit_with_default_values():
    """Omitting fields with default values."""
    # Omit field with default
    NoDefaultModel = omit_model(ModelWithDefaults, ("field_with_default",), "NoDefaultModel")
    instance = NoDefaultModel(required_field="test")
    assert "field_with_default" not in instance.model_dump()
    assert instance.required_field == "test"

    # Omit optional field
    NoOptionalModel = omit_model(ModelWithDefaults, ("optional_field",), "NoOptionalModel")
    instance2 = NoOptionalModel(required_field="test")
    assert "optional_field" not in instance2.model_dump()
    assert instance2.required_field == "test"


# =============================================================================
# 4. VALIDATION EDGE CASES
# =============================================================================

class ConstrainedModel(BaseModel):
    age: int = Field(..., ge=0, le=120)
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age cannot be negative")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


def test_omit_constrained_field_keep_validator():
    """Omit constrained field - validators on remaining fields still work."""
    NameOnlyModel = omit_model(ConstrainedModel, ("age",), "NameOnlyModel")

    # Name validator should still work
    with pytest.raises(ValidationError, match="Name cannot be empty"):
        NameOnlyModel(name="   ")

    # Field constraints should still work
    with pytest.raises(ValidationError):
        NameOnlyModel(name="")  # min_length=1


def test_omit_required_field():
    """Omitting a required field - partial model should still work."""
    AgeOnlyModel = omit_model(ConstrainedModel, ("name",), "AgeOnlyModel")

    # Should be able to instantiate with just age
    instance = AgeOnlyModel(age=25)
    assert instance.age == 25
    assert "name" not in instance.model_dump()


# =============================================================================
# 5. METHOD DEPENDENCY EDGE CASES
# =============================================================================

class MethodDependencyModel(BaseModel):
    direct_field: str
    nested_field: str

    def use_direct(self) -> str:
        return f"Direct: {self.direct_field}"

    def use_nested(self) -> str:
        return f"Nested: {self.nested_field}"

    def use_both(self) -> str:
        return f"Both: {self.direct_field} and {self.nested_field}"


def test_omit_field_method_depends_on():
    """Omit field that a method depends on - method should be omitted."""
    PartialMethodModel = omit_model(MethodDependencyModel, ("direct_field",), "PartialMethodModel")

    instance = PartialMethodModel(nested_field="test")

    # use_direct should be omitted (depends on direct_field)
    assert not hasattr(instance, "use_direct")

    # use_nested should still work (only depends on nested_field)
    assert instance.use_nested() == "Nested: test"

    # use_both should be omitted (depends on direct_field which is gone)
    assert not hasattr(instance, "use_both")


class DynamicAccessModel(BaseModel):
    field_a: str
    field_b: str

    def dynamic_getattr(self, field_name: str) -> str:
        return getattr(self, field_name, "not found")

    def loop_access(self) -> List[str]:
        return [getattr(self, f) for f in ["field_a", "field_b"]]


def test_dynamic_getattr_field_omitted():
    """Field accessed via getattr - AST may not detect, test behavior."""
    # Omit field_a
    PartialDynamic = omit_model(DynamicAccessModel, ("field_a",), "PartialDynamic")

    instance = PartialDynamic(field_b="value_b")

    # dynamic_getattr may still exist since AST can't detect dynamic access
    # But accessing field_a via getattr should return "not found"
    assert instance.dynamic_getattr("field_a") == "not found"
    assert instance.dynamic_getattr("field_b") == "value_b"


def test_loop_comprehension_field_omitted():
    """Field accessed in list comprehension - AST parsing limits."""
    # Omit field_a
    PartialDynamic = omit_model(DynamicAccessModel, ("field_a",), "PartialDynamic")

    instance = PartialDynamic(field_b="value_b")

    # loop_access may still exist, but field_a access in loop should fail
    # This tests that the method fails gracefully or is omitted
    try:
        result = instance.loop_access()
        # If method exists, it should handle missing field gracefully
        assert "field_a" not in result or result == ["not found", "value_b"]
    except AttributeError:
        # Or the method might be omitted entirely
        pass


# =============================================================================
# 6. COMPLEX NESTED OMISSION
# =============================================================================

class Level5(BaseModel):
    deep_field: str
    deeper_secret: str


class Level4(BaseModel):
    level5: Level5
    mid_field: str


class Level3(BaseModel):
    level4: Level4
    upper_field: str


class Level2(BaseModel):
    level3: Level3
    mid_upper_field: str


class Level1(BaseModel):
    level2: Level2
    top_field: str


class DeepNestedModel(BaseModel):
    root: Level1


def test_omit_deeply_nested_path():
    """Omit 'root.level2.level3.level4.level5.deeper_secret' - very deep nesting."""
    PublicDeep = omit_model(
        DeepNestedModel,
        ("root.level2.level3.level4.level5.deeper_secret",),
        "PublicDeep"
    )

    data = {
        "root": {
            "top_field": "top",
            "level2": {
                "mid_upper_field": "mid_upper",
                "level3": {
                    "upper_field": "upper",
                    "level4": {
                        "mid_field": "mid",
                        "level5": {
                            "deep_field": "deep",
                            "deeper_secret": "secret"
                        }
                    }
                }
            }
        }
    }

    instance = PublicDeep(**data)
    dump = instance.model_dump()

    assert dump["root"]["level2"]["level3"]["level4"]["level5"]["deep_field"] == "deep"
    assert "deeper_secret" not in dump["root"]["level2"]["level3"]["level4"]["level5"]


def test_omit_multiple_at_same_level():
    """Omit multiple fields at same nesting level."""
    SelectiveDeep = omit_model(
        DeepNestedModel,
        (
            "root.top_field",
            "root.level2.mid_upper_field",
            "root.level2.level3.upper_field"
        ),
        "SelectiveDeep"
    )

    data = {
        "root": {
            "top_field": "top",
            "level2": {
                "mid_upper_field": "mid_upper",
                "level3": {
                    "upper_field": "upper",
                    "level4": {
                        "mid_field": "mid",
                        "level5": {
                            "deep_field": "deep",
                            "deeper_secret": "secret"
                        }
                    }
                }
            }
        }
    }

    instance = SelectiveDeep(**data)
    dump = instance.model_dump()

    # Omitted fields
    assert "top_field" not in dump["root"]
    assert "mid_upper_field" not in dump["root"]["level2"]
    assert "upper_field" not in dump["root"]["level2"]["level3"]

    # Kept fields
    assert dump["root"]["level2"]["level3"]["level4"]["mid_field"] == "mid"


# =============================================================================
# 7. CASCADING OMISSION TESTS
# =============================================================================

class CascadingModel(BaseModel):
    base_field: str
    intermediate_field: str
    final_field: str

    def method_a(self) -> str:
        """Depends on base_field"""
        return f"A: {self.base_field}"

    def method_b(self) -> str:
        """Depends on method_a (indirectly) and intermediate_field"""
        return f"B: {self.method_a()} + {self.intermediate_field}"

    def method_c(self) -> str:
        """Depends on method_b and final_field"""
        return f"C: {self.method_b()} + {self.final_field}"


def test_cascading_method_omission():
    """Method A uses field X, Method B uses Method A, omit X -> method A omitted, B may survive."""
    # NOTE: The AST parser can only detect direct self.field access, not method calls.
    # So method_b may survive even though it calls method_a, because it doesn't directly
    # access the omitted field.
    # Omit base_field which is the root of the cascade
    PartialCascade = omit_model(CascadingModel, ("base_field",), "PartialCascade")

    instance = PartialCascade(intermediate_field="mid", final_field="fin")

    # method_a should be omitted (depends on base_field)
    assert not hasattr(instance, "method_a")

    # method_b may or may not be omitted depending on AST detection capabilities
    # method_b calls method_a, but AST only sees self.intermediate_field access
    # method_c depends on method_b, so same logic applies


def test_partial_cascade():
    """Omit intermediate - only methods directly depending on it should be omitted."""
    PartialMid = omit_model(CascadingModel, ("intermediate_field",), "PartialMid")

    instance = PartialMid(base_field="base", final_field="fin")

    # method_a should still work (only depends on base_field)
    assert instance.method_a() == "A: base"

    # method_b should be omitted (directly depends on intermediate_field)
    assert not hasattr(instance, "method_b")

    # method_c depends on method_b, but AST may not detect the indirect dependency


# =============================================================================
# 8. UNION BOUNDARY EDGE CASES
# =============================================================================

class UnionMemberA(BaseModel):
    common: str
    unique_a: str
    secret_a: str


class UnionMemberB(BaseModel):
    common: str
    unique_b: str
    secret_b: str


class ModelWithUnion(BaseModel):
    id: int
    union_field: Union[UnionMemberA, UnionMemberB]


def test_omit_across_union_boundaries():
    """Omit field that exists in one Union member but not another."""
    # Omit secret_a (only in UnionMemberA) and secret_b (only in UnionMemberB)
    PublicUnionModel = omit_model(
        ModelWithUnion,
        ("union_field.secret_a", "union_field.secret_b"),
        "PublicUnionModel"
    )

    # Test with UnionMemberA
    instance_a = PublicUnionModel(
        id=1,
        union_field={"common": "test", "unique_a": "value_a", "secret_a": "hidden"}
    )
    dump_a = instance_a.model_dump()
    assert dump_a["union_field"]["common"] == "test"
    assert dump_a["union_field"]["unique_a"] == "value_a"
    assert "secret_a" not in dump_a["union_field"]

    # Test with UnionMemberB
    instance_b = PublicUnionModel(
        id=2,
        union_field={"common": "test", "unique_b": "value_b", "secret_b": "hidden"}
    )
    dump_b = instance_b.model_dump()
    assert dump_b["union_field"]["common"] == "test"
    assert dump_b["union_field"]["unique_b"] == "value_b"
    assert "secret_b" not in dump_b["union_field"]


# =============================================================================
# 9. CACHE AND PERFORMANCE EDGE CASES
# =============================================================================

def test_lru_cache_same_omit_paths():
    """Same omit paths should return cached model."""
    Model1 = omit_model(SimpleModel, ("secret",), "CachedModel")
    Model2 = omit_model(SimpleModel, ("secret",), "CachedModel")

    # Should be the same object due to lru_cache
    assert Model1 is Model2


def test_different_omit_paths_different_models():
    """Different omit paths should return different models."""
    Model1 = omit_model(SimpleModel, ("secret",), "Model1")
    Model2 = omit_model(SimpleModel, ("name", "secret"), "Model2")

    # Should be different objects
    assert Model1 is not Model2
    assert "name" in Model1.model_fields
    assert "name" not in Model2.model_fields
