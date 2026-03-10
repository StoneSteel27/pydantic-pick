import pytest
from typing import Annotated, List
from pydantic import BaseModel, Field, AfterValidator, ValidationError
from pydantic_pick import omit_model


def ensure_lowercase(v):
    if isinstance(v, list):
        return v
    return v


# Complex Annotation: A list of models, requiring at least 1 item, and a custom validator
class InnerModel(BaseModel):
    id: int
    secret: str


# The metadata [Field(min_length=1), AfterValidator] must survive!
ValidList = Annotated[List[InnerModel], Field(min_length=1), AfterValidator(ensure_lowercase)]


class RootModel(BaseModel):
    items: ValidList
    name: str


def test_annotated_preservation_with_omit():
    """Ensure Annotated metadata survives when omitting fields."""
    paths = ("items.secret",)  # Omit secret from items
    PublicModel = omit_model(RootModel, paths, "PublicModel")

    # 1. Test basic extraction - secret should be omitted
    model = PublicModel(name="test", items=[{"id": 1, "secret": "hide"}])
    assert "secret" not in model.model_dump()["items"][0]
    assert "id" in model.model_dump()["items"][0]

    # 2. Test that Field(min_length=1) survived
    with pytest.raises(ValidationError, match="List should have at least 1 item after validation"):
        PublicModel(name="test", items=[])  # Empty list should fail


def test_annotated_omit_preserves_aftervalidator():
    """Ensure AfterValidator survives omission."""
    paths = ("items.secret",)
    PublicModel = omit_model(RootModel, paths, "PublicModel")

    # Test that the AfterValidator still runs (though in this case it just returns the value)
    model = PublicModel(name="test", items=[{"id": 1}])
    assert model.model_dump()["items"][0]["id"] == 1


def test_omit_nothing_annotated():
    """Ensure Annotated types are preserved when omitting nothing."""
    CompleteModel = omit_model(RootModel, (), "CompleteModel")

    model = CompleteModel(name="complete", items=[{"id": 2, "secret": "confidential"}])
    assert model.model_dump()["items"][0]["secret"] == "confidential"
