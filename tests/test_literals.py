from typing import Literal
from pydantic import BaseModel
from pydantic_pick import create_subset


class LiteralModel(BaseModel):
    id: int
    state: Literal["active", "pending", "banned"] = "pending"
    secret: str


def test_literal_preservation():
    PublicModel = create_subset(LiteralModel, ("id", "state"), "PublicModel")

    # Test default literal assignment
    user1 = PublicModel(id=1)
    assert user1.state == "pending"

    # Test literal validation still works
    user2 = PublicModel(id=2, state="active")
    assert user2.state == "active"
