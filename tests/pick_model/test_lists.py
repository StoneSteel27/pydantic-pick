from typing import List
from pydantic import BaseModel, Field
from pydantic_pick import pick_model


# Test models specifically for List operations
class ListItem(BaseModel):
    id: int
    name: str
    secret: str


class ContainerWithList(BaseModel):
    title: str
    items: List[ListItem]
    metadata: str = "default"


def test_list_field_extraction():
    """Test extracting specific fields from models inside a List."""
    PublicContainer = pick_model(
        ContainerWithList,
        ("title", "items.id", "items.name"),
        "PublicContainer"
    )

    data = {
        "title": "My Container",
        "items": [
            {"id": 1, "name": "Item 1", "secret": "secret1"},
            {"id": 2, "name": "Item 2", "secret": "secret2"}
        ]
    }

    container = PublicContainer(**data)
    dump = container.model_dump()

    assert dump["title"] == "My Container"
    assert len(dump["items"]) == 2

    # Check first item
    assert dump["items"][0]["id"] == 1
    assert dump["items"][0]["name"] == "Item 1"
    assert "secret" not in dump["items"][0]

    # Check second item
    assert dump["items"][1]["id"] == 2
    assert dump["items"][1]["name"] == "Item 2"
    assert "secret" not in dump["items"][1]

    # Metadata should be omitted
    assert "metadata" not in dump


def test_list_with_default_value():
    """Test list extraction with default metadata field."""
    PublicContainer = pick_model(
        ContainerWithList,
        ("title", "items.id", "metadata"),
        "PublicContainer"
    )

    # Only provide title, items required
    data = {
        "title": "Container",
        "items": [{"id": 1, "name": "Test", "secret": "hidden"}]
    }

    container = PublicContainer(**data)
    dump = container.model_dump()

    assert dump["title"] == "Container"
    assert dump["metadata"] == "default"
    assert dump["items"][0]["id"] == 1
    assert "name" not in dump["items"][0]


def test_empty_list():
    """Test handling of empty lists."""
    PublicContainer = pick_model(
        ContainerWithList,
        ("title", "items.id", "items.name"),
        "PublicContainer"
    )

    container = PublicContainer(title="Empty", items=[])
    dump = container.model_dump()

    assert dump["title"] == "Empty"
    assert dump["items"] == []
