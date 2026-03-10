import pytest
from pydantic import BaseModel, Field
from pydantic_pick import pick_model


class UserFlat(BaseModel):
    id: int = Field(..., ge=1)
    username: str
    password_hash: str
    is_active: bool = True


def test_flat_model_extraction():
    """Ensure basic fields are kept and omitted correctly."""
    PublicUser = pick_model(UserFlat, ("id", "username"), "PublicUser")

    # Check fields
    assert "id" in PublicUser.model_fields
    assert "username" in PublicUser.model_fields
    assert "password_hash" not in PublicUser.model_fields
    assert "is_active" not in PublicUser.model_fields


def test_flat_model_instantiation():
    """Ensure the dynamically created model can be instantiated."""
    PublicUser = pick_model(UserFlat, ("id", "username"), "PublicUser")
    user = PublicUser(id=1, username="alice")

    assert user.model_dump() == {"id": 1, "username": "alice"}
