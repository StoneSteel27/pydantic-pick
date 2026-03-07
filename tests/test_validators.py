import pytest
from pydantic import BaseModel, field_validator, ValidationError
from pydantic_pick import create_subset


class ValidatedModel(BaseModel):
    age: int
    secret_code: str

    @field_validator("age")
    @classmethod
    def check_age(cls, v):
        if v < 18:
            raise ValueError("Must be at least 18")
        return v

    @field_validator("secret_code")
    @classmethod
    def check_code(cls, v):
        if v != "007":
            raise ValueError("Invalid code")
        return v


def test_kept_validator():
    """Ensure validators attached to KEPT fields survive extraction."""
    PublicModel = create_subset(ValidatedModel, ("age",), "PublicModel")

    # Should raise error from the copied validator
    with pytest.raises(ValidationError, match="Must be at least 18"):
        PublicModel(age=15)


def test_dropped_validator():
    """Ensure validators attached to DROPPED fields are safely ignored without crashing."""
    # We drop 'secret_code', meaning its validator should not cause a crash
    PublicModel = create_subset(ValidatedModel, ("age",), "PublicModel")

    # Valid instantiation should work perfectly
    model = PublicModel(age=20)
    assert model.age == 20
