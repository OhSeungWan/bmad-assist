# Story 1.2: Pydantic Configuration Models

**Status:** Ready for Review
**Story Points:** 3

---

## Story

**As a** developer,
**I want** type-safe configuration models with validation,
**So that** configuration errors are caught early with clear error messages.

### Business Context

This story establishes the configuration foundation for bmad-assist. All subsequent stories (1.3, 1.4, 1.5, 1.6, 1.7) depend on these Pydantic models for configuration loading, validation, and override mechanics. Without type-safe models, configuration errors would surface at runtime in hard-to-debug ways.

### Success Criteria

- Pydantic models validate configuration structure and types
- Invalid configurations produce clear, actionable error messages
- Models support nested structures for providers and power-prompts
- Config singleton pattern enables consistent access across modules
- All fields have explicit type hints and defaults where appropriate

---

## Acceptance Criteria

### AC1: Config Model Exists with Required Sections
```gherkin
Given core/config.py exists
When Config model is instantiated
Then it contains sections for:
  - providers (nested ProviderConfig model)
  - power_prompts (nested PowerPromptConfig model)
  - state_path (str with default)
  - bmad_paths (nested BmadPathsConfig model)
And all fields have type hints
And default values are provided where appropriate
```

### AC2: Provider Configuration Model
```gherkin
Given ProviderConfig model exists
When provider configuration is validated
Then it contains:
  - master: MasterProviderConfig (required)
  - multi: list[MultiProviderConfig] (default empty list)
And MasterProviderConfig contains:
  - provider: str (e.g., "claude", "codex", "gemini")
  - model: str (e.g., "opus_4", "sonnet_4")
  - settings_file: str | None (path to JSON settings)
And MultiProviderConfig has same structure as MasterProviderConfig
```

### AC3: Invalid Configuration Raises ValidationError
```gherkin
Given an invalid configuration dictionary
When Config.model_validate(invalid_dict) is called
Then pydantic.ValidationError is raised
And error message contains:
  - field name that failed validation
  - expected type or constraint
  - actual value received
And error is human-readable and actionable
```

### AC4: Nested Model Validation
```gherkin
Given Config model with nested ProviderConfig
When invalid nested value is provided (e.g., providers.master.model = 123)
Then ValidationError is raised
And error path includes full dotted path (e.g., "providers.master.model")
And error message indicates type mismatch (expected str, got int)
```

### AC5: Default Values Work Correctly
```gherkin
Given minimal valid configuration (only required fields)
When Config is instantiated
Then optional fields have their default values:
  - state_path: "~/.bmad-assist/state.yaml"
  - providers.multi: []
And model is valid and usable
```

### AC6: Config Singleton Pattern
```gherkin
Given config.py contains get_config() function
When get_config() is called before load_config()
Then ConfigError is raised with message "Config not loaded"
And when load_config(config_data: dict) is called with valid config dict
Then config is validated via Pydantic and stored in module-level _config
And subsequent get_config() calls return the same Config instance
```

**Note:** In Story 1.2, `load_config()` accepts a `dict` parameter. File path handling and YAML loading will be added in Story 1.3, which will wrap this function.

---

## Tasks / Subtasks

- [x] Task 1: Create core module structure (AC: 1, 6)
  - [x] 1.1 Create `src/bmad_assist/core/__init__.py`
  - [x] 1.2 Create `src/bmad_assist/core/exceptions.py` with custom exception hierarchy
  - [x] 1.3 Create `src/bmad_assist/core/config.py` with Config model

- [x] Task 2: Implement Pydantic models (AC: 1, 2, 5)
  - [x] 2.1 Create `MasterProviderConfig` model with provider, model, settings_file fields
  - [x] 2.2 Create `MultiProviderConfig` model (same structure as Master)
  - [x] 2.3 Create `ProviderConfig` model with master and multi fields
  - [x] 2.4 Create `PowerPromptConfig` model with set_name and variables fields
  - [x] 2.5 Create `BmadPathsConfig` model with prd, architecture, epics, stories fields
  - [x] 2.6 Create main `Config` model composing all nested models

- [x] Task 3: Implement config singleton (AC: 6)
  - [x] 3.1 Add module-level `_config: Config | None = None`
  - [x] 3.2 Implement `load_config(config_data: dict) -> Config` function (validates dict with Pydantic)
  - [x] 3.3 Implement `get_config()` function with ConfigError guard
  - [x] 3.4 Add `_reset_config()` test helper for singleton testing

- [x] Task 4: Add validation error handling (AC: 3, 4)
  - [x] 4.1 Ensure ValidationError contains field paths
  - [x] 4.2 Add ConfigError for custom config-related errors
  - [x] 4.3 Write docstrings for all public classes and functions

- [x] Task 5: Write comprehensive tests (AC: all)
  - [x] 5.1 Create `tests/core/__init__.py`
  - [x] 5.2 Create `tests/core/test_config.py` with unit tests
  - [x] 5.3 Test valid configurations
  - [x] 5.4 Test invalid configurations and error messages
  - [x] 5.5 Test nested validation error paths
  - [x] 5.6 Test singleton pattern behavior
  - [x] 5.7 Test default values
  - [x] 5.8 Ensure >=95% coverage on new code

---

## Dev Notes

### Critical Architecture Requirements

**From architecture.md - MUST follow exactly:**

1. **Module Location:** `src/bmad_assist/core/config.py`
2. **Exception Hierarchy:** All custom exceptions inherit from `BmadAssistError`
3. **Config Access Pattern:** Global singleton via `get_config()`
4. **Naming Conventions:** PEP8 (snake_case functions, PascalCase classes)
5. **Type Hints:** Required on ALL functions and class attributes
6. **Docstrings:** Google-style for all public APIs

### Exception Hierarchy to Implement

```python
# core/exceptions.py
class BmadAssistError(Exception):
    """Base exception for all bmad-assist errors."""
    pass

class ConfigError(BmadAssistError):
    """Configuration loading or validation error."""
    pass
```

### Config Model Structure Reference

```python
# core/config.py - Target structure
from pydantic import BaseModel, Field
from pathlib import Path

class MasterProviderConfig(BaseModel):
    """Configuration for Master LLM provider."""
    provider: str = Field(..., description="Provider name: claude, codex, gemini")
    model: str = Field(..., description="Model identifier: opus_4, sonnet_4, etc.")
    settings_file: str | None = Field(None, description="Path to provider settings JSON")

class MultiProviderConfig(BaseModel):
    """Configuration for Multi LLM validator."""
    provider: str
    model: str
    settings_file: str | None = None

class ProviderConfig(BaseModel):
    """Provider configuration section."""
    master: MasterProviderConfig
    multi: list[MultiProviderConfig] = Field(default_factory=list)

class PowerPromptConfig(BaseModel):
    """Power-prompt configuration section."""
    set_name: str | None = Field(None, description="Name of power-prompt set to use")
    variables: dict[str, str] = Field(default_factory=dict)

class BmadPathsConfig(BaseModel):
    """Paths to BMAD documentation files."""
    prd: str | None = None
    architecture: str | None = None
    epics: str | None = None
    stories: str | None = None

class Config(BaseModel):
    """Main bmad-assist configuration model."""
    providers: ProviderConfig
    power_prompts: PowerPromptConfig = Field(default_factory=PowerPromptConfig)
    state_path: str = Field(default="~/.bmad-assist/state.yaml")
    bmad_paths: BmadPathsConfig = Field(default_factory=BmadPathsConfig)
```

### Singleton Pattern Reference

```python
from typing import Any
from .exceptions import ConfigError

_config: Config | None = None

def load_config(config_data: dict[str, Any]) -> Config:
    """Load and validate configuration from a dictionary.

    This function validates the configuration dictionary using Pydantic models
    and stores the result in a module-level singleton. File loading (YAML)
    will be added in Story 1.3, which will call this function after parsing.

    Args:
        config_data: Configuration dictionary to validate.

    Returns:
        Validated Config instance.

    Raises:
        pydantic.ValidationError: If configuration is invalid.
        ConfigError: If config_data is not a dict.
    """
    global _config
    if not isinstance(config_data, dict):
        raise ConfigError(f"config_data must be a dict, got {type(config_data).__name__}")
    _config = Config.model_validate(config_data)
    return _config

def get_config() -> Config:
    """Get the loaded configuration singleton.

    Returns:
        The loaded Config instance.

    Raises:
        ConfigError: If config has not been loaded yet.
    """
    if _config is None:
        raise ConfigError("Config not loaded. Call load_config() first.")
    return _config

def _reset_config() -> None:
    """Reset config singleton for testing purposes only."""
    global _config
    _config = None
```

### IMPORTANT: Scope Boundaries

**This story ONLY creates Pydantic models and singleton pattern.**

**NOT in scope for this story:**
- YAML file loading (Story 1.3)
- Config merging/override logic (Story 1.4)
- Credentials handling (Story 1.5)
- CLI config questionnaire (Story 1.7)

The `load_config()` function should accept a `dict` and validate it with Pydantic. Actual YAML loading comes in Story 1.3.

---

## Technical Requirements

### From PRD (FR35-38 - Configuration Domain)

| FR | Requirement | This Story's Contribution |
|----|-------------|---------------------------|
| FR35 | Load global config from ~/.bmad-assist/config.yaml | Models only - loading in 1.3 |
| FR36 | Load project config from ./bmad-assist.yaml | Models only - loading in 1.3 |
| FR37 | Project config can override global | Models support merging - logic in 1.4 |
| FR38 | Generate config via questionnaire | Models define structure - UI in 1.7 |

### From Architecture

**Technology Stack:**
- Pydantic v2.0+ (already in dependencies from Story 1.1)
- Python 3.11+ type hints

**Config Validation Pattern (architecture.md):**
> "Config Validation: Pydantic - Type-safe, LLM-friendly"

**Config Access Pattern (architecture.md section "Config Access Pattern"):**
> "Global singleton via get_config() from any module, never load config directly"

### Dependencies

This story has NO new dependencies - Pydantic v2 is already in pyproject.toml from Story 1.1.

**Story 1.3 Integration Note:** Story 1.3 will add file-based config loading by:
1. Loading YAML files from global and project paths
2. Merging the configurations
3. Calling `load_config(merged_dict)` from this story
This preserves the clean separation where Story 1.2 handles validation only.

---

## Architecture Compliance

### Stack Verification
- [x] Pydantic v2.0+ - Already in pyproject.toml
- [x] Python 3.11+ - Already specified in requires-python
- [x] Type hints on all functions - Required by architecture

### Structure Verification
- [x] Location: `src/bmad_assist/core/config.py`
- [x] Exception hierarchy in `src/bmad_assist/core/exceptions.py`
- [x] Module exports via `src/bmad_assist/core/__init__.py`

### Pattern Verification
- [x] Global singleton pattern for config access
- [x] PEP8 naming conventions
- [x] Google-style docstrings
- [x] Custom exceptions inherit from BmadAssistError

---

## Developer Context

### Git Intelligence Summary

**Recent commits:**
1. `fix(deps): add typer[all] for AC4 compliance` - Dependencies finalized
2. `feat(core): initialize Python project with pyproject.toml` - Project structure created
3. `docs(story): validate and fix story 1.1 acceptance criteria` - Story quality standards established
4. `docs(story): create story 1.1 project initialization context` - Story context patterns
5. `feat(power-prompts): add python-cli power-prompt set` - Power prompts configured

**Key Patterns from Story 1.1:**
- mypy strict mode enforced (`disallow_untyped_defs = true`)
- ruff linting with D100/D104/D203/D213 ignored
- pytest with `-v --tb=short` options
- 81% test coverage achieved (uncovered lines are `__main__` blocks)

**Files Modified in Previous Story:**
- `pyproject.toml` - Package configuration
- `src/bmad_assist/__init__.py` - Package version
- `src/bmad_assist/__main__.py` - Entry point
- `src/bmad_assist/cli.py` - Typer CLI
- `tests/test_cli.py` - CLI tests

### Previous Story Learnings (1.1)

**What worked well:**
- Using `str | None` union syntax (Python 3.10+ style, preferred by ruff)
- Comprehensive test coverage with `typer.testing.CliRunner`
- Adding tool configs to pyproject.toml instead of separate config files

**Issues encountered and resolved:**
- Typer "flattens" single-command apps - fixed with `@app.callback(invoke_without_command=True)`
- `Optional[str]` vs `str | None` - use modern union syntax per ruff preference
- Test expecting exit code 0 for no args, but Typer returns 2 - update test expectations

**Code Review Insights (from story 1.1 code review):**
- 21/22 criticisms were false positives (over-scoping)
- Keep implementation minimal - only what AC requires
- Don't add features not in acceptance criteria

---

## File Structure

### Files to Create

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/core/__init__.py` | Core module exports | ~15 |
| `src/bmad_assist/core/exceptions.py` | Custom exception hierarchy | ~25 |
| `src/bmad_assist/core/config.py` | Pydantic config models + singleton | ~120 |
| `tests/core/__init__.py` | Test package marker | ~1 |
| `tests/core/test_config.py` | Config model tests | ~150 |

### Files NOT to Create/Modify

- `pyproject.toml` - No changes needed (Pydantic already in deps)
- `src/bmad_assist/cli.py` - No changes in this story
- Any YAML config files - Not in scope

### Expected Project Structure After This Story

```
src/bmad_assist/
├── __init__.py          # Existing
├── __main__.py          # Existing
├── cli.py               # Existing
└── core/                # NEW
    ├── __init__.py      # NEW - exports Config, get_config, ConfigError
    ├── exceptions.py    # NEW - BmadAssistError, ConfigError
    └── config.py        # NEW - Pydantic models + singleton
tests/
├── __init__.py          # Existing
├── conftest.py          # Existing
├── test_cli.py          # Existing
└── core/                # NEW
    ├── __init__.py      # NEW
    └── test_config.py   # NEW
```

---

## Testing Requirements

### Unit Tests (tests/core/test_config.py)

```python
"""Tests for configuration models and singleton."""
import pytest
from pydantic import ValidationError

from bmad_assist.core.config import (
    Config,
    ProviderConfig,
    MasterProviderConfig,
    MultiProviderConfig,
    PowerPromptConfig,
    BmadPathsConfig,
    load_config,
    get_config,
    _reset_config,  # For testing only
)
from bmad_assist.core.exceptions import ConfigError


# === AC1: Config Model Structure ===

def test_config_has_required_sections():
    """Config model contains all required sections."""
    config = Config(
        providers=ProviderConfig(
            master=MasterProviderConfig(provider="claude", model="opus_4")
        )
    )
    assert hasattr(config, "providers")
    assert hasattr(config, "power_prompts")
    assert hasattr(config, "state_path")
    assert hasattr(config, "bmad_paths")


# === AC2: Provider Configuration ===

def test_master_provider_config_validates():
    """MasterProviderConfig validates required fields."""
    config = MasterProviderConfig(provider="claude", model="opus_4")
    assert config.provider == "claude"
    assert config.model == "opus_4"
    assert config.settings_file is None


def test_master_provider_with_settings_file():
    """MasterProviderConfig accepts settings_file."""
    config = MasterProviderConfig(
        provider="claude",
        model="opus_4",
        settings_file="./provider-configs/master.json"
    )
    assert config.settings_file == "./provider-configs/master.json"


def test_multi_provider_list():
    """ProviderConfig.multi accepts list of MultiProviderConfig."""
    config = ProviderConfig(
        master=MasterProviderConfig(provider="claude", model="opus_4"),
        multi=[
            MultiProviderConfig(provider="gemini", model="gemini_2_5_pro"),
            MultiProviderConfig(provider="codex", model="o3"),
        ]
    )
    assert len(config.multi) == 2


# === AC3: Invalid Configuration Raises ValidationError ===

def test_missing_required_field_raises_error():
    """Missing required field raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        MasterProviderConfig(provider="claude")  # Missing model
    assert "model" in str(exc_info.value)


def test_wrong_type_raises_error():
    """Wrong type raises ValidationError with clear message."""
    with pytest.raises(ValidationError) as exc_info:
        MasterProviderConfig(provider="claude", model=123)  # model should be str
    error_str = str(exc_info.value)
    assert "model" in error_str
    assert "str" in error_str.lower()


# === AC4: Nested Validation Error Paths ===

def test_nested_validation_error_path():
    """Nested validation error includes full path."""
    with pytest.raises(ValidationError) as exc_info:
        Config(
            providers=ProviderConfig(
                master={"provider": "claude", "model": 123}  # model should be str
            )
        )
    error_str = str(exc_info.value)
    assert "model" in error_str


# === AC5: Default Values ===

def test_default_state_path():
    """Default state_path is set correctly."""
    config = Config(
        providers=ProviderConfig(
            master=MasterProviderConfig(provider="claude", model="opus_4")
        )
    )
    assert config.state_path == "~/.bmad-assist/state.yaml"


def test_default_multi_is_empty_list():
    """Default multi providers is empty list."""
    config = ProviderConfig(
        master=MasterProviderConfig(provider="claude", model="opus_4")
    )
    assert config.multi == []


def test_default_power_prompts():
    """Default power_prompts is empty PowerPromptConfig."""
    config = Config(
        providers=ProviderConfig(
            master=MasterProviderConfig(provider="claude", model="opus_4")
        )
    )
    assert config.power_prompts.set_name is None
    assert config.power_prompts.variables == {}


# === AC6: Singleton Pattern ===

def test_get_config_before_load_raises_error():
    """get_config() before load_config() raises ConfigError."""
    _reset_config()  # Ensure clean state
    with pytest.raises(ConfigError) as exc_info:
        get_config()
    assert "Config not loaded" in str(exc_info.value)


def test_load_config_enables_get_config():
    """After load_config(), get_config() returns config."""
    _reset_config()
    config_dict = {
        "providers": {
            "master": {"provider": "claude", "model": "opus_4"}
        }
    }
    loaded = load_config(config_dict)
    retrieved = get_config()
    assert loaded is retrieved


def test_get_config_returns_same_instance():
    """Multiple get_config() calls return same instance."""
    _reset_config()
    config_dict = {
        "providers": {
            "master": {"provider": "claude", "model": "opus_4"}
        }
    }
    load_config(config_dict)
    first = get_config()
    second = get_config()
    assert first is second


def test_load_config_non_dict_raises_error():
    """load_config() with non-dict raises ConfigError."""
    _reset_config()
    with pytest.raises(ConfigError) as exc_info:
        load_config("not a dict")  # type: ignore
    assert "must be a dict" in str(exc_info.value)


def test_load_config_none_raises_error():
    """load_config() with None raises ConfigError."""
    _reset_config()
    with pytest.raises(ConfigError) as exc_info:
        load_config(None)  # type: ignore
    assert "must be a dict" in str(exc_info.value)
```

### Coverage Target
- **>=95% coverage** on all new code in `core/` module
- All Pydantic model branches tested
- All error paths tested

### Mocking Strategy
- No external mocking needed - models are self-contained
- Use `_reset_config()` helper for singleton testing
- Test ValidationError messages contain expected field names

---

## Library/Framework Requirements

### Pydantic v2 Specifics

**Model Definition (v2 style):**
```python
from pydantic import BaseModel, Field

class MyConfig(BaseModel):
    name: str = Field(..., description="Required field")
    optional: str | None = Field(None, description="Optional field")
    with_default: str = Field(default="value", description="Has default")
```

**Validation (v2 style):**
```python
# From dict
config = Config.model_validate({"key": "value"})

# Validation error handling
from pydantic import ValidationError
try:
    config = Config.model_validate(invalid_dict)
except ValidationError as e:
    print(e.errors())  # List of error dicts with 'loc', 'msg', 'type'
```

**Key v2 changes from v1:**
- `model_validate()` instead of `parse_obj()`
- `model_dump()` instead of `.dict()`
- Field definitions use `Field()` with keyword args
- No `Config` inner class - use `model_config` dict

---

## Project Context Reference

**Project:** bmad-assist - CLI tool for automating BMAD methodology development loop

**Key Architecture Patterns:**
- BaseProvider ABC for CLI adapters
- Config singleton via `get_config()`
- Atomic writes for state persistence
- Custom exceptions inherit from BmadAssistError

**Critical Rules:**
- Python 3.11+, PEP8 naming, type hints on all functions
- Google-style docstrings for public APIs
- Test coverage >=95% on new code
- mypy strict mode, ruff linting

---

## References

- [Source: docs/architecture.md#Config-Access-Pattern] - Singleton pattern
- [Source: docs/architecture.md#Data-Architecture] - Config structure
- [Source: docs/architecture.md#Implementation-Patterns] - Exception hierarchy
- [Source: docs/prd.md#Configuration] - FR35-38 requirements
- [Source: docs/epics.md#Story-1.2] - Original story definition

---

## Verification Checklist

Before marking as complete, verify:

- [ ] `src/bmad_assist/core/` directory created with __init__.py
- [ ] `src/bmad_assist/core/exceptions.py` with BmadAssistError, ConfigError
- [ ] `src/bmad_assist/core/config.py` with all Pydantic models
- [ ] Config model validates correctly with valid dict
- [ ] ValidationError raised for invalid configurations
- [ ] ValidationError messages contain field paths
- [ ] Default values work (state_path, multi=[], power_prompts)
- [ ] get_config() raises ConfigError before load_config()
- [ ] get_config() returns same instance after load_config()
- [ ] load_config() with non-dict raises ConfigError
- [ ] _reset_config() test helper implemented
- [ ] `mypy src/` reports no errors
- [ ] `ruff check src/` reports no issues
- [ ] `pytest tests/core/` passes all tests
- [ ] Coverage >=95% on core/ module

---

## Dev Agent Record

### Context Reference
- Story ID: 1.2
- Story Key: 1-2-pydantic-configuration-models
- Epic: 1 - Project Foundation & CLI Infrastructure
- Previous Story: 1.1 (done) - Project Initialization with pyproject.toml

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- mypy strict mode required pydantic.mypy plugin for proper type checking of Pydantic models
- Added pydantic-mypy plugin configuration to pyproject.toml

### Completion Notes List
- Implemented all 6 Pydantic models (MasterProviderConfig, MultiProviderConfig, ProviderConfig, PowerPromptConfig, BmadPathsConfig, Config)
- Implemented config singleton pattern with load_config(), get_config(), and _reset_config()
- Implemented custom exception hierarchy (BmadAssistError, ConfigError)
- All 43 tests passing with 100% code coverage on core module
- mypy strict mode passes with pydantic plugin
- ruff linting passes with Google-style docstrings

### File List
**New Files:**
- `src/bmad_assist/core/__init__.py` - Core module exports
- `src/bmad_assist/core/exceptions.py` - Custom exception hierarchy
- `src/bmad_assist/core/config.py` - Pydantic configuration models and singleton
- `tests/core/__init__.py` - Test package marker
- `tests/core/test_config.py` - 43 comprehensive tests

**Modified Files:**
- `pyproject.toml` - Added pydantic.mypy plugin configuration

### Change Log
- 2025-12-09: Implemented Story 1.2 - Pydantic Configuration Models
  - Created core module with config models and exceptions
  - 100% test coverage achieved (43 tests)
  - All acceptance criteria satisfied
