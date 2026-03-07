import pytest
from typing import Union, Optional
from pydantic import BaseModel
from pydantic_pick import create_subset


class OptionA(BaseModel):
    type: str = "A"
    pub_a: str
    sec_a: str


class OptionB(BaseModel):
    type: str = "B"
    pub_b: str
    sec_b: str


class MultiModel(BaseModel):
    id: int
    # Tests standard Union (or A | B)
    choice: Union[OptionA, OptionB]
    # Tests Optional (which is technically Union[OptionA, None])
    opt_choice: Optional[OptionA] = None


def test_union_and_optional_extraction():
    # We ask to keep type, pub_a, and pub_b.
    # The module should smartly apply these to A and B respectively.
    paths = (
        "id",
        "choice.type",
        "choice.pub_a",
        "choice.pub_b",
        "opt_choice.pub_a"
    )
    PublicModel = create_subset(MultiModel, paths, "PublicModel")

    # Test instantiation with Option A
    model_a = PublicModel(id=1, choice={"type": "A", "pub_a": "hello", "sec_a": "hidden"})
    assert "sec_a" not in model_a.choice.model_dump()
    assert hasattr(model_a.choice, "pub_a")

    # Test instantiation with Option B
    model_b = PublicModel(id=2, choice={"type": "B", "pub_b": "world", "sec_b": "hidden"})
    assert "sec_b" not in model_b.choice.model_dump()
    assert hasattr(model_b.choice, "pub_b")

    # Test Optional handling
    assert model_a.opt_choice is None
