# Story 1.5: Credentials Security with .env

**Status:** done
**Story Points:** 2

---

## Story

**As a** developer,
**I want** API credentials stored securely in .env file,
**So that** secrets are never exposed in config files or logs.

### Business Context

This story addresses critical security requirements (NFR8, NFR9) for credential handling. API keys for Claude Code, Codex, and Gemini CLI are sensitive secrets that must be:
1. Stored separately from configuration files
2. Protected with restricted file permissions
3. Never logged or displayed in output
4. Loaded via environment variables that CLI tools read directly

The architecture decision (architecture.md) states that "CLI tools (Claude Code, Codex, Gemini CLI) read these environment variables directly - bmad-assist never touches credentials in code." This means bmad-assist only needs to:
- Load `.env` file to set environment variables
- Warn about insecure file permissions
- Provide `.env.example` template

### Success Criteria

- Environment variables are loaded from `.env` file on application start
- Warning is logged if `.env` file has incorrect permissions (not 600)
- `.env.example` template is provided in repository
- Credentials are never written to logs
- Application continues even without `.env` file (CLI tools may have credentials via other means)

---

## Acceptance Criteria

### AC1: Environment Variables Loaded from .env (Without Override)
```gherkin
Given `.env` file exists in the project directory with API keys
  """
  ANTHROPIC_API_KEY=sk-ant-xxx
  OPENAI_API_KEY=sk-xxx
  GEMINI_API_KEY=xxx
  """
When the application starts
Then environment variables are loaded into os.environ
And CLI providers can read these keys via os.getenv()
And existing environment variables are NOT overridden (override=False)
```

### AC1a: Existing Environment Variables Preserved
```gherkin
Given system environment has ANTHROPIC_API_KEY="sk-ant-system-key"
And `.env` file exists with ANTHROPIC_API_KEY="sk-ant-dotenv-key"
When the application loads the .env file
Then os.environ["ANTHROPIC_API_KEY"] remains "sk-ant-system-key"
And the .env value is NOT used (system takes precedence)
```

### AC2: Warning for Insecure Permissions
```gherkin
Given `.env` file exists with permissions other than 600 (e.g., 644)
When the application starts
Then a warning is logged about insecure permissions
And the warning message includes the file path and current permissions
And the application continues to run (not a fatal error)
```

### AC3: Secure Permissions Accepted Silently
```gherkin
Given `.env` file exists with correct permissions (600)
When the application starts
Then no warning is logged about permissions
And environment variables are loaded normally
```

### AC4: Missing .env File Handled Gracefully
```gherkin
Given no `.env` file exists in the project directory
When the application starts
Then no error is raised
And a debug log message indicates ".env file not found, skipping"
And the application continues (credentials may exist via other means)
```

### AC5: .env.example Template Provided
```gherkin
Given the bmad-assist repository
When user clones the repository
Then `.env.example` file exists with documented variables
And the template includes: ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
And the template includes instructions for obtaining API keys
And `.env.example` is tracked in git (NOT in .gitignore)
```

### AC6: .env File Excluded from Git
```gherkin
Given `.gitignore` file exists in repository
When checking git tracking
Then `.env` pattern is listed in `.gitignore`
And actual `.env` files are never committed
```

### AC7: Credentials Never Logged
```gherkin
Given `.env` file is loaded with API keys
When any logging occurs during application execution
Then API key values (sk-ant-*, sk-*, etc.) are never written to logs
And if credentials must be referenced in logs, they are masked (e.g., "sk-ant-***")
```

### AC8: Load .env from Project Directory
```gherkin
Given project_path is "/home/user/my-project"
And `.env` file exists at "/home/user/my-project/.env"
When load_env_file(project_path) is called
Then environment variables from that `.env` file are loaded
And path is resolved from project_path parameter
```

### AC9: Integration with Config Loading
```gherkin
Given load_config_with_project(project_path) is called
When configuration is loaded
Then environment variables are loaded BEFORE config validation
And CLI providers can use credentials immediately after config is loaded
```

### AC10: File Permission Check on Linux/Mac Only
```gherkin
Given application is running on Windows
When `.env` file exists
Then no permission warning is logged (Windows has different permission model)
And environment variables are loaded normally
```

### AC11: UTF-8 Encoding Support
```gherkin
Given `.env` file contains UTF-8 characters in comments
When the file is loaded
Then it is read with UTF-8 encoding
And no encoding errors occur
```

---

## Tasks / Subtasks

- [x] Task 1: Add python-dotenv dependency (AC: 1, 8)
  - [x] 1.1 Add `python-dotenv>=1.0.0` to pyproject.toml dependencies
  - [x] 1.2 Add `types-python-dotenv` to dev dependencies for mypy
  - [x] 1.3 Run `pip install -e .` to install new dependency

- [x] Task 2: Create load_env_file() function (AC: 1, 1a, 3, 4, 8, 11)
  - [x] 2.1 Create function in `core/config.py`: `load_env_file(project_path: Path | None = None) -> bool`
  - [x] 2.2 Resolve `.env` path: `{project_path}/.env` or `{cwd}/.env` if project_path is None
  - [x] 2.3 Return False (no error) if `.env` file doesn't exist
  - [x] 2.4 Use `dotenv.load_dotenv(path, encoding='utf-8', override=False)` to load environment variables (CRITICAL: override=False preserves existing env vars)
  - [x] 2.5 Return True if file was loaded successfully
  - [x] 2.6 Add debug log: "Loaded environment variables from {path}"

- [x] Task 3: Implement permission check function (AC: 2, 3, 10)
  - [x] 3.1 Create `_check_env_file_permissions(path: Path) -> None` in `core/config.py`
  - [x] 3.2 Skip check on Windows: `if sys.platform == 'win32': return`
  - [x] 3.3 Get file mode: `path.stat().st_mode & 0o777`
  - [x] 3.4 If mode != 0o600, log warning with current mode (e.g., "Warning: .env file {path} has insecure permissions {mode:o}, expected 600")
  - [x] 3.5 Use `logger.warning()` for the message

- [x] Task 4: Create .env.example template (AC: 5)
  - [x] 4.1 Create `.env.example` file in project root
  - [x] 4.2 Add documented variables:
    ```
    # bmad-assist Environment Variables
    # Copy this file to .env and fill in your API keys
    # IMPORTANT: Never commit .env to git!

    # Claude Code (Anthropic) - https://console.anthropic.com/
    ANTHROPIC_API_KEY=sk-ant-your-key-here

    # Codex (OpenAI) - https://platform.openai.com/api-keys
    OPENAI_API_KEY=sk-your-key-here

    # Gemini CLI (Google) - https://aistudio.google.com/app/apikey
    GEMINI_API_KEY=your-key-here
    ```
  - [x] 4.3 Verify `.env.example` is NOT in `.gitignore`

- [x] Task 5: Update .gitignore (AC: 6)
  - [x] 5.1 Check if `.gitignore` exists (create if not)
  - [x] 5.2 Add `.env` pattern if not already present (already present)
  - [x] 5.3 Add comment: `# Environment variables with secrets` (already present)

- [x] Task 6: Integrate with config loading (AC: 9)
  - [x] 6.1 Modify `load_config_with_project()` to call `load_env_file()` first
  - [x] 6.2 Call `load_env_file(resolved_project)` at the start of function
  - [x] 6.3 Check permissions after loading: `_check_env_file_permissions()` (via load_env_file)
  - [x] 6.4 Document in docstring that .env is loaded

- [x] Task 7: Add credential masking for logging (AC: 7)
  - [x] 7.1 Create `_mask_credential(value: str) -> str` helper
  - [x] 7.2 Pattern: if value starts with "sk-ant-" or "sk-", show first 7 chars + "***"
  - [x] 7.3 Add constant `ENV_CREDENTIAL_KEYS` = {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"}
  - [x] 7.4 If any credential keys appear in log messages, mask their values (helper available for use)

- [x] Task 8: Update module exports (AC: 9)
  - [x] 8.1 Export `load_env_file` from `core/__init__.py`
  - [x] 8.2 Keep backward compatibility with existing exports

- [x] Task 9: Write comprehensive tests (AC: all)
  - [x] 9.1 Test .env file loaded successfully (AC1)
  - [x] 9.1a Test existing env vars NOT overridden (AC1a) - CRITICAL
  - [x] 9.2 Test warning logged for insecure permissions (AC2)
  - [x] 9.3 Test no warning for secure permissions (AC3)
  - [x] 9.4 Test missing .env handled gracefully (AC4)
  - [x] 9.5 Test .env.example exists and has required keys (AC5) - file created
  - [x] 9.6 Test .env in .gitignore (AC6) - already present
  - [x] 9.7 Test credential masking (AC7)
  - [x] 9.8 Test project path resolution (AC8)
  - [x] 9.9 Test integration with load_config_with_project (AC9)
  - [x] 9.10 Test Windows platform skip (AC10) - mock sys.platform
  - [x] 9.11 Test UTF-8 encoding (AC11)
  - [x] 9.12 Use tmp_path fixture for all test files
  - [x] 9.13 Ensure >=95% coverage on new code (173 tests pass)

---

## Dev Notes

### Critical Architecture Requirements

**From architecture.md - MUST follow exactly:**

1. **Credential Strategy:**
   > "Credentials (secrets): `.env` file (chmod 600, in .gitignore)"
   > "CLI tools (Claude Code, Codex, Gemini CLI) read these environment variables directly - bmad-assist never touches credentials in code."

2. **Module Location:** `src/bmad_assist/core/config.py` (extend existing)
3. **Exception Handling:** Use existing logging (no exceptions for missing .env)
4. **Naming Conventions:** PEP8 (snake_case functions)
5. **Type Hints:** Required on ALL functions
6. **Docstrings:** Google-style for all public APIs

### Implementation Strategy

**Use python-dotenv library:**
- Standard, well-tested solution for .env handling
- Supports UTF-8, comments, multiline values
- **CRITICAL:** Must use `override=False` to preserve existing env vars

```python
from dotenv import load_dotenv

# Load .env file - MUST use override=False to not overwrite system env vars
load_dotenv(path, encoding='utf-8', override=False)
```

**Why `override=False` matters:**
- CI/CD systems may set env vars via secrets managers
- Docker containers may inject env vars
- System-level env vars should take precedence over .env file
- This is standard security practice - explicit system config wins

### Permission Check Implementation

```python
import os
import sys
import stat
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def _check_env_file_permissions(path: Path) -> None:
    """Check if .env file has secure permissions (600 on Unix).

    Only checks on Unix-like systems (Linux, macOS).
    Logs warning if permissions are too permissive.

    Args:
        path: Path to .env file.
    """
    if sys.platform == 'win32':
        return  # Windows has different permission model

    try:
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            logger.warning(
                f".env file {path} has insecure permissions {mode:03o}, "
                f"expected 600. Run: chmod 600 {path}"
            )
    except OSError:
        pass  # File may have been deleted between check and stat
```

### Credential Masking Pattern

```python
ENV_CREDENTIAL_KEYS: frozenset[str] = frozenset({
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
})

def _mask_credential(value: str) -> str:
    """Mask credential value for safe logging.

    Args:
        value: Credential value to mask.

    Returns:
        Masked value showing only first 7 characters.
    """
    if len(value) <= 7:
        return "***"
    return value[:7] + "***"
```

### Function Signature

```python
def load_env_file(
    project_path: str | Path | None = None,
    *,
    check_permissions: bool = True,
) -> bool:
    """Load environment variables from .env file.

    Loads environment variables from {project_path}/.env or {cwd}/.env.
    Does NOT override existing environment variables.

    Args:
        project_path: Path to project directory. Defaults to current working directory.
        check_permissions: Whether to check file permissions (default True).

    Returns:
        True if .env file was found and loaded, False otherwise.

    Note:
        - Missing .env file is not an error (returns False)
        - On Unix, warns if permissions are not 600
        - On Windows, permission check is skipped
    """
```

### IMPORTANT: Security Considerations

1. **Never log credential values** - Use masking for any log that might include credentials
2. **Don't validate credential format** - Let CLI tools handle validation
3. **Don't store credentials in memory beyond os.environ** - Load and forget
4. **File permission warning is advisory** - Don't block execution

### IMPORTANT: Scope Boundaries

**This story handles:**
- Loading `.env` file to set environment variables
- Permission checking and warning
- Providing `.env.example` template
- Integration with config loading

**NOT in scope for this story:**
- Validating API key format
- Testing actual API connectivity
- Credential rotation or expiration
- Encrypted credential storage
- Multi-environment profiles (e.g., .env.development, .env.production)
- Dynamic credential key registration from providers

### Tech Debt Note: Hardcoded ENV_CREDENTIAL_KEYS

**Issue:** The `ENV_CREDENTIAL_KEYS` constant hardcodes known credential variable names (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`). This couples core config to specific providers.

**Impact:** Adding a new provider requires modifying this constant in core code.

**Accepted for now because:**
1. Foundation phase - only 3 providers needed for MVP
2. Limited blast radius - single constant to update
3. YAGNI - dynamic registration adds complexity without immediate benefit

**Future resolution:** When implementing FR10 (Plugin Architecture), providers should register their credential key names dynamically. Track as tech debt item for Epic 4 (CLI Provider Integration).

---

## Technical Requirements

### From PRD (NFR8, NFR9 - Security)

| NFR | Requirement | This Story's Implementation |
|-----|-------------|----------------------------|
| NFR8 | Credentials stored in separate file with chmod 600 | `.env` file with permission check |
| NFR9 | Credentials not logged or displayed in stdout | Credential masking in logs |

### From Architecture

**Provider Configuration (architecture.md):**
> "Credentials (secrets): `.env` file (chmod 600, in .gitignore)"
> "API keys for CLI tools (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY)"
> "CLI tools read env vars directly - bmad-assist never handles secrets"

**Example .env file (from architecture):**
```
# .env - NEVER commit to git
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

### Dependencies

- **Story 1.4 (DONE):** `load_config_with_project()` - Integration point
- **New Dependency:** python-dotenv>=1.0.0

### Integration with Existing Code

Story 1.5 integrates with:
1. `load_config_with_project()` - Add .env loading at the start
2. Logging system - Add credential masking
3. Repository files - Add .env.example, update .gitignore

---

## Architecture Compliance

### Stack Verification
- [x] Python 3.11+ type hints - Required
- [ ] python-dotenv - To be added in pyproject.toml

### Structure Verification
- [x] Location: `src/bmad_assist/core/config.py` (extend existing)
- [x] Template: `.env.example` in project root
- [x] Tests: `tests/core/test_config.py` (extend existing)

### Pattern Verification
- [x] PEP8 naming conventions
- [x] Google-style docstrings
- [x] Warning via logger.warning()
- [x] No exceptions for missing .env

---

## Developer Context

### Git Intelligence Summary

**Recent commits (from git log):**
1. `fix(core): address Multi-LLM code review findings for story 1.4` - Deep copy fix, singleton cleanup
2. `docs(power-prompts): clarify commit requirement in dev-story prompt` - Prompt updates
3. `feat(core): implement project configuration override for story 1.4` - Config merge
4. `docs(story): complete Multi-LLM validation for story 1.4` - Validation done
5. `docs(power-prompts): update python-cli power-prompt set` - Prompt set updates

**Files from most recent commits:**
- `src/bmad_assist/core/config.py` - Extended with deep merge, project config
- `tests/core/test_config.py` - Now 144 tests, 95% coverage
- `power-prompts/python-cli/*.md` - Power-prompt updates

**Key Patterns from Story 1.4:**
- `load_config_with_project()` loads global then project config
- `_deep_merge()` for config merging
- Singleton cleared on failure to prevent stale state
- `copy.deepcopy()` used to avoid mutation bugs

### Previous Story Learnings (1.4)

**What worked well:**
- Reusing `_load_yaml_file()` helper
- Clear error messages distinguishing global vs project config
- Singleton reset on validation failure

**Issues encountered and resolved:**
- Deep copy bug: shallow copy caused list mutation - fixed with copy.deepcopy()
- ValidationError leakage: now wrapped in ConfigError
- Stale singleton: cleared before re-raising exceptions

**Code Review Insights (from story 1.4 code review):**
- Deep copy required for mutable nested structures
- Wrap all external exceptions (ValidationError) in ConfigError
- Reset singleton on ANY failure path

### Files Modified in Previous Story

**Story 1.4 file list:**
- `src/bmad_assist/core/config.py` - Added `_deep_merge()`, `_load_project_config()`, `load_config_with_project()`
- `src/bmad_assist/core/__init__.py` - Added exports
- `tests/core/test_config.py` - Added 52 tests
- `docs/sprint-artifacts/sprint-status.yaml` - Updated status

### Existing Code to Reuse

**From config.py (current implementation):**
```python
PROJECT_CONFIG_NAME: str = "bmad-assist.yaml"

def load_config_with_project(
    project_path: str | Path | None = None,
    *,
    global_config_path: str | Path | None = None,
) -> Config:
    """Load configuration with project override support."""
    ...
```

---

## File Structure

### Files to Create

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment variables with documentation |

### Files to Modify

| File | Changes | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/core/config.py` | Add `load_env_file`, `_check_env_file_permissions`, `_mask_credential`, `ENV_CREDENTIAL_KEYS` | +40-50 |
| `src/bmad_assist/core/__init__.py` | Export `load_env_file` | +1 |
| `tests/core/test_config.py` | Add .env tests | +60-80 |
| `pyproject.toml` | Add python-dotenv dependency | +2 |
| `.gitignore` | Add .env pattern | +2 |

### Expected .env File Structure

```bash
# .env - NEVER commit to git!
# Copy from .env.example and fill in your API keys

# Claude Code (Anthropic)
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# Codex (OpenAI)
OPENAI_API_KEY=sk-your-actual-key-here

# Gemini CLI (Google)
GEMINI_API_KEY=your-actual-key-here
```

---

## Testing Requirements

### Test Cases to Add (tests/core/test_config.py)

```python
"""Additional tests for Story 1.5: Credentials Security with .env."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from bmad_assist.core.config import (
    load_env_file,
    load_config_with_project,
    _check_env_file_permissions,
    _mask_credential,
    ENV_CREDENTIAL_KEYS,
)


class TestLoadEnvFile:
    """Tests for load_env_file function."""

    def test_loads_env_file_successfully(self, tmp_path: Path) -> None:
        """AC1: Environment variables loaded from .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\n")

        result = load_env_file(project_path=tmp_path)

        assert result is True
        assert os.environ.get("TEST_VAR") == "test_value"

    def test_existing_env_var_not_overridden(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC1a: Existing environment variables are NOT overridden."""
        # Set existing env var BEFORE loading .env
        monkeypatch.setenv("EXISTING_VAR", "system_value")

        # Create .env with different value for same key
        env_file = tmp_path / ".env"
        env_file.write_text("EXISTING_VAR=dotenv_value\n")

        result = load_env_file(project_path=tmp_path)

        assert result is True
        # CRITICAL: System value must be preserved, NOT overwritten
        assert os.environ.get("EXISTING_VAR") == "system_value"

    def test_missing_env_file_returns_false(self, tmp_path: Path) -> None:
        """AC4: Missing .env handled gracefully."""
        result = load_env_file(project_path=tmp_path)

        assert result is False

    def test_project_path_resolution(self, tmp_path: Path) -> None:
        """AC8: .env loaded from project directory."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        env_file = project_dir / ".env"
        env_file.write_text("PROJECT_VAR=from_project\n")

        result = load_env_file(project_path=project_dir)

        assert result is True
        assert os.environ.get("PROJECT_VAR") == "from_project"

    def test_utf8_encoding_support(self, tmp_path: Path) -> None:
        """AC11: UTF-8 encoding supported."""
        env_file = tmp_path / ".env"
        env_file.write_text("# Komentarz po polsku: żółć\nUTF8_VAR=wartość\n", encoding="utf-8")

        result = load_env_file(project_path=tmp_path)

        assert result is True
        assert os.environ.get("UTF8_VAR") == "wartość"


class TestEnvFilePermissions:
    """Tests for _check_env_file_permissions function."""

    @pytest.mark.skipif(os.name == 'nt', reason="Unix permissions only")
    def test_warns_on_insecure_permissions(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC2: Warning logged for insecure permissions."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        env_file.chmod(0o644)

        _check_env_file_permissions(env_file)

        assert "insecure permissions" in caplog.text
        assert "644" in caplog.text

    @pytest.mark.skipif(os.name == 'nt', reason="Unix permissions only")
    def test_no_warning_for_secure_permissions(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3: No warning for correct permissions."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        env_file.chmod(0o600)

        _check_env_file_permissions(env_file)

        assert "insecure permissions" not in caplog.text

    def test_skips_check_on_windows(self, tmp_path: Path) -> None:
        """AC10: Permission check skipped on Windows."""
        with patch("sys.platform", "win32"):
            env_file = tmp_path / ".env"
            env_file.write_text("SECRET=value\n")

            # Should not raise or warn
            _check_env_file_permissions(env_file)


class TestCredentialMasking:
    """Tests for _mask_credential function."""

    def test_masks_anthropic_key(self) -> None:
        """AC7: Anthropic key masked."""
        masked = _mask_credential("sk-ant-api123456789")
        assert masked == "sk-ant-***"

    def test_masks_openai_key(self) -> None:
        """AC7: OpenAI key masked."""
        masked = _mask_credential("sk-proj-abcdef123456")
        assert masked == "sk-proj***"

    def test_masks_short_value(self) -> None:
        """AC7: Short values fully masked."""
        masked = _mask_credential("short")
        assert masked == "***"

    def test_credential_keys_defined(self) -> None:
        """AC7: Expected credential keys are defined."""
        assert "ANTHROPIC_API_KEY" in ENV_CREDENTIAL_KEYS
        assert "OPENAI_API_KEY" in ENV_CREDENTIAL_KEYS
        assert "GEMINI_API_KEY" in ENV_CREDENTIAL_KEYS


class TestEnvIntegration:
    """Tests for integration with config loading."""

    def test_env_loaded_before_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC9: .env loaded before config validation."""
        # Create global config
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")

        # Create project with .env
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        env_file = project_dir / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-ant-test\n")

        load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )

        # Verify env was loaded
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test"


class TestEnvExampleFile:
    """Tests for .env.example template."""

    def test_env_example_exists(self) -> None:
        """AC5: .env.example template exists."""
        env_example = Path(__file__).parent.parent.parent.parent / ".env.example"
        assert env_example.exists(), f".env.example not found at {env_example}"

    def test_env_example_has_required_keys(self) -> None:
        """AC5: .env.example contains required variables."""
        env_example = Path(__file__).parent.parent.parent.parent / ".env.example"
        content = env_example.read_text()

        assert "ANTHROPIC_API_KEY" in content
        assert "OPENAI_API_KEY" in content
        assert "GEMINI_API_KEY" in content


class TestGitignore:
    """Tests for .gitignore configuration."""

    def test_env_in_gitignore(self) -> None:
        """AC6: .env is in .gitignore."""
        gitignore = Path(__file__).parent.parent.parent.parent / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            assert ".env" in content
```

### Coverage Target
- **>=95% coverage** on new code
- All permission scenarios tested (600, 644, missing file)
- Integration with config loading tested
- Platform-specific behavior tested (mock sys.platform)

### Mocking Strategy
- Use `tmp_path` pytest fixture for test .env files
- Use `monkeypatch` for environment variable cleanup
- Use `patch("sys.platform", "win32")` for Windows tests
- Use `caplog` fixture for log message assertions

---

## Library/Framework Requirements

### python-dotenv Usage

```python
from dotenv import load_dotenv

# Basic usage
load_dotenv(path, encoding='utf-8')

# With options
load_dotenv(
    dotenv_path=path,
    encoding='utf-8',
    override=False,  # Don't override existing env vars
)
```

### pathlib Usage

```python
from pathlib import Path

ENV_FILE_NAME = ".env"

def _get_env_file_path(project_path: Path) -> Path:
    return project_path / ENV_FILE_NAME
```

---

## Project Context Reference

**Project:** bmad-assist - CLI tool for automating BMAD methodology development loop

**Key Architecture Patterns:**
- Config singleton via `get_config()` - Stories 1.2, 1.3, 1.4 established this
- Pydantic validation with frozen models
- Credentials via environment variables (CLI tools read directly)
- Logging via `logger = logging.getLogger(__name__)`

**Critical Rules:**
- Python 3.11+, PEP8 naming, type hints on all functions
- Google-style docstrings for public APIs
- Test coverage >=95% on new code
- mypy strict mode, ruff linting
- **NEVER log credential values**

---

## References

- [Source: docs/architecture.md#Provider-Configuration] - Credentials in .env file, chmod 600
- [Source: docs/architecture.md#Data-Architecture] - Credentials strategy
- [Source: docs/prd.md#Non-Functional-Requirements] - NFR8, NFR9 security requirements
- [Source: docs/epics.md#Story-1.5] - Original story definition
- [Source: Story 1.4] - load_config_with_project() integration point
- [Source: docs/project-context.md#Security-Rules] - Credentials ONLY in .env, never in code/logs

---

## Verification Checklist

Before marking as complete, verify:

- [ ] `python-dotenv>=1.0.0` added to pyproject.toml
- [ ] `load_env_file()` function implemented with `override=False`
- [ ] Test confirms existing env vars are NOT overridden (AC1a)
- [ ] `_check_env_file_permissions()` helper implemented
- [ ] `_mask_credential()` helper implemented
- [ ] `ENV_CREDENTIAL_KEYS` constant defined
- [ ] `.env.example` template created with all required keys
- [ ] `.gitignore` includes `.env` pattern
- [ ] `load_config_with_project()` calls `load_env_file()` first
- [ ] `load_env_file` exported from `core/__init__.py`
- [ ] Permission check skips on Windows
- [ ] Warning logged for permissions != 600
- [ ] Missing .env file handled gracefully (no error)
- [ ] Credentials never logged (masking implemented)
- [ ] `mypy src/` reports no errors
- [ ] `ruff check src/` reports no issues
- [ ] `pytest tests/core/` passes all tests
- [ ] Coverage >=95% on new code

---

## Dev Agent Record

### Context Reference
- Story ID: 1.5
- Story Key: 1-5-credentials-security-with-env
- Epic: 1 - Project Foundation & CLI Infrastructure
- Previous Story: 1.4 (review) - Project Configuration Override

### Agent Model Used
Claude Opus 4.5 (Master LLM Synthesis)

### Debug Log References
- Initial implementation: commit a0ae56b
- Code review synthesis: 2025-12-09

### Completion Notes List
1. Implementation completed in commit a0ae56b with all 11 ACs implemented
2. Multi-LLM code reviews received from Sonnet 4.5, Codex GPT-5, Gemini 2.5 Flash
3. Master synthesis applied 3 valid fixes:
   - Fixed `_mask_credential` to handle None values (Gemini finding)
   - Relaxed permission check to accept 0o400 in addition to 0o600 (Gemini finding)
   - Removed non-existent `types-python-dotenv` package from pyproject.toml
4. Added 2 new tests for the fixes (175 total tests)
5. 97% code coverage on config.py, mypy and ruff pass clean

### File List
- `src/bmad_assist/core/config.py` - Added load_env_file(), _check_env_file_permissions(), _mask_credential(), ENV_CREDENTIAL_KEYS (+94 lines)
- `src/bmad_assist/core/__init__.py` - Exported load_env_file (+2 lines)
- `tests/core/test_config.py` - Added 32 tests for Story 1.5 ACs (+~400 lines)
- `pyproject.toml` - Added python-dotenv>=1.0.0 dependency (+2 lines, -1 invalid package)
- `.env.example` - New file with documented API key template (21 lines)
- `.gitignore` - Already had .env pattern (no changes needed)
