from enum import Enum
from pydantic import BaseModel
from pydantic_pick import omit_model


class RoleEnum(str, Enum):
    ADMIN = "admin"
    GUEST = "guest"


class UserWithEnum(BaseModel):
    id: int
    role: RoleEnum
    secret: str


def test_enum_preservation_with_omit():
    """Ensure Enum types survive when omitting other fields."""
    PublicUser = omit_model(UserWithEnum, ("secret",), "PublicUser")

    # Ensure Pydantic still enforces the Enum validation
    user = PublicUser(id=1, role="admin")
    assert user.role == RoleEnum.ADMIN
    assert "secret" not in user.model_dump()
    assert "id" in user.model_dump()


def test_omit_enum_field():
    """Test omitting the Enum field itself."""
    MinimalUser = omit_model(UserWithEnum, ("role", "secret"), "MinimalUser")

    user = MinimalUser(id=1)
    assert user.model_dump() == {"id": 1}
    assert not hasattr(user, "role")


def test_omit_nothing_enum():
    """Ensure Enum is preserved when omitting nothing."""
    CompleteUser = omit_model(UserWithEnum, (), "CompleteUser")

    user = CompleteUser(id=1, role="guest", secret="hidden")
    assert user.role == RoleEnum.GUEST
    assert user.secret == "hidden"
