import pytest
from typing import List, Dict, Union
from typing_extensions import TypeAliasType
from pydantic import BaseModel
from pydantic_pick import omit_model

# The Pydantic-safe way to define a recursive type in Python < 3.12
JsonType = TypeAliasType(
    "JsonType",
    Union[Dict[str, "JsonType"], List["JsonType"], str, int, float, bool, None]
)


class Webhook(BaseModel):
    event_id: str
    payload: JsonType
    server_ip: str  # We want to omit this


def test_recursive_json_passthrough_with_omit():
    """Ensure recursive types work when omitting fields."""
    PublicWebhook = omit_model(Webhook, ("server_ip",), "PublicWebhook")

    data = {
        "event_id": "evt_123",
        "payload": {
            "user": "Alice",
            "nested_list": [1, 2, {"deep": True}],
            "is_active": True
        },
        "server_ip": "192.168.1.1"
    }

    webhook = PublicWebhook(**data)
    dump = webhook.model_dump()

    assert dump["payload"]["nested_list"][2]["deep"] is True
    assert "server_ip" not in dump
    assert dump["event_id"] == "evt_123"


def test_omit_nothing_preserves_recursive():
    """Ensure recursive types are preserved when omitting nothing."""
    CompleteWebhook = omit_model(Webhook, (), "CompleteWebhook")

    data = {
        "event_id": "evt_456",
        "payload": {"key": "value"},
        "server_ip": "10.0.0.1"
    }

    webhook = CompleteWebhook(**data)
    dump = webhook.model_dump()

    assert dump["event_id"] == "evt_456"
    assert dump["server_ip"] == "10.0.0.1"
    assert dump["payload"] == {"key": "value"}
