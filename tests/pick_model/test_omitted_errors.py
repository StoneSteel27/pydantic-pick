import pytest
from pydantic import BaseModel, computed_field
from pydantic_pick import pick_model
import functools

# --- Mock Model for Testing ---

class InvoiceItem(BaseModel):
    id: int
    price: float
    tax_rate: float

    @computed_field
    def total_cost(self) -> float:
        # Depends on 'price' and 'tax_rate'
        return self.price + (self.price * self.tax_rate)

    def print_receipt(self) -> str:
        # Depends on 'id' and the computed field 'total_cost'
        return f"Item {self.id}: ${self.total_cost}"

# --- Custom Wrapper ---
def requires_auth(func):
    """A dummy decorator that simulates an auth wrapper."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# --- Mock Model for Testing Custom Wrappers ---
class SecuredItem(BaseModel):
    id: int
    public_data: str
    secret_code: str

    @requires_auth
    def get_secret(self) -> str:
        # Relies on the 'secret_code' field, but is hidden behind a decorator
        return f"Secret is: {self.secret_code}"


# --- Tests ---

def test_omitted_attributes_raise_custom_error():
    """
    Tests that dynamically omitted fields, computed fields, and methods
    raise a custom developer-friendly AttributeError.
    """
    # We deliberately omit 'tax_rate'.
    # This should cascade and drop 'total_cost', which drops 'print_receipt'.
    PublicItem = pick_model(InvoiceItem, ("id", "price"), "PublicItem")

    item = PublicItem(id=1, price=100.0)

    # 1. Test omitted standard data field
    with pytest.raises(AttributeError, match="intentionally omitted by pydantic-pick"):
        _ = item.tax_rate

    # 2. Test omitted @computed_field
    with pytest.raises(AttributeError, match="intentionally omitted by pydantic-pick"):
        _ = item.total_cost

    # 3. Test omitted method
    with pytest.raises(AttributeError, match="intentionally omitted by pydantic-pick"):
        item.print_receipt()


def test_genuine_missing_attributes_use_standard_error():
    """
    Ensures that if a developer typos a property name, they get a
    standard Python AttributeError, not our custom pydantic-pick one.
    """
    PublicItem = pick_model(InvoiceItem, ("id", "price"), "PublicItem")
    item = PublicItem(id=1, price=100.0)

    # Accessing a completely fake attribute
    with pytest.raises(AttributeError) as exc_info:
        _ = item.typo_field

    # The error message should be the standard Python one, NOT our custom one
    assert "intentionally omitted by pydantic-pick" not in str(exc_info.value)
    assert "'PublicItem' object has no attribute 'typo_field'" in str(exc_info.value)


def test_kept_attributes_work_normally():
    """
    Ensures that if dependencies ARE met, methods and computed fields work fine.
    """
    # This time, we include all required dependencies
    FullItem = pick_model(InvoiceItem, ("id", "price", "tax_rate"), "FullItem")
    item = FullItem(id=1, price=100.0, tax_rate=0.05)

    # Nothing should raise an error
    assert item.tax_rate == 0.05
    assert item.total_cost == 105.0
    assert item.print_receipt() == "Item 1: $105.0"


def test_omitted_wrapped_methods_raise_custom_error():
    """
    Ensures that methods wrapped in custom decorators (like @requires_auth)
    are successfully unwrapped, their AST is parsed, and they are omitted
    if their dependencies are missing.
    """
    # We deliberately omit 'secret_code'
    PublicSecured = pick_model(SecuredItem, ("id", "public_data"), "PublicSecured")

    item = PublicSecured(id=1, public_data="hello")

    # Because 'secret_code' is missing, the AST parser should have looked inside
    # the @requires_auth wrapper, seen the dependency, and dropped get_secret().
    with pytest.raises(AttributeError, match="intentionally omitted by pydantic-pick"):
        item.get_secret()


def test_kept_wrapped_methods_work_normally():
    """
    Ensures that if the dependencies for a wrapped method ARE included,
    the method survives and the decorator still functions properly.
    """
    # We include everything
    FullSecured = pick_model(SecuredItem, ("id", "public_data", "secret_code"), "FullSecured")

    item = FullSecured(id=1, public_data="hello", secret_code="12345")

    # The method should survive and execute normally through the wrapper
    assert item.get_secret() == "Secret is: 12345"
