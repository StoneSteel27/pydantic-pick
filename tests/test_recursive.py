import pytest
from typing import List, Dict, Union
from typing_extensions import TypeAliasType
from pydantic import BaseModel
from pydantic_pick import create_subset

# The Pydantic-safe way to define a recursive type in Python < 3.12
JsonType = TypeAliasType(
    "JsonType",
    Union[Dict[str, "JsonType"], List["JsonType"], str, int, float, bool, None]
)


class Webhook(BaseModel):
    event_id: str
    payload: JsonType
    server_ip: str  # We want to drop this


def test_recursive_json_passthrough():
    PublicWebhook = create_subset(Webhook, ("event_id", "payload"), "PublicWebhook")

    data = {
        "event_id": "evt_123",
        "payload": {
            "user": "Alice",
            "nested_list": [1, 2, {"deep": True}],
            "is_active": True
        }
    }

    webhook = PublicWebhook(**data)
    dump = webhook.model_dump()

    assert dump["payload"]["nested_list"][2]["deep"] is True
    assert "server_ip" not in dump
