<p align="center">
  <img src="https://raw.githubusercontent.com/StoneSteel27/pydantic-pick/main/assets/logo.svg" width="200" alt="pydantic-pick logo">
</p>

<p align="center">
  <a href="https://github.com/StoneSteel27/pydantic-pick/actions/workflows/tests.yml"><img src="https://github.com/StoneSteel27/pydantic-pick/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python Version"></a>
  <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/pydantic-v2-e92063" alt="Pydantic v2"></a>
  <a href="https://github.com/StoneSteel27/pydantic-pick/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>


# pydantic-pick

> Dynamically create subsets of Pydantic V2 models using `pick_model` or `omit_model`. Preserves validators, methods, and constraints.

This library provides two approaches for dynamically creating model subsets:

- **`pick_model`** - Keep only the fields you specify. Everything else is dropped.
- **`omit_model`** - Remove only the fields you specify. Everything else is kept.

Both functions preserve your `Field` constraints, `@field_validator` logic, `@computed_field` properties, custom methods, `ClassVar` attributes, and `model_config` settings. They handle nested models and standard library types: `List`, `Dict`, `Tuple`, `Set`, `Union`, `Optional`, and `Annotated`.

## Installation

```bash
pip install pydantic-pick
```

**Note:** This library requires `pydantic >= 2.0.0` and Python 3.10+. It is deeply tied to Pydantic V2's core architecture and is not compatible with Pydantic V1.

## Quick Start

Both functions take a base model, a tuple of dot-notation paths, and a name for the new class.

### Using `pick_model`

Specify which fields to keep. Everything else is dropped.

```python
from pydantic import BaseModel, Field, field_validator
from pydantic_pick import pick_model

class DBUser(BaseModel):
    id: int = Field(..., ge=1)
    username: str
    password_hash: str
    email: str
    is_active: bool = True

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str):
        if "admin" in v.lower():
            raise ValueError("Reserved username")
        return v

# Keep only 'id' and 'username', drop everything else
PublicUser = pick_model(DBUser, ("id", "username"), "PublicUser")

user = PublicUser(id=10, username="alice")
print(user.model_dump())
# {'id': 10, 'username': 'alice'}

# Validators and constraints still work
PublicUser(id=-5, username="bob")      # Fails: id must be >= 1
PublicUser(id=1, username="admin123")  # Fails: Reserved username
```

### Using `omit_model`

Specify which fields to remove. Everything else stays.

```python
from pydantic_pick import omit_model

# Remove 'password_hash' and 'email', keep everything else
PublicUser = omit_model(DBUser, ("password_hash", "email"), "PublicUser")

user = PublicUser(id=10, username="alice", is_active=True)
print(user.model_dump())
# {'id': 10, 'username': 'alice', 'is_active': True}

# Same validator and constraint behavior
PublicUser(id=-5, username="bob")      # Fails: id must be >= 1
PublicUser(id=1, username="admin123")  # Fails: Reserved username
```

Both approaches preserve your `Field` constraints, validators, and methods.

## Deep Nesting & Complex Types

Both functions handle nested models and standard library generics: `List`, `Dict`, `Tuple`, `Set`, `Union`, `Optional`, `Annotated`.

```python
class Profile(BaseModel):
    avatar_url: str
    billing_secret: str

class Account(BaseModel):
    user_id: int
    profiles: list[Profile]
```

**With `pick_model`** - specify what to keep:
```python
paths = ("user_id", "profiles.avatar_url")
PublicAccount = pick_model(Account, paths, "PublicAccount")
# Keeps user_id and avatar_url. Drops everything else including billing_secret.
```

**With `omit_model`** - specify what to remove:
```python
paths = ("profiles.billing_secret",)
PublicAccount = omit_model(Account, paths, "PublicAccount")
# Keeps everything except billing_secret.
```

## Advanced Use Case: LLM Context Compression

When building autonomous AI agents, tool responses (like executing a Python script or scraping a webpage) can return thousands of lines of raw output. You can use either function to compress this before sending to the LLM.

**With `pick_model`** - keep only what you need:
```python
from pydantic import BaseModel
from pydantic_pick import pick_model

class ToolResponse(BaseModel):
    tool_response: str  # Heavy output
    tool_close_instructions: str = "Analyze the tool_response above."
    execution_time: float
    exit_code: int

CompressedResponse = pick_model(
    ToolResponse, 
    ("tool_close_instructions", "execution_time"),  # Keep only these
    "CompressedResponse"
)
```

**With `omit_model`** - remove what you don't need:
```python
from pydantic_pick import omit_model

CompressedResponse = omit_model(
    ToolResponse, 
    ("tool_response",),  # Only drop the heavy field
    "CompressedResponse"
)
```

**Performance Tip:** Both functions use `functools.lru_cache`. Generating a model dynamically takes a few milliseconds, but subsequent calls requesting the exact same subset of the same model return instantly from memory. It is completely safe to use inside fast-paced API endpoints or intensive AI agent loops.

## What Survives Extraction?

Unlike naive `create_model` wrappers, this library actively preserves your business logic:
- ✅ **Field Constraints:** Everything inside `Field(...)` (like `ge`, `max_length`, `alias`).
- ✅ **Field Validators:** `@field_validator` logic is preserved (as long as the fields it targets were not omitted).
- ✅ **Computed Fields:** `@computed_field` properties are safely carried over.
- ✅ **Methods:** Custom instance methods, `@classmethod`, `@staticmethod`, and custom wrappers.
- ✅ **ClassVars:** `typing.ClassVar` attributes are safely mapped.
- ✅ **Config:** Your `model_config` (like `frozen=True` or `alias_generator`) is inherited.

---

## Intelligent Dependency Resolution (AST Parsing)

What happens if you have a `@computed_field` or a custom method that relies on a data field, but you omit that data field during extraction?

Instead of letting your application crash randomly at runtime with a cryptic Python error, `pydantic-pick` uses **Abstract Syntax Tree (AST) parsing** to peek inside your methods and wrappers. 

It maps exactly which `self` attributes your functions access. **If a method relies on a field that you omitted, `pydantic-pick` gracefully and silently omits the method as well!** This cascades, so if `method_b` relies on `method_a`, and `method_a` was dropped, `method_b` is safely dropped too.

### Clean Developer Experience Errors
If another developer on your team tries to call a method or field that was dynamically dropped, `pydantic-pick` intercepts it via a custom `__getattr__` and provides a clear error:

```python
PublicUser = pick_model(DBUser, ("id", "username"), "PublicUser")
user = PublicUser(id=1, username="alice")

user.check_password("secret")
```
**Output:**
```text
AttributeError: 'PublicUser' object has no attribute 'check_password'.
-> This field/method was intentionally omitted by pydantic-pick during extraction.
```

## Function Reference

```python
from pydantic_pick import pick_model, omit_model

# Keep only specified fields
pick_model(
    base: Type[BaseModel],      # Your original model class
    paths: tuple[str, ...],     # Fields to keep (dot-notation for nested)
    name: str                   # Name for the new model class
) -> Type[BaseModel]

# Remove specified fields, keep the rest
omit_model(
    base: Type[BaseModel],      # Your original model class
    paths: tuple[str, ...],     # Fields to remove (dot-notation for nested)
    name: str                   # Name for the new model class
) -> Type[BaseModel]
```

The `paths` parameter uses dot-notation for nested fields (e.g., `"profile.settings.theme"`).

## Truthful Limitations & Quirks

Because dynamic AST generation and Pydantic's Rust-based core have strict boundaries, there are a few edge cases this library **does not** currently handle. Be aware of these before using it in production:

**Warning:** Both `@model_validator` and `@model_serializer` are intentionally ignored during extraction. Because `mode="before"` model validators check dictionary state rather than `self.attribute` state, our AST parser cannot reliably map their dependencies. Copying them to a subset class where fields might be missing would cause fatal dictionary/Attribute errors at runtime, so `pydantic-pick` safely drops them.

1. **Forward References:** If you use string-based forward references for circular imports (e.g., `leader: "User"`), the extraction engine cannot peek inside the string to extract nested fields.
2. **Private Attributes:** `PrivateAttr()` definitions are currently lost during extraction.
3. **Field Aliases in Paths:** When defining your include paths, you must use the actual internal Python variable name, not the Pydantic alias. (e.g., Use `"first_name"`, not `"firstName"`).
4. **Sets and `model_dump`:** If you extract a model containing a `Set[NestedModel]`, remember that Pydantic V2 requires you to use `model_dump(mode="json")` to serialize sets. Standard `model_dump()` will throw a standard Python `TypeError: unhashable type: 'dict'`.
5. **Generic Models:** Dynamically creating a subset of a `Generic[T]` model results in a standard model; it will lose its generic subscriptable properties.

## Links

- **GitHub**: https://github.com/StoneSteel27/pydantic-pick
- **Issues**: https://github.com/StoneSteel27/pydantic-pick/issues

## License
MIT License