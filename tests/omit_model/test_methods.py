import functools
import pytest
from pydantic import BaseModel, computed_field
from pydantic_pick import omit_model


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
    internal_draft: bool  # We will omit this

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
# The Tests
# -------------------------------------------------------------------
def test_omit_preserves_computed_field():
    """Ensure @computed_field survives when its dependencies are kept."""
    # Omit internal_draft, keep fields that word_count needs (content)
    PublicDoc = omit_model(Document, ("internal_draft",), "PublicDoc")

    # Instantiate
    doc = PublicDoc(id=1, title="Test Doc", content="This is a very important document.")

    # Assert @computed_field perfectly survived and appears in model_dump
    assert doc.word_count == 6
    dump = doc.model_dump()
    assert "word_count" in dump
    assert dump["word_count"] == 6


def test_omit_preserves_standard_method():
    """Ensure standard instance methods survive."""
    PublicDoc = omit_model(Document, ("internal_draft",), "PublicDoc")

    doc = PublicDoc(id=1, title="Test Doc", content="This is a very important document.")

    # Assert standard instance method survived
    assert doc.get_summary() == "Test Doc: This is a ..."


def test_omit_preserves_function_wrapper():
    """Ensure custom function-wrapper decorators survive."""
    PublicDoc = omit_model(Document, ("internal_draft",), "PublicDoc")

    doc = PublicDoc(id=1, title="Test Doc", content="This is a very important document.")

    # Assert custom function-wrapper survived and executed
    assert getattr(doc.process_document, "has_run", None) is False
    assert doc.process_document() == "Processed"
    assert getattr(doc.process_document, "has_run", None) is True


def test_omit_preserves_class_wrapper():
    """Ensure custom class-based wrapper decorators survive."""
    PublicDoc = omit_model(Document, ("internal_draft",), "PublicDoc")

    doc = PublicDoc(id=1, title="Test Doc", content="This is a very important document.")

    # Assert custom class-based wrapper survived and executed
    assert doc.get_formatted_title() == "[DOC] Test Doc"


def test_omit_cascades_to_computed_field():
    """If computed_field dependency is omitted, computed_field should be omitted."""
    # Omit content, which word_count depends on
    MinimalDoc = omit_model(Document, ("content", "internal_draft"), "MinimalDoc")

    doc = MinimalDoc(id=1, title="Test Doc")

    # word_count should be omitted because it depends on content
    assert not hasattr(doc, "word_count")


def test_omit_cascades_to_method():
    """If method dependency is omitted, method should be omitted."""
    # Omit title, which get_summary depends on
    MinimalDoc = omit_model(Document, ("title", "internal_draft"), "MinimalDoc")

    doc = MinimalDoc(id=1, content="This is content.")

    # get_summary should be omitted because it depends on title
    assert not hasattr(doc, "get_summary")
