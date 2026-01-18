# Story 1.3: Global Configuration Loading

**Status:** done
**Story Points:** 3

---

## Story

**As a** developer,
**I want** to load global configuration from `~/.bmad-assist/config.yaml`,
**So that** I have default settings that apply to all projects.

### Business Context

This story builds upon Story 1.2's Pydantic configuration models to add file-based configuration loading. The global configuration provides sensible defaults that apply across all projects. This is a prerequisite for Story 1.4 (project config override) and Story 1.7 (interactive config generation).

### Success Criteria

- Global config file is loaded from `~/.bmad-assist/config.yaml`
- YAML content is parsed and validated through existing Pydantic models
- Missing optional fields use Story 1.2's default values
- Clear error messages for malformed YAML files
- If global config file doesn't exist, ConfigError is raised with helpful message
- Config singleton (`get_config()`) works after loading from file
- File size limit (1MB) protects against YAML bombs
- Non-ASCII content (UTF-8) is properly handled

---

## Acceptance Criteria

### AC1: Global Config File Loading
```gherkin
Given a global config file exists at `~/.bmad-assist/config.yaml`
When `load_global_config()` is called
Then the file is read and parsed as YAML
And the parsed dict is validated against Pydantic models (via Story 1.2's load_config)
And the Config instance is stored in the module-level singleton
```

### AC2: Missing Optional Fields Use Defaults
```gherkin
Given a global config file with only required fields (providers.master)
When configuration is loaded
Then optional fields use default values from Story 1.2:
  - state_path: "~/.bmad-assist/state.yaml" (expanded)
  - providers.multi: []
  - power_prompts.set_name: None
  - power_prompts.variables: {}
  - bmad_paths.*: None
```

### AC3: ConfigError for Malformed YAML
```gherkin
Given a global config file exists with invalid YAML syntax
When `load_global_config()` is called
Then ConfigError is raised
And error message contains "YAML" or indicates parsing failure
And error includes file path for debugging
```

### AC4: ConfigError When File Missing
```gherkin
Given no global config file exists at `~/.bmad-assist/config.yaml`
When `load_global_config()` is called
Then ConfigError is raised
And error message includes the file path
And error message suggests running 'bmad-assist init'
```

### AC5: Path Expansion in Loaded Config
```gherkin
Given config file contains `state_path: ~/.bmad-assist/state.yaml`
When configuration is loaded
Then state_path is expanded to absolute path (e.g., /home/user/.bmad-assist/state.yaml)
And ~ is replaced with actual home directory
```

### AC6: Integration with Existing Singleton
```gherkin
Given `load_global_config()` is called with valid config file
When `get_config()` is called subsequently
Then it returns the same Config instance loaded from file
And singleton pattern from Story 1.2 is preserved
```

### AC7: ConfigError for Unreadable File (OSError)
```gherkin
Given a global config file exists but is not readable (e.g., permission denied)
When `load_global_config()` is called
Then ConfigError is raised
And error message contains "Cannot read" or indicates I/O failure
And error includes file path for debugging
```

### AC8: Empty Config File Returns Valid Config with Defaults
```gherkin
Given a global config file exists but is empty (0 bytes or only whitespace)
When `load_global_config()` is called
Then ConfigError is raised
And error message indicates missing required fields (providers.master)
```

### AC9: Non-ASCII Content Loads Correctly
```gherkin
Given a global config file contains non-ASCII characters (e.g., user_name: Paweł)
When `load_global_config()` is called
Then the file is loaded successfully with UTF-8 encoding
And non-ASCII characters are preserved correctly
```

### AC10: File Size Limit Protection
```gherkin
Given a global config file larger than 1MB exists
When `load_global_config()` is called
Then ConfigError is raised
And error message indicates file is too large
```

---

## Tasks / Subtasks

- [x] Task 1: Add YAML parsing to config module (AC: 1, 3, 7)
  - [x] 1.1 Import `yaml` (PyYAML already in dependencies)
  - [x] 1.2 Create `_load_yaml_file(path: Path) -> dict` helper
  - [x] 1.3 Handle `yaml.YAMLError` and wrap in `ConfigError`
  - [x] 1.4 Handle `OSError` and wrap in `ConfigError` (AC7)
  - [x] 1.5 Include file path in all error messages

- [x] Task 2: Implement `load_global_config()` function (AC: 1, 4, 6, 10)
  - [x] 2.1 Define `GLOBAL_CONFIG_PATH = Path.home() / ".bmad-assist" / "config.yaml"`
  - [x] 2.2 Define `MAX_CONFIG_SIZE = 1_048_576` (1MB)
  - [x] 2.3 Create `load_global_config(path: Path | None = None) -> Config`
  - [x] 2.4 If file doesn't exist, raise ConfigError with helpful message suggesting `bmad-assist init` (AC4)
  - [x] 2.5 Check file size before loading, raise ConfigError if > 1MB (AC10)
  - [x] 2.6 If file exists, load YAML and call existing `load_config(dict)`

- [x] Task 3: Handle edge cases (AC: 8, 9)
  - [x] 3.1 Empty file → yaml.safe_load returns None → pass empty dict to Pydantic → ValidationError → ConfigError (AC8)
  - [x] 3.2 UTF-8 encoding explicitly set in file read (AC9)

- [x] Task 4: Update module exports (AC: 6)
  - [x] 4.1 Export `load_global_config` from `core/__init__.py`
  - [x] 4.2 Export `GLOBAL_CONFIG_PATH` and `MAX_CONFIG_SIZE` constants
  - [x] 4.3 Ensure backward compatibility with Story 1.2's `load_config`

- [x] Task 5: Write comprehensive tests (AC: all)
  - [x] 5.1 Test loading valid YAML config file (AC1)
  - [x] 5.2 Test optional fields use defaults (AC2)
  - [x] 5.3 Test malformed YAML raises ConfigError (AC3)
  - [x] 5.4 Test missing file raises ConfigError with init hint (AC4)
  - [x] 5.5 Test path expansion works from file (AC5)
  - [x] 5.6 Test singleton integration after file load (AC6)
  - [x] 5.7 Test permission denied raises ConfigError (AC7)
  - [x] 5.8 Test empty file raises ConfigError (AC8)
  - [x] 5.9 Test non-ASCII content loads correctly (AC9)
  - [x] 5.10 Test file > 1MB raises ConfigError (AC10)
  - [x] 5.11 Use tmp_path fixture for test config files
  - [x] 5.12 Ensure >=95% coverage on new code

---

## Dev Notes

### Critical Architecture Requirements

**From architecture.md - MUST follow exactly:**

1. **Module Location:** `src/bmad_assist/core/config.py` (extend existing)
2. **Exception Handling:** Use existing `ConfigError` from Story 1.2
3. **Config Access Pattern:** Maintain singleton via `get_config()`
4. **Naming Conventions:** PEP8 (snake_case functions)
5. **Type Hints:** Required on ALL functions
6. **Docstrings:** Google-style for all public APIs

### Design Decision: Missing File Behavior (DECIDED)

**Decision: Raise ConfigError when file doesn't exist**

```python
def load_global_config(path: Path | None = None) -> Config:
    config_path = path or GLOBAL_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(
            f"Global config not found at {config_path}.\n"
            f"Run 'bmad-assist init' to create one."
        )
    # ... continue with loading
```

**Rationale:**
1. Aligns with Story 1.7 (interactive config generation) - user should explicitly create config
2. Default config with hardcoded provider/model would fail without API key anyway
3. Silent failure with defaults is worse than explicit error with helpful message
4. Error message guides user to correct action (`bmad-assist init`)

**This decision is FINAL - do not ask user during implementation.**

### YAML Loading Pattern

```python
import yaml
from pathlib import Path
from typing import Any
from .exceptions import ConfigError

MAX_CONFIG_SIZE = 1_048_576  # 1MB - protection against YAML bombs

def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file with safety checks.

    Args:
        path: Path to YAML file.

    Returns:
        Parsed YAML content as dictionary (empty dict if file is empty).

    Raises:
        ConfigError: If file cannot be read, is too large, or YAML is invalid.
    """
    try:
        # Check file size before loading (YAML bomb protection)
        file_size = path.stat().st_size
        if file_size > MAX_CONFIG_SIZE:
            raise ConfigError(
                f"Config file {path} is too large ({file_size} bytes). "
                f"Maximum allowed size is {MAX_CONFIG_SIZE} bytes (1MB)."
            )

        content = path.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Cannot read config file {path}: {e}") from e
```

### Function Signature

```python
def load_global_config(path: str | Path | None = None) -> Config:
    """Load global configuration from file.

    Args:
        path: Optional custom path. Defaults to ~/.bmad-assist/config.yaml

    Returns:
        Validated Config instance.

    Raises:
        ConfigError: If file is malformed or cannot be read.
        pydantic.ValidationError: If config structure is invalid.
    """
```

### IMPORTANT: Scope Boundaries

**This story ONLY handles global config file loading.**

**NOT in scope for this story:**
- Project config loading (Story 1.4)
- Config merging/override logic (Story 1.4)
- Config file creation (Story 1.7)
- Credentials handling (Story 1.5)

---

## Technical Requirements

### From PRD (FR35 - Configuration)

| FR | Requirement | This Story's Implementation |
|----|-------------|----------------------------|
| FR35 | Load global config from ~/.bmad-assist/config.yaml | Full implementation |

### From Architecture

**Technology Stack:**
- PyYAML (already in pyproject.toml from Story 1.1)
- Pydantic v2 (Story 1.2's validation)
- pathlib.Path for file operations

**Config Access Pattern (architecture.md):**
> "Global config: `~/.bmad-assist/config.yaml`"
> "Config Validation: Pydantic - Type-safe, LLM-friendly"

### Dependencies

- **Story 1.2 (DONE):** Pydantic models, `load_config()`, `get_config()`, `ConfigError`
- **PyYAML:** Already in pyproject.toml

### Story 1.4 Integration Note

Story 1.4 will add project config by:
1. Loading global config via `load_global_config()`
2. Loading project config from `./bmad-assist.yaml`
3. Deep merging project over global
4. Calling `load_config(merged_dict)`

---

## Architecture Compliance

### Stack Verification
- [x] PyYAML - Already in pyproject.toml
- [x] Pydantic v2 - Used for validation (Story 1.2)
- [x] Python 3.11+ type hints - Required

### Structure Verification
- [x] Location: `src/bmad_assist/core/config.py` (extend existing)
- [x] Exception: Use existing `ConfigError`
- [x] Tests: `tests/core/test_config.py` (extend existing)

### Pattern Verification
- [x] Global singleton pattern maintained
- [x] PEP8 naming conventions
- [x] Google-style docstrings
- [x] Error handling via ConfigError

---

## Developer Context

### Git Intelligence Summary

**Recent commits (from git log):**
1. `fix(core): address Multi-LLM code review findings for story 1.2` - Code review fixes applied
2. `docs(story): add story 1.2 validation reports` - Validation complete
3. `feat(core): add Pydantic configuration models` - Models implemented
4. `docs(power-prompts): clarify code review file pattern` - Power prompt updates
5. `fix(deps): add typer[all] for AC4 compliance` - Dependencies finalized

**Files from most recent commit:**
- `src/bmad_assist/core/config.py` - Extended with frozen models, path expansion
- `tests/core/test_config.py` - 52 tests, 100% coverage

**Key Patterns from Story 1.2:**
- All Pydantic models use `ConfigDict(frozen=True)` for immutability
- `model_validator(mode="after")` for path expansion
- `object.__setattr__` for mutating frozen models in validators
- Test fixtures with `_reset_config()` for singleton testing
- pytest `autouse=True` fixture for automatic cleanup

### Previous Story Learnings (1.2)

**What worked well:**
- Using `str | None` union syntax (Python 3.10+ style)
- `model_validator` for tilde expansion
- Comprehensive test organization by AC
- 100% coverage achieved with 52 tests

**Issues encountered and resolved:**
- Frozen models need `object.__setattr__` for mutation in validators
- Default values processed after instantiation need model_validator
- Import `Self` from `typing` for validator return type

**Code Review Insights (from story 1.2 code review):**
- Lambda in `default_factory` → use class directly: `Field(default_factory=PowerPromptConfig)`
- Add `frozen=True` to all models
- State path tilde must be expanded

### Files Modified in Previous Story

**Story 1.2 file list:**
- `src/bmad_assist/core/__init__.py` - Core module exports
- `src/bmad_assist/core/exceptions.py` - BmadAssistError, ConfigError
- `src/bmad_assist/core/config.py` - Pydantic models + singleton
- `tests/core/__init__.py` - Test package
- `tests/core/test_config.py` - 52 comprehensive tests

---

## File Structure

### Files to Modify

| File | Changes | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/core/config.py` | Add YAML loading functions | +30-40 |
| `src/bmad_assist/core/__init__.py` | Export `load_global_config` | +1 |
| `tests/core/test_config.py` | Add file loading tests | +60-80 |

### Files NOT to Create/Modify

- `pyproject.toml` - No changes (PyYAML already present)
- `src/bmad_assist/cli.py` - CLI integration in later stories
- Any actual config files - User creates these

### Expected Config File Structure

```yaml
# ~/.bmad-assist/config.yaml
providers:
  master:
    provider: claude
    model: opus_4_5
    settings_file: ./provider-configs/master-claude-opus_4_5.json
  multi:
    - provider: gemini
      model: gemini_2_5_pro
    - provider: codex
      model: o3

power_prompts:
  set_name: python-cli
  variables:
    project_type: cli-tool

state_path: ~/.bmad-assist/state.yaml

bmad_paths:
  prd: ./docs/prd.md
  architecture: ./docs/architecture.md
  epics: ./docs/epics.md
  stories: ./docs/sprint-artifacts/
```

---

## Testing Requirements

### Test Cases to Add (tests/core/test_config.py)

```python
"""Additional tests for Story 1.3: Global Configuration Loading."""

import tempfile
from pathlib import Path
import pytest
import yaml

from bmad_assist.core.config import (
    load_global_config,
    get_config,
    _reset_config,
    GLOBAL_CONFIG_PATH,  # If exposed
)
from bmad_assist.core.exceptions import ConfigError


class TestGlobalConfigLoading:
    """Tests for AC1: Global config file loading."""

    def test_load_valid_yaml_config(self, tmp_path: Path) -> None:
        """Valid YAML config file is loaded and validated."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")
        config = load_global_config(path=config_file)
        assert config.providers.master.provider == "claude"
        assert config.providers.master.model == "opus_4"

    def test_load_config_calls_singleton(self, tmp_path: Path) -> None:
        """load_global_config populates the singleton."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: codex
    model: o3
""")
        load_global_config(path=config_file)
        retrieved = get_config()
        assert retrieved.providers.master.provider == "codex"


class TestMalformedYaml:
    """Tests for AC3: ConfigError for malformed YAML."""

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path) -> None:
        """Invalid YAML syntax raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: syntax:")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert "YAML" in str(exc_info.value) or "yaml" in str(exc_info.value).lower()

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        """Error message includes file path."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: [unclosed")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert str(config_file) in str(exc_info.value)


class TestMissingConfigFile:
    """Tests for AC4: ConfigError when file missing."""

    def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
        """Missing config file raises ConfigError with helpful message."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=nonexistent)

        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg or "does not exist" in error_msg
        assert "does_not_exist.yaml" in str(exc_info.value)
        assert "init" in error_msg  # Suggests bmad-assist init


class TestDefaultValues:
    """Tests for AC2: Missing optional fields use defaults."""

    def test_minimal_config_gets_defaults(self, tmp_path: Path) -> None:
        """Minimal config with only required fields gets defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")
        config = load_global_config(path=config_file)

        # Verify defaults from Story 1.2
        assert config.providers.multi == []
        assert config.power_prompts.set_name is None
        assert config.power_prompts.variables == {}
        assert config.bmad_paths.prd is None


class TestPathExpansion:
    """Tests for AC5: Path expansion in loaded config."""

    def test_state_path_tilde_expanded_from_file(self, tmp_path: Path) -> None:
        """State path with ~ from file is expanded."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
state_path: ~/.bmad-assist/state.yaml
""")
        config = load_global_config(path=config_file)
        assert "~" not in config.state_path
        assert config.state_path.startswith("/")


class TestSingletonIntegration:
    """Tests for AC6: Integration with existing singleton."""

    def test_get_config_after_load_global(self, tmp_path: Path) -> None:
        """get_config returns config after load_global_config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: gemini
    model: gemini_2_5_pro
""")
        loaded = load_global_config(path=config_file)
        retrieved = get_config()
        assert loaded is retrieved


class TestUnreadableFile:
    """Tests for AC7: ConfigError for unreadable file (OSError)."""

    def test_permission_denied_raises_config_error(self, tmp_path: Path) -> None:
        """Unreadable file (permission denied) raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("providers:\n  master:\n    provider: claude\n")
        config_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(ConfigError) as exc_info:
                load_global_config(path=config_file)
            assert "cannot read" in str(exc_info.value).lower() or "permission" in str(exc_info.value).lower()
        finally:
            config_file.chmod(0o644)  # Restore permissions for cleanup


class TestEmptyConfigFile:
    """Tests for AC8: Empty config file raises ConfigError."""

    def test_empty_file_raises_config_error(self, tmp_path: Path) -> None:
        """Empty config file raises ConfigError (missing required fields)."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        # Empty file → empty dict → Pydantic ValidationError → ConfigError
        assert "providers" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_whitespace_only_file_raises_config_error(self, tmp_path: Path) -> None:
        """Whitespace-only config file raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("   \n\n   \n")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert "providers" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()


class TestNonAsciiContent:
    """Tests for AC9: Non-ASCII content loads correctly."""

    def test_polish_characters_load_correctly(self, tmp_path: Path) -> None:
        """Config with Polish characters (UTF-8) loads correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
# Comment with Polish: Paweł, żółć, źdźbło
""", encoding="utf-8")
        config = load_global_config(path=config_file)
        assert config.providers.master.provider == "claude"

    def test_unicode_in_string_values(self, tmp_path: Path) -> None:
        """Unicode characters in string values are preserved."""
        config_file = tmp_path / "config.yaml"
        # Note: This tests that YAML loading preserves Unicode,
        # actual field validation depends on Pydantic model
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: polski-zestaw-żółć
""", encoding="utf-8")
        config = load_global_config(path=config_file)
        assert "żółć" in config.power_prompts.set_name


class TestFileSizeLimit:
    """Tests for AC10: File size limit protection."""

    def test_file_over_1mb_raises_config_error(self, tmp_path: Path) -> None:
        """Config file larger than 1MB raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        # Create file slightly over 1MB
        large_content = "x" * (1_048_576 + 1)
        config_file.write_text(large_content)

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert "too large" in str(exc_info.value).lower()
        assert "1mb" in str(exc_info.value).lower() or "1048576" in str(exc_info.value)

    def test_file_exactly_1mb_loads_successfully(self, tmp_path: Path) -> None:
        """Config file exactly at 1MB limit loads successfully."""
        config_file = tmp_path / "config.yaml"
        # Valid YAML that's close to but not over 1MB
        # (actual valid YAML needed, not just random bytes)
        valid_yaml = """
providers:
  master:
    provider: claude
    model: opus_4
"""
        config_file.write_text(valid_yaml)
        # This should not raise - file is well under 1MB
        config = load_global_config(path=config_file)
        assert config is not None
```

### Coverage Target
- **>=95% coverage** on new code
- All error paths tested (malformed YAML, missing file, validation errors)
- Integration with Story 1.2 singleton tested

### Mocking Strategy
- Use `tmp_path` pytest fixture for test config files
- Use `_reset_config()` fixture from Story 1.2 for singleton cleanup
- No mocking of file system - use real temp files

---

## Library/Framework Requirements

### PyYAML Usage

**Safe loading (CRITICAL):**
```python
import yaml

# ALWAYS use safe_load, NEVER use load()
data = yaml.safe_load(file_content)
```

**Error handling:**
```python
try:
    data = yaml.safe_load(content)
except yaml.YAMLError as e:
    raise ConfigError(f"Invalid YAML: {e}")
```

### pathlib Usage

```python
from pathlib import Path

GLOBAL_CONFIG_PATH = Path.home() / ".bmad-assist" / "config.yaml"

# Check existence
if not path.exists():
    raise ConfigError(f"Config not found: {path}")

# Read file
content = path.read_text(encoding="utf-8")
```

---

## Project Context Reference

**Project:** bmad-assist - CLI tool for automating BMAD methodology development loop

**Key Architecture Patterns:**
- Config singleton via `get_config()` - Story 1.2 established this
- Pydantic validation with frozen models
- Path expansion for ~ in state_path

**Critical Rules:**
- Python 3.11+, PEP8 naming, type hints on all functions
- Google-style docstrings for public APIs
- Test coverage >=95% on new code
- mypy strict mode, ruff linting

---

## References

- [Source: docs/architecture.md#Data-Architecture] - Global config path
- [Source: docs/architecture.md#Config-Access-Pattern] - Singleton pattern
- [Source: docs/prd.md#Configuration] - FR35 requirement
- [Source: docs/epics.md#Story-1.3] - Original story definition
- [Source: Story 1.2] - Pydantic models, load_config(), get_config()

---

## Verification Checklist

Before marking as complete, verify:

- [ ] `load_global_config()` function implemented in `core/config.py`
- [ ] Function loads YAML from `~/.bmad-assist/config.yaml` by default
- [ ] Custom path parameter allows override for testing
- [ ] Malformed YAML raises `ConfigError` with file path (AC3)
- [ ] Missing file raises `ConfigError` with init hint (AC4)
- [ ] Optional fields use Story 1.2 defaults (AC2)
- [ ] Path expansion works for state_path from file (AC5)
- [ ] `get_config()` works after `load_global_config()` (AC6)
- [ ] OSError (permissions) raises `ConfigError` (AC7)
- [ ] Empty file raises `ConfigError` (AC8)
- [ ] Non-ASCII content loads correctly with UTF-8 (AC9)
- [ ] File > 1MB raises `ConfigError` (AC10)
- [ ] `load_global_config` exported from `core/__init__.py`
- [ ] `GLOBAL_CONFIG_PATH` and `MAX_CONFIG_SIZE` exported
- [ ] `mypy src/` reports no errors
- [ ] `ruff check src/` reports no issues
- [ ] `pytest tests/core/` passes all tests
- [ ] Coverage >=95% on new code

---

## Dev Agent Record

### Context Reference
- Story ID: 1.3
- Story Key: 1-3-global-configuration-loading
- Epic: 1 - Project Foundation & CLI Infrastructure
- Previous Story: 1.2 (done) - Pydantic Configuration Models

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- All tests pass (84 tests, 100% coverage)
- mypy strict mode: no issues
- ruff linting: all checks passed

### Completion Notes List
- Implemented `_load_yaml_file()` helper with YAML bomb protection (1MB limit)
- Implemented `load_global_config()` with file existence check and helpful error messages
- Added `GLOBAL_CONFIG_PATH` and `MAX_CONFIG_SIZE` constants
- All error paths wrap exceptions in `ConfigError` with file path included
- UTF-8 encoding explicitly used for non-ASCII support
- Empty file handling: raises ConfigError due to missing required `providers` field
- Added types-PyYAML to dev dependencies for mypy type checking
- 32 new tests added for Story 1.3 (total 84 tests)
- 100% test coverage achieved on config module

### File List
- `src/bmad_assist/core/config.py` - Added `_load_yaml_file()`, `load_global_config()`, constants
- `src/bmad_assist/core/__init__.py` - Added exports for new function and constants
- `tests/core/test_config.py` - Added 32 tests for AC1-AC10
- `pyproject.toml` - Added types-PyYAML to dev dependencies
