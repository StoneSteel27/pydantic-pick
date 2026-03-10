import pytest
from typing import Dict, Set, Tuple
from pydantic import BaseModel, ConfigDict
from pydantic_pick import omit_model


# A model destined for a Set MUST be frozen in Pydantic V2
class Profile(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str
    admin_note: str  # We want to drop this


class SystemState(BaseModel):
    user_map: Dict[str, Profile]
    history: Tuple[int, str, Profile]
    active_profiles: Set[Profile]


def test_complex_collections_omit():
    """Ensure dot-notation correctly omits fields within collection types."""
    # Omit admin_note from all nested Profile models
    PublicState = omit_model(
        SystemState,
        ("user_map.admin_note", "history.admin_note", "active_profiles.admin_note"),
        "PublicState"
    )

    state = PublicState(
        user_map={"user_1": {"username": "Alice", "admin_note": "secret"}},
        history=(404, "login", {"username": "Bob", "admin_note": "secret"}),
        # When passing to a Set, pass the instantiated model to avoid dict hashing bugs
        active_profiles={PublicState.model_fields["active_profiles"].annotation.__args__[0](username="Charlie")}
    )

    # In Pydantic V2, dumping a set of models sometimes raises unhashable dict errors
    # if you don't use mode='json'
    dump = state.model_dump(mode="json")

    assert dump["user_map"]["user_1"]["username"] == "Alice"
    assert "admin_note" not in dump["user_map"]["user_1"]

    assert dump["history"][2]["username"] == "Bob"

    # Sets are dumped as lists in JSON mode
    set_item = dump["active_profiles"][0]
    assert set_item["username"] == "Charlie"
    assert "admin_note" not in set_item


def test_omit_entire_collection_model():
    """Omit entire nested model within collection."""
    # This tests omitting at a different level
    # If we omit 'user_map.username', the username field should be gone
    PartialState = omit_model(
        SystemState,
        ("user_map.username",),
        "PartialState"
    )

    # user_map should still exist but without username
    state = PartialState(
        user_map={"user_1": {"admin_note": "secret"}},
        history=(404, "login", {"username": "Bob", "admin_note": "note"}),
        # active_profiles - provide empty set to avoid the complex Profile instantiation
        active_profiles=set()
    )

    dump = state.model_dump(mode="json")
    assert "username" not in dump["user_map"]["user_1"]
    assert dump["user_map"]["user_1"]["admin_note"] == "secret"
    # Other collections should still have username
    assert dump["history"][2]["username"] == "Bob"
