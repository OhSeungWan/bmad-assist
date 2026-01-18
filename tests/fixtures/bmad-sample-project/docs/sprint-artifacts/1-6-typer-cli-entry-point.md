# Story 1.6: Typer CLI Entry Point

**Status:** Ready for Review
**Story Points:** 2

---

## Story

**As a** developer,
**I want** a Typer CLI with `run` command,
**So that** I can execute bmad-assist from the command line.

### Business Context

This story completes Epic 1 (Project Foundation & CLI Infrastructure) by implementing a production-ready CLI entry point. The CLI serves as the primary user interface for bmad-assist, enabling fire-and-forget execution of the BMAD development loop.

The CLI must:
1. Accept project path and config file arguments
2. Load and validate configuration
3. Delegate execution to the main loop (Epic 6)
4. Display Rich-formatted output for all messages
5. Handle errors gracefully with clear messages

### Success Criteria

- `bmad-assist run --project ./my-project` parses arguments and initiates the main loop
- `--config` option allows custom config path
- `--help` displays comprehensive usage information
- Rich console is used for all output (errors, progress, results)
- Configuration is loaded via `load_config_with_project()` from Story 1.4
- Environment variables are loaded from `.env` via Story 1.5 integration
- Proper exit codes for success (0), user error (1), and configuration error (2)

### 🚨 CRITICAL REQUIREMENTS

> **These requirements are NON-NEGOTIABLE. Violation = story failure.**

1. **No Business Logic in CLI Layer** - `cli.py` only parses args, calls `core/loop.py`
2. **Rich Console for ALL Output** - Replace all `typer.echo()` with `console.print()`
3. **Exit Codes:** `0` = success, `1` = general error, `2` = config error
4. **Integration:** Must call `load_config_with_project()` from Story 1.4
5. **Security:** `.env` loaded automatically via Story 1.5 integration
6. **Main Loop Stub:** Create minimal `run_loop()` stub in `core/loop.py` (actual implementation in Epic 6)

### Blocking Dependencies

| Dependency | Status | Provides |
|------------|--------|----------|
| Story 1.4 | ✅ DONE | `load_config_with_project()` function |
| Story 1.5 | ✅ DONE | `.env` loading (automatic via config) |
| `typer[all]` | ✅ Available | Rich console via pyproject.toml |

**Future Dependency (NOT blocking):**
- Epic 6, Story 6.5: Full `run_loop()` implementation (this story creates stub only)

---

## Acceptance Criteria

### AC1: Run Command Parses Arguments Correctly
```gherkin
Given bmad-assist is installed
When user runs `bmad-assist run --project ./my-project`
Then CLI parses the --project argument as path to project directory
And CLI resolves relative paths to absolute paths
And CLI validates that the project directory exists
```

### AC2: Config Option Specifies Custom Config Path
```gherkin
Given bmad-assist is installed
When user runs `bmad-assist run --project ./my-project --config ./custom-config.yaml`
Then CLI passes the config path to load_config_with_project()
And configuration is loaded from the specified file
And project config merging follows Story 1.4 behavior
```

### AC3: Help Displays Usage Information
```gherkin
Given bmad-assist is installed
When user runs `bmad-assist run --help`
Then help displays command description
And help shows all available options (--project, --config)
And help shows option descriptions and defaults
And help shows short forms (-p, -c)
```

### AC4: Rich Console for All Output
```gherkin
Given bmad-assist is running
When any output is displayed (messages, errors, progress)
Then Rich console is used for formatting
And errors are displayed with [red] styling
And success messages use [green] styling
And warning messages use [yellow] styling
```

### AC5: Delegates to Main Loop (Stub)
```gherkin
Given configuration is loaded successfully
When run command executes
Then CLI imports and calls run_loop() from core/loop.py
And CLI passes loaded Config object and project Path
And CLI waits for run_loop() to return (blocking call)
And CLI exits with code 0 if run_loop() returns successfully
```

**Note:** This story creates a stub `run_loop()` that:
- Accepts `config: Config` and `project_path: Path` parameters
- Logs "Main loop placeholder - see Epic 6 for implementation"
- Returns immediately (no actual loop logic)
- Full implementation deferred to Epic 6, Story 6.5

### AC6: Configuration Loading Integration
```gherkin
Given project path is provided
When run command executes
Then CLI calls load_config_with_project(project_path, global_config_path=config)
And .env file is loaded automatically (per Story 1.5)
And config validation errors display user-friendly message
```

### AC7: Error Handling with Exit Codes
```gherkin
Given an error occurs during execution
When error is ConfigError (missing/invalid config)
Then exit code is 2
And error message is displayed with Rich formatting

Given an error occurs during execution
When error is FileNotFoundError (project not found)
Then exit code is 1
And error message includes the path that wasn't found

Given execution completes successfully
Then exit code is 0
```

### AC8: Project Path Validation
```gherkin
Given user runs `bmad-assist run --project ./nonexistent`
When project path doesn't exist
Then error message indicates "Project directory not found: ./nonexistent"
And exit code is 1

Given user runs `bmad-assist run --project ./file.txt`
When project path is a file (not directory)
Then error message indicates "Project path must be a directory"
And exit code is 1
```

### AC9: Default Project Path
```gherkin
Given user runs `bmad-assist run` without --project
When no project path is specified
Then current working directory is used as project path
And this matches load_config_with_project() default behavior
```

### AC10: Verbose Output Option
```gherkin
Given user runs `bmad-assist run --verbose` or `-v`
When verbose mode is enabled
Then debug-level messages are displayed
And configuration loading details are shown
And file paths being processed are shown
```

### AC11: Quiet Mode Option
```gherkin
Given user runs `bmad-assist run --quiet` or `-q`
When quiet mode is enabled
Then only errors (exit code > 0) and final success message are displayed
And informational messages are suppressed (config loaded, paths resolved, debug info)
And logging level is set to WARNING
```

**Clarification - Message Categories:**
- **Errors** (always shown): ConfigError, FileNotFoundError, exceptions
- **Final result** (always shown): "Configuration loaded successfully" or error message
- **Informational** (suppressed in quiet): "Loading config from...", "Project path resolved to...", debug logs

---

## Tasks / Subtasks

- [x] Task 1: Verify dependencies and add Rich console integration (AC: 4)
  - [x] 1.0 Verify `rich` is available via `typer[all]` in pyproject.toml (should already be there)
  - [x] 1.1 Import Rich Console: `from rich.console import Console`
  - [x] 1.2 Create module-level console: `console = Console()`
  - [x] 1.3 Replace `typer.echo()` with `console.print()` throughout
  - [x] 1.4 Add helper functions for styled output: `_error()`, `_success()`, `_warning()`

- [x] Task 2: Enhance run command options (AC: 2, 10, 11)
  - [x] 2.1 Add `--verbose` / `-v` flag: `typer.Option(False, "--verbose", "-v")`
  - [x] 2.2 Add `--quiet` / `-q` flag: `typer.Option(False, "--quiet", "-q")`
  - [x] 2.3 Ensure `--verbose` and `--quiet` are mutually exclusive
  - [x] 2.4 Update help strings for all options

- [x] Task 3: Implement project path validation (AC: 1, 8, 9)
  - [x] 3.1 Resolve project path to absolute: `Path(project).resolve()`
  - [x] 3.2 Check if path exists: `if not project_path.exists()`
  - [x] 3.3 Check if path is directory: `if not project_path.is_dir()`
  - [x] 3.4 Display Rich-formatted errors for validation failures

- [x] Task 4: Integrate configuration loading (AC: 2, 6)
  - [x] 4.1 Import `load_config_with_project` from `bmad_assist.core.config`
  - [x] 4.2 Call `load_config_with_project(project_path, global_config_path=config)`
  - [x] 4.3 Handle `ConfigError` with user-friendly message
  - [x] 4.4 Log configuration loading in verbose mode

- [x] Task 5: Implement exit code handling (AC: 7)
  - [x] 5.1 Define exit codes as constants: `EXIT_SUCCESS = 0`, `EXIT_ERROR = 1`, `EXIT_CONFIG_ERROR = 2`
  - [x] 5.2 Wrap main logic in try/except for ConfigError → exit 2
  - [x] 5.3 Handle FileNotFoundError → exit 1
  - [x] 5.4 Handle unexpected exceptions → exit 1 with traceback in verbose mode

- [x] Task 6: Create main loop stub and delegation (AC: 5)
  - [x] 6.1 Create `src/bmad_assist/core/loop.py` with stub `run_loop()` function
  - [x] 6.2 Stub signature: `def run_loop(config: Config, project_path: Path) -> None`
  - [x] 6.3 Stub body: log "Main loop placeholder - see Epic 6 for implementation" and return
  - [x] 6.4 In cli.py: import `run_loop` from `bmad_assist.core.loop`
  - [x] 6.5 In cli.py: call `run_loop(loaded_config, project_path)` after successful config load
  - [x] 6.6 Export `run_loop` from `core/__init__.py`

- [x] Task 7: Setup logging integration (AC: 10, 11)
  - [x] 7.1 Configure logging level based on --verbose/--quiet flags
  - [x] 7.2 Use `logging.basicConfig(level=...)` at CLI start
  - [x] 7.3 Add RichHandler for formatted log output: `from rich.logging import RichHandler`

- [x] Task 8: Write comprehensive tests (AC: all)
  - [x] 8.1 Test run command with Rich output (mock console)
  - [x] 8.2 Test --verbose flag enables debug logging
  - [x] 8.3 Test --quiet flag suppresses non-error output
  - [x] 8.4 Test project path validation (nonexistent, file not dir)
  - [x] 8.5 Test config loading integration (valid config, invalid config)
  - [x] 8.6 Test exit codes (0 success, 1 error, 2 config error)
  - [x] 8.7 Test default project path (cwd)
  - [x] 8.8 Test --help output includes all options
  - [x] 8.9 Test run_loop() stub is called with correct args (mock and verify)
  - [x] 8.10 Test run_loop() stub exists in core/loop.py and is importable
  - [x] 8.11 Achieve >=95% coverage on cli.py AND core/loop.py

---

## Dev Notes

### Critical Architecture Requirements

**From architecture.md - MUST follow exactly:**

1. **CLI Entry Boundary:**
   > "cli.py → only parses args, calls core/loop.py"
   > "No business logic in CLI layer"

2. **Module Location:** `src/bmad_assist/cli.py` (extend existing)
3. **Console Output:** Rich console for all output
4. **Logging:** `from rich.logging import RichHandler`
5. **Naming Conventions:** PEP8 (snake_case functions)
6. **Type Hints:** Required on ALL functions
7. **Docstrings:** Google-style for all public APIs

### Implementation Strategy

**Rich Console Integration:**
```python
from rich.console import Console
from rich.panel import Panel

console = Console()

def _error(message: str) -> None:
    """Display error message with red styling."""
    console.print(f"[red]Error:[/red] {message}")

def _success(message: str) -> None:
    """Display success message with green styling."""
    console.print(f"[green]✓[/green] {message}")

def _warning(message: str) -> None:
    """Display warning message with yellow styling."""
    console.print(f"[yellow]Warning:[/yellow] {message}")
```

**Exit Code Constants:**
```python
# Exit codes following Unix conventions
EXIT_SUCCESS: int = 0
EXIT_ERROR: int = 1  # General error
EXIT_CONFIG_ERROR: int = 2  # Configuration/usage error
```

**Logging Configuration:**
```python
import logging
from rich.logging import RichHandler

def _setup_logging(verbose: bool, quiet: bool) -> None:
    """Configure logging based on verbosity flags."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
```

### Path Validation Pattern

```python
from pathlib import Path

def _validate_project_path(project: str) -> Path:
    """Validate and resolve project path.

    Args:
        project: Path to project directory.

    Returns:
        Resolved absolute Path.

    Raises:
        typer.Exit: If path doesn't exist or isn't a directory.
    """
    project_path = Path(project).resolve()

    if not project_path.exists():
        _error(f"Project directory not found: {project}")
        raise typer.Exit(code=EXIT_ERROR)

    if not project_path.is_dir():
        _error(f"Project path must be a directory, got file: {project}")
        raise typer.Exit(code=EXIT_ERROR)

    return project_path
```

### Error Handling Pattern

```python
from bmad_assist.core.loop import run_loop

@app.command()
def run(
    project: str = typer.Option(".", "--project", "-p", help="Path to project directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
) -> None:
    """Execute the main BMAD development loop."""
    # Setup logging first
    _setup_logging(verbose, quiet)

    try:
        # Validate project path
        project_path = _validate_project_path(project)

        # Load configuration (includes .env loading per Story 1.5)
        loaded_config = load_config_with_project(
            project_path=project_path,
            global_config_path=config,
        )

        _success(f"Configuration loaded from {project_path}")

        # Delegate to main loop (stub in this story, full impl in Epic 6)
        run_loop(loaded_config, project_path)

    except ConfigError as e:
        _error(str(e))
        raise typer.Exit(code=EXIT_CONFIG_ERROR)
    except Exception as e:
        _error(f"Unexpected error: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=EXIT_ERROR)
```

### IMPORTANT: Scope Boundaries

**This story handles:**
- Rich console integration for all output
- Project path validation and resolution
- Config loading via `load_config_with_project()`
- Verbose/quiet mode logging control
- Exit code handling
- Help text formatting

**NOT in scope for this story:**
- Main loop implementation (Epic 6, Story 6.5)
- Interactive config generation (Story 1.7)
- Progress bars or spinners (future enhancement)
- Signal handling (SIGINT/SIGTERM - Epic 6)

### Main Loop Stub Pattern (IMPORTANT)

**This story creates:** `src/bmad_assist/core/loop.py` with stub `run_loop()` function

```python
# src/bmad_assist/core/loop.py
"""Main loop orchestration (stub - full implementation in Epic 6)."""

import logging
from pathlib import Path

from bmad_assist.core.config import Config

logger = logging.getLogger(__name__)


def run_loop(config: Config, project_path: Path) -> None:
    """Execute the main BMAD development loop.

    Args:
        config: Loaded and validated configuration.
        project_path: Path to the project directory.

    Note:
        This is a stub. Full implementation in Epic 6, Story 6.5.
    """
    logger.info("Main loop placeholder - see Epic 6 for implementation")
    logger.debug(f"Config loaded: {config.model_dump_json()[:100]}...")
    logger.debug(f"Project path: {project_path}")
```

**Why stub instead of placeholder comment:**
1. Validates the import path works (catches `ImportError` early)
2. Tests can verify `run_loop()` is actually called
3. Clean interface for Epic 6 to implement
4. Follows architecture: `cli.py` → `core/loop.py` boundary

---

## Technical Requirements

### From PRD (FR38 - partial)

| FR | Requirement | This Story's Implementation |
|----|-------------|----------------------------|
| FR38 | System can generate config file via CLI questionnaire when config is missing | Partial - config loading; questionnaire is Story 1.7 |

### From Architecture

**CLI Entry Boundary (architecture.md):**
> "cli.py → only parses args, calls core/loop.py"
> "No business logic in CLI layer"

**Example from architecture:**
```
CLI (cli.py)
    │
    ▼
Main Loop (core/loop.py) ◄──► State (state.yaml)
                         ◄──► Config (config.yaml)
```

### Dependencies

- **Story 1.4 (DONE):** `load_config_with_project()` - Config loading integration
- **Story 1.5 (DONE):** `load_env_file()` - Automatic .env loading
- **Existing:** Typer framework already in pyproject.toml
- **Existing:** Rich already available via `typer[all]`

### Integration with Existing Code

Story 1.6 integrates with:
1. `load_config_with_project()` - Story 1.4 config loading
2. `load_env_file()` - Story 1.5 .env loading (automatic via load_config_with_project)
3. `ConfigError` - Story 1.2 exception handling
4. Logging system - Stories 1.3-1.5 established patterns

---

## Architecture Compliance

### Stack Verification
- [x] Python 3.11+ type hints - Required
- [x] Typer CLI framework - Already in pyproject.toml
- [x] Rich console - Available via typer[all]

### Structure Verification
- [x] Location: `src/bmad_assist/cli.py` (extend existing)
- [x] Tests: `tests/test_cli.py` (extend existing)
- [x] Entry point: `bmad-assist` via pyproject.toml

### Pattern Verification
- [x] PEP8 naming conventions
- [x] Google-style docstrings
- [x] No business logic in CLI layer
- [x] Exit codes follow Unix conventions

---

## Developer Context

### Git Intelligence Summary

**Recent commits (from git log):**
1. `fix(core): address Multi-LLM code review findings for story 1.5` - _mask_credential fixes
2. `feat(core): implement .env credential loading for Story 1.5` - load_env_file()
3. `docs(story): complete Multi-LLM validation synthesis for story 1.5` - Validation done
4. `docs: add AGENTS.md repository guidelines` - Agent guidelines
5. `docs(power-prompts): fix action_required wording in create-story` - Prompt updates

**Files from most recent commits:**
- `src/bmad_assist/core/config.py` - Extended with load_env_file, credential masking
- `tests/core/test_config.py` - 175 tests, 97% coverage
- `.env.example` - Template file created

**Key Patterns from Story 1.5:**
- `load_config_with_project()` automatically calls `load_env_file()` first
- Logger configured per module: `logger = logging.getLogger(__name__)`
- ConfigError for all configuration-related errors
- Tests use `tmp_path` fixture and `monkeypatch` for env vars

### Previous Story Learnings (1.5)

**What worked well:**
- Integration with existing `load_config_with_project()`
- Debug logging for troubleshooting
- Graceful handling of missing files

**Issues encountered and resolved:**
- `_mask_credential` needed None handling - fixed
- Permission check needed 0o400 in addition to 0o600 - fixed
- `types-python-dotenv` package doesn't exist - removed

**Code Review Insights (from story 1.5 code review):**
- Handle None values in helper functions
- Consider edge cases (permissions, missing files)
- Clean up dev dependencies that don't exist

### Files Modified in Previous Story

**Story 1.5 file list:**
- `src/bmad_assist/core/config.py` - Added load_env_file(), _check_env_file_permissions(), _mask_credential()
- `src/bmad_assist/core/__init__.py` - Exported load_env_file
- `tests/core/test_config.py` - Added 32 tests for Story 1.5
- `.env.example` - New template file
- `pyproject.toml` - Added python-dotenv

### Existing Code to Extend

**From cli.py (current implementation):**
```python
"""Typer CLI entry point for bmad-assist."""

import typer

app = typer.Typer(
    name="bmad-assist",
    help="CLI tool for automating BMAD methodology development loop",
    no_args_is_help=True,
)

@app.command()
def run(
    project: str = typer.Option(".", "--project", "-p", help="Path to project directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to configuration file"),
) -> None:
    """Execute the main BMAD development loop."""
    typer.echo(f"bmad-assist: project={project}, config={config}")
    typer.echo("Main loop not implemented yet - see Epic 6")
```

---

## File Structure

### Files to Create

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/core/loop.py` | Main loop stub with `run_loop()` function | +25-30 |
| `tests/core/test_loop.py` | Tests for loop stub | +20-30 |

### Files to Modify

| File | Changes | Lines (est.) |
|------|---------|--------------|
| `src/bmad_assist/cli.py` | Add Rich console, path validation, config loading, exit codes, run_loop() call | +80-100 |
| `src/bmad_assist/core/__init__.py` | Export `run_loop` | +1 |
| `tests/test_cli.py` | Extend with config integration tests, error handling tests, run_loop mock | +100-120 |

### Expected Final cli.py Structure

```python
"""Typer CLI entry point for bmad-assist."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from bmad_assist.core.config import load_config_with_project
from bmad_assist.core.exceptions import ConfigError
from bmad_assist.core.loop import run_loop

# Exit codes
EXIT_SUCCESS: int = 0
EXIT_ERROR: int = 1
EXIT_CONFIG_ERROR: int = 2

# Rich console for output
console = Console()

app = typer.Typer(
    name="bmad-assist",
    help="CLI tool for automating BMAD methodology development loop",
    no_args_is_help=True,
)

# ... helper functions (_error, _success, _warning, _setup_logging, _validate_project_path)
# ... run command implementation calling run_loop(config, project_path)
```

---

## Testing Requirements

### Test Cases to Add (tests/test_cli.py)

```python
"""Extended tests for Story 1.6: Typer CLI Entry Point."""

import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from bmad_assist.cli import app, EXIT_SUCCESS, EXIT_ERROR, EXIT_CONFIG_ERROR

runner = CliRunner()


class TestRichOutput:
    """Tests for Rich console integration."""

    def test_error_output_uses_rich_formatting(self, tmp_path: Path) -> None:
        """AC4: Errors use Rich formatting."""
        result = runner.invoke(app, ["run", "--project", str(tmp_path / "nonexistent")])
        assert result.exit_code == EXIT_ERROR
        # Rich output will have the error message
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestProjectPathValidation:
    """Tests for project path validation."""

    def test_nonexistent_project_path_exits_with_error(self, tmp_path: Path) -> None:
        """AC8: Nonexistent path returns exit code 1."""
        result = runner.invoke(app, ["run", "--project", str(tmp_path / "nonexistent")])
        assert result.exit_code == EXIT_ERROR
        assert "not found" in result.output.lower()

    def test_file_as_project_path_exits_with_error(self, tmp_path: Path) -> None:
        """AC8: File (not dir) as project path returns exit code 1."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        result = runner.invoke(app, ["run", "--project", str(file_path)])
        assert result.exit_code == EXIT_ERROR
        assert "directory" in result.output.lower()

    def test_default_project_path_uses_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC9: Default project path is cwd."""
        # Create minimal config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["run", "--config", str(config_file)])
        # Should not fail due to missing project path
        assert "error" not in result.output.lower() or "config" in result.output.lower()


class TestConfigIntegration:
    """Tests for configuration loading integration."""

    def test_valid_config_loads_successfully(self, tmp_path: Path) -> None:
        """AC6: Valid config loads without error."""
        # Create project dir with config
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")

        result = runner.invoke(app, [
            "run",
            "--project", str(project_dir),
            "--config", str(global_config),
        ])

        # Should succeed (main loop not implemented, but config loads)
        assert result.exit_code == EXIT_SUCCESS or "main loop" in result.output.lower()

    def test_invalid_config_exits_with_config_error(self, tmp_path: Path) -> None:
        """AC7: Invalid config returns exit code 2."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        config = tmp_path / "config.yaml"
        config.write_text("invalid: yaml: content: [")

        result = runner.invoke(app, [
            "run",
            "--project", str(project_dir),
            "--config", str(config),
        ])

        assert result.exit_code == EXIT_CONFIG_ERROR


class TestVerboseQuietModes:
    """Tests for verbose and quiet mode flags."""

    def test_verbose_flag_accepted(self, tmp_path: Path) -> None:
        """AC10: --verbose flag is accepted."""
        result = runner.invoke(app, ["run", "--verbose", "--help"])
        # Just check it doesn't crash with the flag
        assert "--verbose" in result.output or result.exit_code == 0

    def test_quiet_flag_accepted(self, tmp_path: Path) -> None:
        """AC11: --quiet flag is accepted."""
        result = runner.invoke(app, ["run", "--quiet", "--help"])
        # Just check it doesn't crash with the flag
        assert "--quiet" in result.output or result.exit_code == 0

    def test_verbose_short_form(self) -> None:
        """AC10: -v short form works."""
        result = runner.invoke(app, ["run", "-v", "--help"])
        assert result.exit_code == 0

    def test_quiet_short_form(self) -> None:
        """AC11: -q short form works."""
        result = runner.invoke(app, ["run", "-q", "--help"])
        assert result.exit_code == 0


class TestExitCodes:
    """Tests for exit code behavior."""

    def test_exit_success_is_zero(self) -> None:
        """AC7: Success exit code is 0."""
        from bmad_assist.cli import EXIT_SUCCESS
        assert EXIT_SUCCESS == 0

    def test_exit_error_is_one(self) -> None:
        """AC7: General error exit code is 1."""
        from bmad_assist.cli import EXIT_ERROR
        assert EXIT_ERROR == 1

    def test_exit_config_error_is_two(self) -> None:
        """AC7: Config error exit code is 2."""
        from bmad_assist.cli import EXIT_CONFIG_ERROR
        assert EXIT_CONFIG_ERROR == 2


class TestHelpOutput:
    """Tests for help text."""

    def test_run_help_shows_all_options(self) -> None:
        """AC3: Help shows all options."""
        result = runner.invoke(app, ["run", "--help"])
        assert "--project" in result.output
        assert "--config" in result.output
        assert "-p" in result.output
        assert "-c" in result.output
```

### Coverage Target
- **>=95% coverage** on cli.py
- All exit code paths tested
- Config loading integration tested
- Path validation edge cases tested

### Mocking Strategy
- Use `tmp_path` fixture for test directories and configs
- Use `monkeypatch.chdir()` for cwd tests
- Mock `load_config_with_project` for isolated tests if needed
- Use `CliRunner` from typer.testing for CLI invocation

---

## Library/Framework Requirements

### Rich Console Usage

```python
from rich.console import Console
from rich.panel import Panel

console = Console()

# Basic output
console.print("Hello, [bold magenta]World[/bold magenta]!")

# Error styling
console.print("[red]Error:[/red] Something went wrong")

# Success styling
console.print("[green]✓[/green] Operation completed")

# Warning styling
console.print("[yellow]Warning:[/yellow] Proceed with caution")
```

### Rich Logging Handler

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("bmad_assist")
```

### Typer with Rich

```python
import typer
from rich.console import Console

app = typer.Typer(rich_markup_mode="rich")
console = Console()

@app.command()
def run(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable [bold]debug[/bold] output"),
) -> None:
    """Execute the [bold blue]BMAD[/bold blue] development loop."""
    ...
```

---

## Project Context Reference

**Project:** bmad-assist - CLI tool for automating BMAD methodology development loop

**Key Architecture Patterns:**
- Config singleton via `get_config()` - Stories 1.2-1.5 established this
- CLI boundary: parse args, call core/loop.py
- Rich console for all user-facing output
- Logging via `logger = logging.getLogger(__name__)`

**Critical Rules:**
- Python 3.11+, PEP8 naming, type hints on all functions
- Google-style docstrings for public APIs
- Test coverage >=95% on new code
- mypy strict mode, ruff linting
- **No business logic in CLI layer**

---

## References

- [Source: docs/architecture.md#CLI-Entry-Boundary] - CLI only parses args, calls core/loop.py
- [Source: docs/architecture.md#Project-Structure] - cli.py location
- [Source: docs/architecture.md#Logging-Pattern] - Rich logging handler
- [Source: docs/prd.md#CLI-Tool-Specific-Requirements] - Command structure
- [Source: docs/epics.md#Story-1.6] - Original story definition
- [Source: Story 1.4] - load_config_with_project() integration
- [Source: Story 1.5] - .env loading (automatic via config)

---

## Verification Checklist

Before marking as complete, verify:

**CLI Implementation:**
- [x] Rich console imported and used for all output
- [x] `_error()`, `_success()`, `_warning()` helper functions created
- [x] `--verbose` / `-v` flag implemented
- [x] `--quiet` / `-q` flag implemented
- [x] Project path validation implemented (exists, is_dir)
- [x] `load_config_with_project()` integration working
- [x] Exit codes defined: EXIT_SUCCESS=0, EXIT_ERROR=1, EXIT_CONFIG_ERROR=2
- [x] ConfigError caught and exits with code 2
- [x] FileNotFoundError caught and exits with code 1
- [x] Logging configured based on verbose/quiet flags
- [x] RichHandler used for logging output

**Main Loop Stub:**
- [x] `src/bmad_assist/core/loop.py` created with `run_loop()` function
- [x] `run_loop()` accepts `config: Config` and `project_path: Path`
- [x] `run_loop()` logs placeholder message and returns
- [x] `run_loop` exported from `core/__init__.py`
- [x] `cli.py` imports and calls `run_loop()` after config load

**Quality Gates:**
- [x] `mypy src/` reports no errors
- [x] `ruff check src/` reports no issues
- [x] `pytest tests/` passes all tests (224 tests pass)
- [x] Coverage >=95% on cli.py (96%) AND core/loop.py (100%)

---

## Dev Agent Record

### Context Reference
- Story ID: 1.6
- Story Key: 1-6-typer-cli-entry-point
- Epic: 1 - Project Foundation & CLI Infrastructure
- Previous Story: 1.5 (done) - Credentials Security with .env

### Agent Model Used
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
- No debug issues encountered during implementation

### Completion Notes List
- **Rich Console Integration**: Implemented `_error()`, `_success()`, `_warning()` helper functions with Rich formatting. Module-level `Console()` instance created at `cli.py:24`.
- **Verbose/Quiet Flags**: Added mutually exclusive flags with warning when both specified. Verbose takes precedence per AC10/AC11.
- **Project Path Validation**: `_validate_project_path()` resolves paths to absolute and validates existence + is_dir. Returns EXIT_ERROR (1) on failure.
- **Config Loading Integration**: Calls `load_config_with_project()` with project_path and optional global_config_path. ConfigError → EXIT_CONFIG_ERROR (2).
- **Main Loop Stub**: Created `core/loop.py` with `run_loop(config, project_path)` stub that logs placeholder message. Exported from `core/__init__.py`.
- **Logging Integration**: `_setup_logging()` configures RichHandler with level based on verbose/quiet flags. Clears existing handlers to avoid duplicates.
- **Exit Code Handling**: EXIT_SUCCESS=0, EXIT_ERROR=1, EXIT_CONFIG_ERROR=2. Proper try/except chain handles ConfigError, typer.Exit, and generic exceptions.
- **Test Coverage**: 49 new tests for CLI + loop. 96% coverage on cli.py, 100% on loop.py. Total 224 tests pass.

### Change Log
- 2025-12-10: Story 1.6 implementation complete - Typer CLI entry point with Rich console, verbose/quiet flags, path validation, config loading, exit codes, and run_loop() stub

### File List
- `src/bmad_assist/cli.py` - Enhanced CLI with Rich console, path validation, config loading, exit codes (Modified)
- `src/bmad_assist/core/loop.py` - New file: run_loop() stub for main loop orchestration (Created)
- `src/bmad_assist/core/__init__.py` - Added run_loop export (Modified)
- `tests/test_cli.py` - Comprehensive CLI tests covering all ACs (Modified - rewritten)
- `tests/core/test_loop.py` - Tests for run_loop() stub (Created)
- `docs/sprint-artifacts/sprint-status.yaml` - Updated 1-6 status to in-progress, then review (Modified)
