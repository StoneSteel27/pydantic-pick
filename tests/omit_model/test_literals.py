from typing import Literal
from pydantic import BaseModel
from pydantic_pick import omit_model


class LiteralModel(BaseModel):
    id: int
    state: Literal["active", "pending", "banned"] = "pending"
    secret: str


def test_literal_preservation_with_omit():
    """Ensure Literal types survive when omitting other fields."""
    PublicModel = omit_model(LiteralModel, ("secret",), "PublicModel")

    # Test default literal assignment
    user1 = PublicModel(id=1)
    assert user1.state == "pending"

    # Test literal validation still works
    user2 = PublicModel(id=2, state="active")
    assert user2.state == "active"

    # Ensure secret is omitted
    assert "secret" not in user1.model_dump()


def test_omit_literal_field():
    """Test omitting the Literal field itself."""
    MinimalModel = omit_model(LiteralModel, ("state", "secret"), "MinimalModel")

    user = MinimalModel(id=1)
    assert user.model_dump() == {"id": 1}
    assert not hasattr(user, "state")


def test_omit_nothing_literal():
    """Ensure Literal is preserved when omitting nothing."""
    CompleteModel = omit_model(LiteralModel, (), "CompleteModel")

    # Test default for state, but secret is required
    user1 = CompleteModel(id=1, secret="hidden")
    assert user1.state == "pending"

    # Test explicit value
    user2 = CompleteModel(id=2, state="banned", secret="hidden")
    assert user2.state == "banned"
    assert user2.secret == "hidden"
