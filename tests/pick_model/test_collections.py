import pytest
from typing import Dict, Set, Tuple
from pydantic import BaseModel, ConfigDict
from pydantic_pick import pick_model


# A model destined for a Set MUST be frozen in Pydantic V2
class Profile(BaseModel):
    model_config = ConfigDict(frozen=True)

    username: str
    admin_note: str  # We want to drop this


class SystemState(BaseModel):
    user_map: Dict[str, Profile]
    history: Tuple[int, str, Profile]
    active_profiles: Set[Profile]


def test_complex_collections_extraction():
    paths = (
        "user_map.username",
        "history.username",
        "active_profiles.username"
    )

    PublicState = pick_model(SystemState, paths, "PublicState")

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
