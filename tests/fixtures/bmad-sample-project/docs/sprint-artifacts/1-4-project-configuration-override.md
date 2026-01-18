# Story 1.4: Project Configuration Override

**Status:** Ready for Review
**Story Points:** 3

---

## Story

**As a** developer,
**I want** project-level config to override global settings,
**So that** each project can have custom CLI providers and power-prompts.

### Business Context

This story extends Story 1.3's global configuration loading with project-level configuration support. When working on multiple projects, each may require different LLM providers, models, or power-prompt sets. Project configuration allows customization without modifying global settings, following the principle of configuration hierarchy (global → project).

### Success Criteria

- Project config file `./bmad-assist.yaml` is discovered and loaded
- Project config values override global config values
- Non-overridden global values are preserved
- Deep merge is performed for nested structures (providers.multi, power_prompts.variables)
- If only project config exists (no global), it's used directly
- If only global config exists (no project), it's used directly
- If neither exists, ConfigError is raised
- Config singleton works correctly after merged loading

---

## Acceptance Criteria

### AC1: Project Config Overrides Global Values
```gherkin
Given global config exists with `timeout: 300`
And project config exists with `timeout: 600`
When configuration is loaded for the project
Then timeout value is 600 (project overrides global)
And non-overridden global values are preserved
```

### AC2: Deep Merge for Nested Structures
```gherkin
Given global config has:
  providers:
    master:
      provider: claude
      model: opus_4
    multi:
      - provider: gemini
        model: gemini_2_5_pro
And project config has:
  providers:
    master:
      model: sonnet_4  # Override just model, keep provider
When configuration is merged
Then providers.master.provider = "claude" (from global)
And providers.master.model = "sonnet_4" (from project)
And providers.multi list is preserved from global
```

### AC3: Project Config Only (No Global)
```gherkin
Given no global config file exists at ~/.bmad-assist/config.yaml
And project config exists at ./bmad-assist.yaml with valid configuration
When load_config_with_project(project_path) is called
Then project config is loaded successfully
And no error is raised about missing global config
```

### AC4: Global Config Only (No Project)
```gherkin
Given global config file exists at ~/.bmad-assist/config.yaml
And no project config exists at specified project path
When load_config_with_project(project_path) is called
Then global config is used
And no error is raised about missing project config
```

### AC5: Neither Config Exists
```gherkin
Given no global config file exists
And no project config file exists
When load_config_with_project(project_path) is called
Then ConfigError is raised
And error message suggests running 'bmad-assist init'
```

### AC6: Project Config Path Resolution
```gherkin
Given project_path = "/home/user/my-project"
When project config is searched for
Then it looks for "/home/user/my-project/bmad-assist.yaml"
And path is resolved from project_path parameter
```

### AC7: List Override (Not Merge) for providers.multi
```gherkin
Given global config has:
  providers:
    multi:
      - provider: gemini
        model: gemini_2_5_pro
And project config has:
  providers:
    multi:
      - provider: codex
        model: o3
When configuration is merged
Then providers.multi contains only [codex/o3] from project
And gemini/gemini_2_5_pro is NOT preserved (list replacement, not append)
```

### AC8: Dictionary Deep Merge for power_prompts.variables
```gherkin
Given global config has:
  power_prompts:
    set_name: python-cli
    variables:
      project_type: cli
      language: python
And project config has:
  power_prompts:
    variables:
      project_type: web-app  # Override
      framework: react       # Add new
When configuration is merged
Then power_prompts.set_name = "python-cli" (from global)
And power_prompts.variables.project_type = "web-app" (overridden)
And power_prompts.variables.language = "python" (preserved from global)
And power_prompts.variables.framework = "react" (added from project)
```

### AC9: Path Fields from Project Config
```gherkin
Given project config has:
  bmad_paths:
    prd: ./docs/prd.md
    architecture: ./docs/architecture.md
When configuration is loaded
Then paths are preserved as-is (not expanded)
And relative paths remain relative for later resolution
```

### AC10: Singleton Updated with Merged Config
```gherkin
Given load_config_with_project() is called successfully
When get_config() is called
Then it returns the merged Config instance
And singleton is updated with merged configuration
```

### AC11: ConfigError for Invalid Project YAML
```gherkin
Given global config exists and is valid
And project config exists at ./bmad-assist.yaml with invalid YAML syntax
When load_config_with_project(project_path) is called
Then ConfigError is raised
And error message contains "project config" or project config path
And error message distinguishes project config failure from global config failure
```

### AC12: Project Path Must Be Directory
```gherkin
Given project_path points to a file (not a directory)
When load_config_with_project(project_path) is called
Then ConfigError is raised
And error message indicates project_path must be a directory
```

---

## Tasks / Subtasks

- [x] Task 1: Create deep merge utility function (AC: 2, 7, 8)
  - [x] 1.1 Create `_deep_merge(base: dict, override: dict) -> dict` helper
  - [x] 1.2 Implement recursive merge for nested dicts
  - [x] 1.3 Lists are REPLACED (not merged) to match AC7 behavior
  - [x] 1.4 Add unit tests for merge edge cases

- [x] Task 2: Implement `load_config_with_project()` function (AC: 1, 3, 4, 5, 6, 10, 11, 12)
  - [x] 2.1 Create function signature: `load_config_with_project(project_path: str | Path | None = None) -> Config`
  - [x] 2.2 Default project_path to current working directory if None
  - [x] 2.3 Validate project_path is a directory (AC12)
  - [x] 2.4 Construct project config path: `{project_path}/bmad-assist.yaml`
  - [x] 2.5 Check global config existence (use GLOBAL_CONFIG_PATH)
  - [x] 2.6 Check project config existence
  - [x] 2.7 Handle 4 scenarios: both exist, global only, project only, neither
  - [x] 2.8 Deep merge project over global when both exist
  - [x] 2.9 Call existing `load_config(merged_dict)` with result
  - [x] 2.10 Handle ValidationError and wrap in ConfigError with context (AC11)

- [x] Task 3: Add helper for loading project config file (AC: 6, 9, 11)
  - [x] 3.1 Create `_load_project_config(project_path: Path) -> dict | None`
  - [x] 3.2 Return None if file doesn't exist (not an error)
  - [x] 3.3 Raise ConfigError if file exists but is invalid YAML (AC11)
  - [x] 3.4 Error message MUST include "project config" to distinguish from global config errors
  - [x] 3.5 Use existing `_load_yaml_file()` helper for actual loading

- [x] Task 4: Update module exports (AC: 10)
  - [x] 4.1 Export `load_config_with_project` from `core/__init__.py`
  - [x] 4.2 Keep backward compatibility with existing `load_global_config`

- [x] Task 5: Write comprehensive tests (AC: all)
  - [x] 5.1 Test project config overrides scalar values (AC1)
  - [x] 5.2 Test deep merge for nested dicts (AC2)
  - [x] 5.3 Test project config only scenario (AC3)
  - [x] 5.4 Test global config only scenario (AC4)
  - [x] 5.5 Test neither config exists (AC5)
  - [x] 5.6 Test project path resolution (AC6)
  - [x] 5.7 Test list replacement for providers.multi (AC7)
  - [x] 5.8 Test dict deep merge for power_prompts.variables (AC8)
  - [x] 5.9 Test path fields preserved from project (AC9)
  - [x] 5.10 Test singleton integration (AC10)
  - [x] 5.11 Test invalid project YAML raises ConfigError with "project config" in message (AC11)
  - [x] 5.12 Test project_path pointing to file raises ConfigError (AC12)
  - [x] 5.13 Use tmp_path fixture for all config files
  - [x] 5.14 Ensure >=95% coverage on new code

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

### Deep Merge Strategy (DECIDED)

**Decision: Recursive dict merge, list replacement**

```python
def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base.

    Rules:
    - Dicts are merged recursively
    - Lists are replaced (NOT merged/appended)
    - Scalar values are replaced by override
    - Keys only in base are preserved
    - Keys only in override are added

    Args:
        base: Base configuration dictionary.
        override: Override dictionary with higher priority.

    Returns:
        Merged dictionary (new dict, does not modify inputs).
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

**Rationale:**
1. Dict merge allows partial override (AC2, AC8) - override just `model` without repeating `provider`
2. List replacement is simpler and safer (AC7) - avoids duplicate entries
3. Matches YAML override patterns used by tools like docker-compose

**IMPORTANT: List Replacement Applies to ALL Lists**
- Not just `providers.multi` - ANY list in config is fully replaced by project config
- This is a global merge rule for consistency
- Example: if global has `excluded_paths: [a, b]` and project has `excluded_paths: [c]`, result is `[c]`

### Function Signature

```python
def load_config_with_project(
    project_path: str | Path | None = None,
    *,
    global_config_path: str | Path | None = None,  # For testing
) -> Config:
    """Load configuration with project override support.

    Loads global config from ~/.bmad-assist/config.yaml (or specified path),
    then loads project config from {project_path}/bmad-assist.yaml,
    and performs deep merge with project taking precedence.

    Args:
        project_path: Path to project directory. Defaults to current working directory.
            MUST be a directory, not a file (AC12).
        global_config_path: Custom global config path (for testing).

    Returns:
        Validated Config instance with merged configuration.

    Raises:
        ConfigError: If neither config exists, if config is invalid YAML,
            if project_path is not a directory, or if Pydantic validation fails.
            Error messages MUST distinguish between global and project config errors.
    """
```

### Error Message Requirements (AC11)

**Error messages MUST clearly distinguish which config file caused the error:**

| Error Type | Message Pattern |
|------------|-----------------|
| Invalid global YAML | `"Failed to parse global config at ~/.bmad-assist/config.yaml: {yaml_error}"` |
| Invalid project YAML | `"Failed to parse project config at {path}/bmad-assist.yaml: {yaml_error}"` |
| project_path is file | `"project_path must be a directory, got file: {path}"` |
| Neither exists | `"No configuration found. Run 'bmad-assist init' to create config."` |
| Pydantic validation | `"Invalid configuration (merged from global + project): {validation_error}"` |

### IMPORTANT: Scope Boundaries

**This story handles:**
- Loading project config from `{project_path}/bmad-assist.yaml`
- Deep merging project config over global config
- Handling all 4 scenarios (both/global/project/neither)

**NOT in scope for this story:**
- Interactive config generation (Story 1.7)
- Credentials handling (Story 1.5)
- CLI integration (Story 1.6)

---

## Technical Requirements

### From PRD (FR36, FR37 - Configuration)

| FR | Requirement | This Story's Implementation |
|----|-------------|----------------------------|
| FR36 | Load project config from ./bmad-assist.yaml | `load_config_with_project()` |
| FR37 | Project config can override global config values | Deep merge with project priority |

### From Architecture

**Configuration Hierarchy (architecture.md):**
> "Global config: `~/.bmad-assist/config.yaml`"
> "Project config: `./bmad-assist.yaml` (overrides global)"

**Config Validation:**
> "Pydantic - Type-safe, LLM-friendly"

### Dependencies

- **Story 1.2 (DONE):** Pydantic models, `load_config()`, `get_config()`, `ConfigError`
- **Story 1.3 (DONE):** `load_global_config()`, `_load_yaml_file()`, `GLOBAL_CONFIG_PATH`

### Integration with Existing Code

Story 1.4 builds on:
1. `_load_yaml_file(path: Path)` - Already handles YAML loading with safety checks
2. `load_config(config_data: dict)` - Validates and stores in singleton
3. `GLOBAL_CONFIG_PATH` - Default global config location

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
1. `fix(core): address Multi-LLM code review findings for story 1.3` - Code review fixes applied
2. `docs: add GEMINI.md project context for Gemini CLI` - Project context added
3. `docs(story): complete Multi-LLM validation for story 1.3` - Validation complete
4. `docs(story): create story 1.3 global configuration loading` - Story 1.3 created
5. `fix(core): address Multi-LLM code review findings for story 1.2` - Code review fixes

**Files from most recent commits:**
- `src/bmad_assist/core/config.py` - Extended with `_load_yaml_file`, `load_global_config`
- `tests/core/test_config.py` - 84 tests, 100% coverage
- `GEMINI.md` - Project context file added

**Key Patterns from Story 1.3:**
- `_load_yaml_file()` handles YAML loading with:
  - Size limit check (1MB)
  - Empty file detection
  - Permission error handling
  - UTF-8 encoding
- `load_global_config()` checks existence before loading
- ValidationError from Pydantic wrapped in ConfigError

### Previous Story Learnings (1.3)

**What worked well:**
- Using existing `_load_yaml_file()` helper for YAML loading
- Wrapping ValidationError in ConfigError with path context
- Resetting singleton on validation failure
- `Path(path).expanduser()` for tilde expansion

**Issues encountered and resolved:**
- File size check changed from stat-then-read to read-with-limit (TOCTOU fix)
- Empty file detection: `yaml.safe_load()` returns `None` for empty files
- IsADirectoryError needs separate handling

**Code Review Insights (from story 1.3 code review):**
- Read with size limit instead of stat-then-read (TOCTOU vulnerability)
- Explicit check for `is_file()` after `exists()`
- Reset singleton on validation failure

### Files Modified in Previous Story

**Story 1.3 file list:**
- `src/bmad_assist/core/config.py` - Added `_load_yaml_file()`, `load_global_config()`, constants
- `src/bmad_assist/core/__init__.py` - Added exports
- `tests/core/test_config.py` - Added 32 tests
- `pyproject.toml` - Added types-PyYAML

### Existing Code to Reuse

**From config.py (current implementation):**
```python
GLOBAL_CONFIG_PATH: Path = Path.home() / ".bmad-assist" / "config.yaml"
MAX_CONFIG_SIZE: int = 1_048_576

def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file with safety checks."""
    # ... existing implementation ...

def load_global_config(path: str | Path | None = None) -> Config:
    """Load global configuration from YAML file."""
    # ... existing implementation ...

def load_config(config_data: dict[str, Any]) -> Config:
    """Load and validate configuration from a dictionary."""
    # ... existing implementation ...
```

---

## File Structure

### Files to Modify

| File | Changes | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/core/config.py` | Add `_deep_merge`, `_load_project_config`, `load_config_with_project` | +40-50 |
| `src/bmad_assist/core/__init__.py` | Export `load_config_with_project` | +1 |
| `tests/core/test_config.py` | Add project config tests | +80-100 |

### Files NOT to Create/Modify

- `pyproject.toml` - No changes needed
- `src/bmad_assist/cli.py` - CLI integration in Story 1.6
- Any actual config files - User creates these

### Expected Project Config File Structure

```yaml
# ./bmad-assist.yaml (project-specific overrides)
providers:
  master:
    model: sonnet_4  # Override model, keep provider from global
  multi:
    - provider: codex
      model: o3

power_prompts:
  set_name: react-frontend  # Override set for this project
  variables:
    framework: react
    testing: jest

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
"""Additional tests for Story 1.4: Project Configuration Override."""

from pathlib import Path
import pytest

from bmad_assist.core.config import (
    load_config_with_project,
    get_config,
    _reset_config,
    _deep_merge,
)
from bmad_assist.core.exceptions import ConfigError


class TestDeepMerge:
    """Tests for _deep_merge helper function."""

    def test_scalar_override(self) -> None:
        """Override scalar values replace base values."""
        base = {"timeout": 300, "retries": 3}
        override = {"timeout": 600}
        result = _deep_merge(base, override)
        assert result["timeout"] == 600
        assert result["retries"] == 3

    def test_nested_dict_merge(self) -> None:
        """Nested dicts are merged recursively."""
        base = {"providers": {"master": {"provider": "claude", "model": "opus_4"}}}
        override = {"providers": {"master": {"model": "sonnet_4"}}}
        result = _deep_merge(base, override)
        assert result["providers"]["master"]["provider"] == "claude"
        assert result["providers"]["master"]["model"] == "sonnet_4"

    def test_list_replacement(self) -> None:
        """Lists are replaced, not merged."""
        base = {"multi": [{"provider": "gemini"}]}
        override = {"multi": [{"provider": "codex"}]}
        result = _deep_merge(base, override)
        assert len(result["multi"]) == 1
        assert result["multi"][0]["provider"] == "codex"

    def test_base_not_modified(self) -> None:
        """Original base dict is not modified."""
        base = {"key": "original"}
        override = {"key": "override"}
        _deep_merge(base, override)
        assert base["key"] == "original"


class TestProjectConfigOverride:
    """Tests for AC1: Project config overrides global values."""

    def test_project_overrides_global_scalar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Project config scalar values override global."""
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        global_config = global_dir / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
state_path: /global/state.yaml
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("""
state_path: /project/state.yaml
""")

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.state_path == "/project/state.yaml"
        assert config.providers.master.provider == "claude"


class TestDeepMergeNested:
    """Tests for AC2: Deep merge for nested structures."""

    def test_providers_master_partial_override(
        self, tmp_path: Path
    ) -> None:
        """Override just model, keep provider from global."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
    settings_file: /global/settings.json
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("""
providers:
  master:
    model: sonnet_4
""")

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.providers.master.provider == "claude"
        assert config.providers.master.model == "sonnet_4"
        assert config.providers.master.settings_file == "/global/settings.json"


class TestProjectConfigOnly:
    """Tests for AC3: Project config only (no global)."""

    def test_project_only_loads_successfully(
        self, tmp_path: Path
    ) -> None:
        """Project config alone is sufficient."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("""
providers:
  master:
    provider: codex
    model: o3
""")

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=nonexistent_global,
        )
        assert config.providers.master.provider == "codex"


class TestGlobalConfigOnly:
    """Tests for AC4: Global config only (no project)."""

    def test_global_only_loads_successfully(
        self, tmp_path: Path
    ) -> None:
        """Global config alone is sufficient."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: gemini
    model: gemini_2_5_pro
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # No bmad-assist.yaml in project

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.providers.master.provider == "gemini"


class TestNeitherConfigExists:
    """Tests for AC5: Neither config exists."""

    def test_neither_raises_config_error(self, tmp_path: Path) -> None:
        """Error when neither global nor project config exists."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=nonexistent_global,
            )
        assert "init" in str(exc_info.value).lower()


class TestListReplacement:
    """Tests for AC7: List override (not merge) for providers.multi."""

    def test_multi_list_replaced_not_merged(
        self, tmp_path: Path
    ) -> None:
        """Project multi list replaces global, not appends."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
  multi:
    - provider: gemini
      model: gemini_2_5_pro
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("""
providers:
  multi:
    - provider: codex
      model: o3
""")

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert len(config.providers.multi) == 1
        assert config.providers.multi[0].provider == "codex"


class TestDictDeepMerge:
    """Tests for AC8: Dictionary deep merge for power_prompts.variables."""

    def test_variables_deep_merged(self, tmp_path: Path) -> None:
        """power_prompts.variables dict is deep merged."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: python-cli
  variables:
    project_type: cli
    language: python
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("""
power_prompts:
  variables:
    project_type: web-app
    framework: react
""")

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.power_prompts.set_name == "python-cli"
        assert config.power_prompts.variables["project_type"] == "web-app"
        assert config.power_prompts.variables["language"] == "python"
        assert config.power_prompts.variables["framework"] == "react"


class TestSingletonIntegration:
    """Tests for AC10: Singleton updated with merged config."""

    def test_get_config_after_project_load(
        self, tmp_path: Path
    ) -> None:
        """get_config returns merged config after load_config_with_project."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        loaded = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        retrieved = get_config()
        assert loaded is retrieved


class TestProjectConfigMalformedYaml:
    """Tests for AC11: Invalid project YAML raises ConfigError."""

    def test_invalid_project_yaml_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Invalid YAML in project config raises ConfigError with 'project config' in message."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("invalid: yaml: syntax: [unclosed")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
            )
        assert "project config" in str(exc_info.value).lower() or "bmad-assist.yaml" in str(exc_info.value)


class TestProjectPathValidation:
    """Tests for AC12: project_path must be a directory."""

    def test_project_path_is_file_raises_error(
        self, tmp_path: Path
    ) -> None:
        """project_path pointing to a file raises ConfigError."""
        file_path = tmp_path / "not-a-dir.txt"
        file_path.write_text("i am a file")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(project_path=file_path)
        assert "directory" in str(exc_info.value).lower()
```

### Coverage Target
- **>=95% coverage** on new code
- All merge scenarios tested
- All 4 config existence scenarios tested
- Integration with singleton tested

### Mocking Strategy
- Use `tmp_path` pytest fixture for test config files
- Use `_reset_config()` fixture from Story 1.2 for singleton cleanup
- Use `monkeypatch` for any path manipulation if needed
- No mocking of file system - use real temp files

---

## Library/Framework Requirements

### Deep Merge Implementation

```python
from typing import Any

def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base dict.

    Args:
        base: Base configuration dictionary.
        override: Override dictionary with higher priority.

    Returns:
        New merged dictionary (inputs not modified).
    """
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
```

### pathlib Usage

```python
from pathlib import Path

PROJECT_CONFIG_NAME = "bmad-assist.yaml"

def _get_project_config_path(project_path: Path) -> Path:
    return project_path / PROJECT_CONFIG_NAME
```

---

## Project Context Reference

**Project:** bmad-assist - CLI tool for automating BMAD methodology development loop

**Key Architecture Patterns:**
- Config singleton via `get_config()` - Stories 1.2, 1.3 established this
- Pydantic validation with frozen models
- Path expansion for ~ in state_path
- YAML loading via `_load_yaml_file()` helper

**Critical Rules:**
- Python 3.11+, PEP8 naming, type hints on all functions
- Google-style docstrings for public APIs
- Test coverage >=95% on new code
- mypy strict mode, ruff linting

---

## References

- [Source: docs/architecture.md#Data-Architecture] - Config hierarchy: global + project
- [Source: docs/architecture.md#Config-Access-Pattern] - Singleton pattern
- [Source: docs/prd.md#Configuration] - FR36, FR37 requirements
- [Source: docs/epics.md#Story-1.4] - Original story definition
- [Source: Story 1.2] - Pydantic models, load_config(), get_config()
- [Source: Story 1.3] - load_global_config(), _load_yaml_file()

---

## Verification Checklist

Before marking as complete, verify:

- [x] `_deep_merge()` helper function implemented
- [x] `load_config_with_project()` function implemented
- [x] Function loads global config from `~/.bmad-assist/config.yaml`
- [x] Function loads project config from `{project_path}/bmad-assist.yaml`
- [x] Deep merge correctly handles nested dicts (AC2, AC8)
- [x] Lists are replaced, not merged (AC7)
- [x] Project-only scenario works (AC3)
- [x] Global-only scenario works (AC4)
- [x] Neither scenario raises ConfigError (AC5)
- [x] Singleton updated correctly (AC10)
- [x] Invalid project YAML raises ConfigError with "project config" in message (AC11)
- [x] project_path pointing to file raises ConfigError (AC12)
- [x] `load_config_with_project` exported from `core/__init__.py`
- [x] `mypy src/` reports no errors
- [x] `ruff check src/` reports no issues
- [x] `pytest tests/core/` passes all tests (142 passed)
- [x] Coverage >=95% on new code (95% achieved)

---

## Dev Agent Record

### Context Reference
- Story ID: 1.4
- Story Key: 1-4-project-configuration-override
- Epic: 1 - Project Foundation & CLI Infrastructure
- Previous Story: 1.3 (done) - Global Configuration Loading

### Agent Model Used
Claude claude-opus-4-5-20251101

### Debug Log References
N/A - Implementation completed without errors

### Completion Notes List
- Implemented `_deep_merge()` helper with recursive dict merge and list replacement
- Implemented `load_config_with_project()` with support for 4 scenarios (both, global-only, project-only, neither)
- Added `_load_project_config()` helper for loading project-specific YAML
- Updated `core/__init__.py` exports with `load_config_with_project` and `PROJECT_CONFIG_NAME`
- Added 52 new tests for Story 1.4 functionality
- All 142 tests pass, 95% coverage achieved

### File List
Modified:
- `src/bmad_assist/core/config.py` - Added `_deep_merge()`, `_load_project_config()`, `load_config_with_project()`, `PROJECT_CONFIG_NAME`
- `src/bmad_assist/core/__init__.py` - Added exports for new functions and constants
- `tests/core/test_config.py` - Added comprehensive test suite for Story 1.4 (52 new tests)
- `docs/sprint-artifacts/sprint-status.yaml` - Updated story status
- `docs/sprint-artifacts/1-4-project-configuration-override.md` - Updated task completion status
