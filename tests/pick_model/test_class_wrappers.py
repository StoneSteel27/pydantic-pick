import pytest
from functools import partial
from pydantic import BaseModel, ConfigDict
from pydantic_pick import pick_model


# --- Class-Based Decorator ---
class ClassWrapper:
    """A custom class acting as a method decorator."""

    def __init__(self, func):
        self.func = func  # Save the original method here
        self.num_calls = 0

    def __call__(self, *args, **kwargs):
        self.num_calls += 1
        return self.func(*args, **kwargs)

    def __get__(self, instance, owner):
        # This makes it behave like a bound method on the class
        if instance is None:
            return self
        return partial(self.__call__, instance)


# --- Mock Model ---
class DocumentItem(BaseModel):
    # FIX: Tell Pydantic V2 to not treat our class decorator as a missing type-hint field!
    model_config = ConfigDict(ignored_types=(ClassWrapper,))

    id: int
    title: str
    confidential_notes: str

    @ClassWrapper
    def read_notes(self) -> str:
        # Relies on the 'confidential_notes' field, behind a class decorator
        return f"Notes: {self.confidential_notes}"


# --- Tests ---

def test_omitted_class_wrapped_methods_raise_custom_error():
    """
    Ensures that methods wrapped in a class decorator are successfully
    unwrapped (via .func), parsed, and omitted if dependencies are missing.
    """
    # We omit 'confidential_notes'
    PublicDocument = pick_model(DocumentItem, ("id", "title"), "PublicDocument")

    doc = PublicDocument(id=1, title="Public Specs")

    # Because 'confidential_notes' is missing, the AST parser should have
    # stripped away the ClassWrapper, seen the dependency, and dropped read_notes().
    with pytest.raises(AttributeError, match="intentionally omitted by pydantic-pick"):
        doc.read_notes()


def test_kept_class_wrapped_methods_work_normally():
    """
    Ensures that if the dependencies ARE included, the class wrapper
    survives, binds properly, and tracks state correctly.
    """
    # We include everything
    FullDocument = pick_model(
        DocumentItem,
        ("id", "title", "confidential_notes"),
        "FullDocument"
    )

    doc = FullDocument(id=1, title="Public Specs", confidential_notes="Top secret!")

    # The method survives and executes normally through the ClassWrapper
    assert doc.read_notes() == "Notes: Top secret!"

    # Optional: Verify the wrapper's internal state was properly maintained
    # We access the descriptor from the class dictionary
    wrapper_instance = FullDocument.read_notes
    assert wrapper_instance.num_calls == 1
