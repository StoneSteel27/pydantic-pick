from pydantic import BaseModel
from pydantic_pick import pick_model


class DeepSettings(BaseModel):
    theme: str
    api_key: str


class Profile(BaseModel):
    bio: str
    settings: DeepSettings


class UserNested(BaseModel):
    id: int
    profile: Profile


def test_nested_model_extraction():
    """Ensure dot-notation correctly rebuilds nested Pydantic models."""
    PublicUser = pick_model(
        UserNested,
        ("id", "profile.bio", "profile.settings.theme"),
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
