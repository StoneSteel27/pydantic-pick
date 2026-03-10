import pytest
from typing import Annotated, List
from pydantic import BaseModel, Field, AfterValidator, ValidationError
from pydantic_pick import pick_model


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


def test_annotated_preservation():
    paths = ("items.id", "name")
    PublicModel = pick_model(RootModel, paths, "PublicModel")

    # 1. Test basic extraction
    model = PublicModel(name="test", items=[{"id": 1, "secret": "hide"}])
    assert "secret" not in model.model_dump()["items"][0]

    # 2. Test that Field(min_length=1) survived
    with pytest.raises(ValidationError, match="List should have at least 1 item after validation"):
        PublicModel(name="test", items=[])  # Empty list should fail
