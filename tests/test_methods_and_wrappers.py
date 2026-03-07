import functools
import pytest
from pydantic import BaseModel, computed_field
from pydantic_pick import create_subset


# -------------------------------------------------------------------
# Custom Wrappers
# -------------------------------------------------------------------

# 1. Standard Function-based Decorator
def log_execution(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # We will use this to verify the wrapper actually ran
        wrapper.has_run = True
        return func(*args, **kwargs)

    wrapper.has_run = False
    return wrapper


# 2. Class-based Decorator (Callable Object)
class PrefixWrapper:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return f"[{self.prefix}] {func(*args, **kwargs)}"

        return wrapper


# -------------------------------------------------------------------
# The Test Model
# -------------------------------------------------------------------
class Document(BaseModel):
    id: int
    title: str
    content: str
    internal_draft: bool  # We will drop this

    # A standard Pydantic Computed Field
    @computed_field
    def word_count(self) -> int:
        return len(self.content.split())

    # A standard instance method (no decorators)
    def get_summary(self) -> str:
        return f"{self.title}: {self.content[:10]}..."

    # A method with a custom function decorator
    @log_execution
    def process_document(self) -> str:
        return "Processed"

    # A method with a custom class-based callable decorator
    @PrefixWrapper("DOC")
    def get_formatted_title(self) -> str:
        return self.title


# -------------------------------------------------------------------
# The Test
# -------------------------------------------------------------------
def test_all_method_types_and_wrappers():
    paths = ("id", "title", "content")

    # Extract
    PublicDoc = create_subset(Document, paths, "PublicDoc")

    # Instantiate
    doc = PublicDoc(id=1, title="Test Doc", content="This is a very important document.")

    # 1. Assert standard fields work and dropped fields are gone
    assert doc.id == 1
    assert not hasattr(doc, "internal_draft")

    # 2. Assert @computed_field perfectly survived and appears in model_dump
    assert doc.word_count == 6
    dump = doc.model_dump()
    assert "word_count" in dump
    assert dump["word_count"] == 6

    # 3. Assert standard instance method survived
    assert doc.get_summary() == "Test Doc: This is a ..."

    # 4. Assert custom function-wrapper survived and executed
    assert getattr(doc.process_document, "has_run", None) is False
    assert doc.process_document() == "Processed"
    assert getattr(doc.process_document, "has_run", None) is True

    # 5. Assert custom class-based wrapper survived and executed
    assert doc.get_formatted_title() == "[DOC] Test Doc"

    # Ensure Pydantic's internal state didn't bleed into standard dir()
    attrs = dir(doc)
    assert "model_fields" in attrs
    assert "process_document" in attrs