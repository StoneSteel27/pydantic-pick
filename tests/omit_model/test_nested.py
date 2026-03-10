from pydantic import BaseModel
from pydantic_pick import omit_model


class DeepSettings(BaseModel):
    theme: str
    api_key: str


class Profile(BaseModel):
    bio: str
    settings: DeepSettings


class UserNested(BaseModel):
    id: int
    profile: Profile


def test_omit_nested_field():
    """Ensure dot-notation correctly omits nested Pydantic model fields."""
    PublicUser = omit_model(
        UserNested,
        ("profile.settings.api_key",),
        "PublicUser"
    )

    # Instantiate the data (api_key is completely omitted)
    user = PublicUser(
        id=1,
        profile={"bio": "Hello", "settings": {"theme": "dark"}}
    )

    dump = user.model_dump()
    assert dump["id"] == 1
    assert dump["profile"]["bio"] == "Hello"
    assert dump["profile"]["settings"]["theme"] == "dark"
    assert "api_key" not in dump["profile"]["settings"]


def test_omit_entire_nested_model():
    """Omit entire nested model."""
    MinimalUser = omit_model(
        UserNested,
        ("profile",),
        "MinimalUser"
    )

    assert "profile" not in MinimalUser.model_fields
    user = MinimalUser(id=1)
    assert user.model_dump() == {"id": 1}


def test_omit_multiple_nested_fields():
    """Omit multiple fields from different nesting levels."""
    SelectiveUser = omit_model(
        UserNested,
        ("profile.bio", "profile.settings.api_key"),
        "SelectiveUser"
    )

    user = SelectiveUser(
        id=1,
        profile={"settings": {"theme": "dark"}}
    )

    dump = user.model_dump()
    assert dump["id"] == 1
    assert "bio" not in dump["profile"]
    assert dump["profile"]["settings"]["theme"] == "dark"
    assert "api_key" not in dump["profile"]["settings"]
