import pytest
from typing import Dict, List, Optional, Union, Set, ClassVar
from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator, ValidationError
from pydantic_pick import omit_model


# -------------------------------------------------------------------
# 1. Deep Base Models
# -------------------------------------------------------------------
class Permission(BaseModel):
    model_config = ConfigDict(frozen=True)  # Required for Sets

    resource: str
    access_level: int = Field(..., ge=1, le=5)
    internal_admin_note: str


class ProfileA(BaseModel):
    type: str = "A"
    username: str
    password_hash: str


class ProfileB(BaseModel):
    type: str = "B"
    company_name: str
    billing_secret: str


class AccountSettings(BaseModel):
    theme: str
    active_permissions: Set[Permission]


# -------------------------------------------------------------------
# 2. The Mega Root Model (Combining everything)
# -------------------------------------------------------------------
class EnterpriseUser(BaseModel):
    # Class Variables
    API_VERSION: ClassVar[str] = "v3"

    # Primitives & Basic Constraints
    id: int = Field(..., ge=1000)

    # Complex Nested Types (Union + Optional + Dict + List)
    profiles_map: Dict[str, Union[ProfileA, ProfileB]]
    optional_settings: Optional[AccountSettings] = None
    historical_log: List[Union[ProfileA, ProfileB]]

    # Validators
    @field_validator("id")
    @classmethod
    def check_id_not_test(cls, v):
        if v == 9999:
            raise ValueError("ID 9999 is reserved for internal tests")
        return v

    # Computed Fields & Custom Methods
    @computed_field
    def total_profiles(self) -> int:
        return len(self.profiles_map)

    def get_public_summary(self) -> str:
        return f"User {self.id} has {self.total_profiles} profiles."


# -------------------------------------------------------------------
# 3. The Ultimate Test for omit_model
# -------------------------------------------------------------------
def test_ultimate_deep_nested_omit():
    """Comprehensive test omitting sensitive fields from a complex nested model."""
    # We want to drop: password_hash, billing_secret, and internal_admin_note.
    paths = (
        "profiles_map.password_hash",
        "profiles_map.billing_secret",
        "optional_settings.active_permissions.internal_admin_note",
        "historical_log.password_hash"
    )

    PublicUser = omit_model(EnterpriseUser, paths, "PublicUser")

    # --- Assertions before instantiation ---

    # 1. ClassVar survived
    assert PublicUser.API_VERSION == "v3"

    # --- Instantiation Test ---
    data = {
        "id": 1050,
        "profiles_map": {
            "main": {"type": "A", "username": "Alice", "password_hash": "hash1"},
            "work": {"type": "B", "company_name": "Acme Corp", "billing_secret": "sec1"}
        },
        "optional_settings": {
            "theme": "dark",
            "active_permissions": [
                {"resource": "db", "access_level": 5, "internal_admin_note": "shh"}
            ]
        },
        "historical_log": [
            {"type": "A", "username": "Alice_old", "password_hash": "hash2"}
        ]
    }

    user = PublicUser(**data)
    dump = user.model_dump(mode="json")

    # 2. Check Data Extraction / Dropping Secrets
    # Dict + Union omission
    assert "password_hash" not in dump["profiles_map"]["main"]
    assert dump["profiles_map"]["main"]["username"] == "Alice"
    assert "billing_secret" not in dump["profiles_map"]["work"]
    assert dump["profiles_map"]["work"]["company_name"] == "Acme Corp"

    # Optional + Set omission
    permission = dump["optional_settings"]["active_permissions"][0]
    assert "internal_admin_note" not in permission
    assert permission["access_level"] == 5
    assert permission["resource"] == "db"

    # List + Union omission
    assert "password_hash" not in dump["historical_log"][0]
    assert dump["historical_log"][0]["username"] == "Alice_old"

    # 3. Check @computed_field & Methods survived
    assert dump["total_profiles"] == 2  # Computed fields appear in model_dump!
    assert user.get_public_summary() == "User 1050 has 2 profiles."

    # 4. Check Field constraints survived inside nested models (access_level <= 5)
    with pytest.raises(ValidationError, match="Input should be less than or equal to 5"):
        PublicUser(
            id=1050,
            profiles_map={},
            historical_log=[],
            optional_settings={
                "theme": "light",
                "active_permissions": [{"resource": "db", "access_level": 9}]  # 9 is > 5
            }
        )

    # 5. Check @field_validator survived
    with pytest.raises(ValidationError, match="ID 9999 is reserved for internal tests"):
        PublicUser(id=9999, profiles_map={}, historical_log=[])


def test_omit_model_preserves_all_features():
    """Test that all features are preserved when omitting nothing."""
    CompleteUser = omit_model(EnterpriseUser, (), "CompleteUser")

    # All fields should be present
    assert "id" in CompleteUser.model_fields
    assert "profiles_map" in CompleteUser.model_fields
    assert "optional_settings" in CompleteUser.model_fields
    assert "historical_log" in CompleteUser.model_fields

    # All methods should work
    data = {
        "id": 1001,
        "profiles_map": {"main": {"type": "A", "username": "Test", "password_hash": "hash"}},
        "historical_log": []
    }

    user = CompleteUser(**data)
    assert user.total_profiles == 1
    assert "1001" in user.get_public_summary()
