import pytest
from pydantic import BaseModel, Field
from pydantic_pick import omit_model


class UserFlat(BaseModel):
    id: int = Field(..., ge=1)
    username: str
    password_hash: str
    is_active: bool = True


def test_omit_single_field():
    """Omit single field, keep rest."""
    PublicUser = omit_model(UserFlat, ("password_hash",), "PublicUser")

    # Check fields - password_hash should be omitted
    assert "id" in PublicUser.model_fields
    assert "username" in PublicUser.model_fields
    assert "is_active" in PublicUser.model_fields
    assert "password_hash" not in PublicUser.model_fields


def test_omit_multiple_fields():
    """Omit multiple fields, keep rest."""
    MinimalUser = omit_model(UserFlat, ("password_hash", "is_active"), "MinimalUser")

    assert "id" in MinimalUser.model_fields
    assert "username" in MinimalUser.model_fields
    assert "password_hash" not in MinimalUser.model_fields
    assert "is_active" not in MinimalUser.model_fields


def test_omit_model_instantiation():
    """Ensure the dynamically created model can be instantiated."""
    PublicUser = omit_model(UserFlat, ("password_hash",), "PublicUser")
    user = PublicUser(id=1, username="alice", is_active=True)

    assert user.model_dump() == {"id": 1, "username": "alice", "is_active": True}


def test_omit_model_preserves_field_constraints():
    """Ensure field constraints survive omission."""
    PublicUser = omit_model(UserFlat, ("password_hash",), "PublicUser")

    # The ge=1 constraint should still be enforced
    with pytest.raises(Exception):  # ValidationError
        PublicUser(id=0, username="alice", is_active=True)


def test_omit_nothing_returns_complete_model():
    """Omit nothing - should return functionally identical model."""
    CompleteUser = omit_model(UserFlat, (), "CompleteUser")

    # All fields should be present
    assert "id" in CompleteUser.model_fields
    assert "username" in CompleteUser.model_fields
    assert "password_hash" in CompleteUser.model_fields
    assert "is_active" in CompleteUser.model_fields


def test_omit_all_fields():
    """Omit all fields - creates minimal model."""
    EmptyUser = omit_model(UserFlat, ("id", "username", "password_hash", "is_active"), "EmptyUser")

    # Model should exist but have no fields
    assert len(EmptyUser.model_fields) == 0
    user = EmptyUser()
    assert user.model_dump() == {}
