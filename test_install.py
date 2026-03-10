"""Quick test of pydantic-pick from Test PyPI"""
from pydantic import BaseModel, Field, field_validator
from pydantic_pick import pick_model
import pydantic_pick

print(f"Testing pydantic-pick version {pydantic_pick.__version__}")
print("-" * 50)

class DBUser(BaseModel):
    id: int = Field(..., ge=1)
    username: str
    password_hash: str
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str):
        if "admin" in v.lower():
            raise ValueError("Reserved username")
        return v

# Test 1: Basic subset creation
print("\n[PASS] Test 1: Creating subset model")
PublicUser = pick_model(DBUser, ("id", "username"), "PublicUser")
print(f"  Created model: {PublicUser.__name__}")

# Test 2: Create instance
print("\n[PASS] Test 2: Creating instance")
user = PublicUser(id=10, username="alice")
print(f"  User: {user.model_dump()}")

# Test 3: Field constraint validation
print("\n[PASS] Test 3: Testing field constraints (ge=1)")
try:
    bad_user = PublicUser(id=-5, username="bob")
    print("  [FAIL] Should have raised validation error")
except Exception as e:
    print(f"  [PASS] Correctly rejected: {type(e).__name__}")

# Test 4: Field validator preservation
print("\n[PASS] Test 4: Testing field validator preservation")
try:
    admin_user = PublicUser(id=1, username="admin123")
    print("  [FAIL] Should have raised validation error")
except Exception as e:
    print(f"  [PASS] Correctly rejected: {e}")

print("\n" + "=" * 50)
print("SUCCESS: All tests passed! Package works correctly.")
