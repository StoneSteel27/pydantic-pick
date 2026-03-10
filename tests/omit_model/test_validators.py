import pytest
from pydantic import BaseModel, field_validator, ValidationError
from pydantic_pick import omit_model


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


def test_remaining_fields_keep_validators():
    """Ensure validators attached to remaining fields survive omission."""
    # Omit secret_code, keep age
    PublicModel = omit_model(ValidatedModel, ("secret_code",), "PublicModel")

    # Should raise error from the kept validator
    with pytest.raises(ValidationError, match="Must be at least 18"):
        PublicModel(age=15)


def test_omitted_field_validator_ignored():
    """Ensure validators attached to omitted fields are safely ignored."""
    # Omit secret_code, its validator should not cause issues
    PublicModel = omit_model(ValidatedModel, ("secret_code",), "PublicModel")

    # Valid instantiation should work
    model = PublicModel(age=20)
    assert model.age == 20


def test_all_fields_kept_validators_work():
    """When all fields kept, all validators work."""
    CompleteModel = omit_model(ValidatedModel, (), "CompleteModel")

    # Both validators should work
    with pytest.raises(ValidationError, match="Must be at least 18"):
        CompleteModel(age=15, secret_code="007")

    with pytest.raises(ValidationError, match="Invalid code"):
        CompleteModel(age=20, secret_code="123")


def test_omit_all_but_one_validator():
    """Omit all fields except one - validator still works."""
    AgeOnlyModel = omit_model(ValidatedModel, ("secret_code",), "AgeOnlyModel")

    # Age validator should still work
    with pytest.raises(ValidationError, match="Must be at least 18"):
        AgeOnlyModel(age=15)
