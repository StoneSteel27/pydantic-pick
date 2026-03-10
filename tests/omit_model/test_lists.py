from typing import List
from pydantic import BaseModel, Field
from pydantic_pick import omit_model


# Test models specifically for List operations
class ListItem(BaseModel):
    id: int
    name: str
    secret: str


class ContainerWithList(BaseModel):
    title: str
    items: List[ListItem]
    metadata: str = "default"


def test_list_field_omission():
    """Test omitting specific fields from models inside a List."""
    PublicContainer = omit_model(
        ContainerWithList,
        ("items.secret",),
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

    # Check first item - secret should be omitted
    assert dump["items"][0]["id"] == 1
    assert dump["items"][0]["name"] == "Item 1"
    assert "secret" not in dump["items"][0]

    # Check second item - secret should be omitted
    assert dump["items"][1]["id"] == 2
    assert dump["items"][1]["name"] == "Item 2"
    assert "secret" not in dump["items"][1]

    # Metadata should be present (not omitted)
    assert dump["metadata"] == "default"


def test_list_omit_with_top_level_fields():
    """Test omitting both list item fields and top-level fields."""
    MinimalContainer = omit_model(
        ContainerWithList,
        ("items.name", "items.secret", "metadata"),
        "MinimalContainer"
    )

    data = {
        "title": "Minimal",
        "items": [{"id": 1, "name": "Test", "secret": "hidden"}]
    }

    container = MinimalContainer(**data)
    dump = container.model_dump()

    assert dump["title"] == "Minimal"
    assert dump["items"][0]["id"] == 1
    assert "name" not in dump["items"][0]
    assert "secret" not in dump["items"][0]
    assert "metadata" not in dump


def test_empty_list_omit():
    """Test handling of empty lists when omitting fields."""
    PublicContainer = omit_model(
        ContainerWithList,
        ("items.secret",),
        "PublicContainer"
    )

    container = PublicContainer(title="Empty", items=[])
    dump = container.model_dump()

    assert dump["title"] == "Empty"
    assert dump["items"] == []
    assert dump["metadata"] == "default"


def test_list_omit_nothing():
    """Test list handling when omitting nothing."""
    CompleteContainer = omit_model(ContainerWithList, (), "CompleteContainer")

    data = {
        "title": "Complete",
        "items": [{"id": 1, "name": "Item", "secret": "secret"}]
    }

    container = CompleteContainer(**data)
    dump = container.model_dump()

    assert dump["items"][0]["secret"] == "secret"
    assert dump["metadata"] == "default"
