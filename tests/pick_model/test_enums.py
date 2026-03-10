from enum import Enum
from pydantic import BaseModel
from pydantic_pick import pick_model


class RoleEnum(str, Enum):
    ADMIN = "admin"
    GUEST = "guest"


class UserWithEnum(BaseModel):
    id: int
    role: RoleEnum
    secret: str


def test_enum_preservation():
    PublicUser = pick_model(UserWithEnum, ("id", "role"), "PublicUser")

    # Ensure Pydantic still enforces the Enum validation
    user = PublicUser(id=1, role="admin")
    assert user.role == RoleEnum.ADMIN
    assert "secret" not in user.model_dump()
