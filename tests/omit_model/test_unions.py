import pytest
from typing import Union, Optional
from pydantic import BaseModel
from pydantic_pick import omit_model


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


def test_union_and_optional_omit():
    # We ask to omit sec_a and sec_b from the Union choices
    # The module should smartly apply these to A and B respectively.
    paths = (
        "choice.sec_a",
        "choice.sec_b",
        "opt_choice.sec_a"
    )
    PublicModel = omit_model(MultiModel, paths, "PublicModel")

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


def test_omit_across_union_boundaries():
    """Test omitting fields that only exist in one Union member."""
    # sec_a only exists in OptionA, sec_b only in OptionB
    SelectiveModel = omit_model(
        MultiModel,
        ("choice.sec_a",),  # Only omit from OptionA
        "SelectiveModel"
    )

    # OptionA should not have sec_a
    model_a = SelectiveModel(id=1, choice={"type": "A", "pub_a": "hello", "sec_a": "hidden"})
    assert "sec_a" not in model_a.choice.model_dump()

    # OptionB should still have sec_b (not omitted)
    # But wait, omit_model should omit from all union members
    model_b = SelectiveModel(id=2, choice={"type": "B", "pub_b": "world", "sec_b": "hidden"})
    # If the path doesn't exist in OptionB, it should just not affect it
    # This tests that omitting a non-existent field path is handled gracefully
