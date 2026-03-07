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

> Dynamically extract and subset Pydantic V2 models using dot-notation, while preserving your validators, methods, and constraints.

In modern API development (especially with FastAPI) and AI Agent frameworks, it's common to have a "fat" data model that contains heavy internal data (like `password_hash` or massive `tool_responses`) and a "thin" model for JSON responses or LLM context windows. Manually writing and maintaining dozens of subset models is tedious.

While some existing libraries allow you to subset Pydantic models, **they usually drop all your custom validation logic and methods** when generating the new class. 

`pydantic-pick` is different. It recursively rebuilds your models while safely copying over your `@field_validator`s, `@computed_field`s, `Field` constraints, and user-defined methods.

## Installation

```bash
pip install pydantic-pick
```

**Note:** This library requires `pydantic >= 2.0.0` and Python 3.10+. It is deeply tied to Pydantic V2's core architecture and is not compatible with Pydantic V1.

## Quick Start

Pass your base model, a tuple of dot-notation paths to keep, and the name for the new dynamically generated class.

```python
from pydantic import BaseModel, Field, field_validator
from pydantic_pick import create_subset

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

# Create a subset keeping only 'id' and 'username'
PublicUser = create_subset(DBUser, ("id", "username"), "PublicUser")

# The new model works exactly as expected
user = PublicUser(id=10, username="alice")
print(user.model_dump())
# {'id': 10, 'username': 'alice'}

# AND your validators/constraints survived!
PublicUser(id=-5, username="bob")      # Fails: id must be >= 1
PublicUser(id=1, username="admin123")  # Fails: Reserved username
```

## Deep Nesting & Complex Types

`pydantic-pick` handles deeply nested models and complex standard library types natively. You can drill into models wrapped in `List`, `Dict`, `Tuple`, `Set`, `Union`, `Optional`, and `Annotated`.

```python
class Profile(BaseModel):
    avatar_url: str
    billing_secret: str

class Account(BaseModel):
    user_id: int
    # Works perfectly through Lists, Dicts, Unions, and Optionals!
    profiles: list[Profile] 

# Use dot-notation to drill down into the nested lists
paths = (
    "user_id",
    "profiles.avatar_url"  # Keeps the avatar, drops the billing_secret
)

PublicAccount = create_subset(Account, paths, "PublicAccount")
```

## Advanced Use Case: LLM Context Compression

When building autonomous AI agents, tool responses (like executing a Python script or scraping a webpage) can return thousands of lines of raw output. Appending this directly to your LLM's conversation history quickly exhausts the context window and skyrockets API costs.

You can use `pydantic-pick` to maintain a "Fat History" for your database, but dynamically generate a "Thin History" before calling the LLM.

```python
from pydantic import BaseModel
from pydantic_pick import create_subset

# 1. Your "Fat" schema that gets saved to your database
class ToolResponse(BaseModel):
    tool_response: str  # Might contain 10,000 tokens of raw terminal output
    tool_close_instructions: str = "Analyze the tool_response above. Trigger ToolComplete next."

# 2. Dynamically drop the heavy data, but keep the structural instructions
CompressedToolResponse = create_subset(
    ToolResponse, 
    ("tool_close_instructions",), # Keeps instructions, DROPS 'tool_response'
    "CompressedToolResponse"
)

# Now, when you build your LLM prompt payload:
history_for_llm = []
for event in database_history:
    if isinstance(event, ToolResponse):
        # Convert to thin model, saving thousands of tokens instantly
        thin_event = CompressedToolResponse(**event.model_dump())
        history_for_llm.append(thin_event.model_dump_json())
```

**💡 Performance Tip:** The `create_subset` function uses `functools.lru_cache`. Generating a model dynamically takes a few milliseconds, but subsequent calls requesting the exact same subset of the same model return instantly from memory. It is completely safe to use inside fast-paced API endpoints or intensive AI agent loops.

## What Survives Extraction?

Unlike naive `create_model` wrappers, this library actively preserves your business logic:
- ✅ **Field Constraints:** Everything inside `Field(...)` (like `ge`, `max_length`, `alias`).
- ✅ **Field Validators:** `@field_validator` logic is preserved (as long as the fields it targets were not omitted).
- ✅ **Computed Fields:** `@computed_field` properties are carried over and will show up in `.model_dump()`.
- ✅ **Methods:** Custom instance methods, `@classmethod`, `@staticmethod`, and custom wrappers.
- ✅ **ClassVars:** `typing.ClassVar` attributes are safely mapped.
- ✅ **Config:** Your `model_config` (like `frozen=True` or `alias_generator`) is inherited.

## Truthful Limitations & Quirks

Because dynamic AST generation and Pydantic's Rust-based core have strict boundaries, there are a few edge cases this library **does not** currently handle. Be aware of these before using it in production:

**⚠️ Warning:** Model Validators are Dropped - Both `@model_validator` and `@model_serializer` are ignored during extraction. Because model validators check the entire class state (e.g., checking if `password == confirm_password`), copying them to a subset class where fields might be missing would cause fatal `AttributeError`s at runtime.

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
