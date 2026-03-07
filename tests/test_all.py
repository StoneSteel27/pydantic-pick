import pytest
from typing import Dict, List, Optional, Union, Set, ClassVar
from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator, ValidationError
from pydantic_pick import create_subset


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
# 3. The Ultimate Test
# -------------------------------------------------------------------
def test_ultimate_deep_nested_combination():
    # We want to extract a clean public API response.
    # We must explicitly drop: password_hash, billing_secret, and internal_admin_note.
    paths = (
        "id",
        # Extract from Union mapped inside a Dict
        "profiles_map.type",
        "profiles_map.username",  # Will apply to ProfileA
        "profiles_map.company_name",  # Will apply to ProfileB

        # Extract from Set mapped inside Optional Model
        "optional_settings.theme",
        "optional_settings.active_permissions.resource",
        "optional_settings.active_permissions.access_level",

        # Extract from Union mapped inside a List
        "historical_log.type",
        "historical_log.username",
        "historical_log.company_name"
    )

    PublicUser = create_subset(EnterpriseUser, paths, "PublicUser")

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
    # Dict + Union extraction
    assert "password_hash" not in dump["profiles_map"]["main"]
    assert "billing_secret" not in dump["profiles_map"]["work"]
    assert dump["profiles_map"]["work"]["company_name"] == "Acme Corp"

    # Optional + Set extraction
    permission = dump["optional_settings"]["active_permissions"][0]
    assert "internal_admin_note" not in permission
    assert permission["access_level"] == 5

    # List + Union extraction
    assert "password_hash" not in dump["historical_log"][0]

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
