# Story 1.8: Test Suite Refactoring

**Status:** done
**Story Points:** 2

---

## Story

**As a** developer,
**I want** test files split into logical modules,
**So that** tests are maintainable and easy to navigate.

### Business Context

Epic 1 generated 294 tests across 4701 lines of test code. The main problem is `test_config.py` with 3003 lines - the file contains tests from 4 different stories (1.2-1.5), making navigation and maintenance difficult.

Refactoring before Epic 2 will prevent further tech debt accumulation.

### Success Criteria

- No test file exceeds 500 lines
- All 294 tests still pass
- Coverage remains >=95%
- Shared fixtures extracted to `conftest.py`
- Test structure mirrors source code structure

---

## Acceptance Criteria

### AC1: test_config.py split into modules
```gherkin
Given test_config.py has 3003 lines
When refactoring is complete
Then separate files exist:
  - test_config_models.py (Story 1.2 - Pydantic models)
  - test_config_loading.py (Story 1.3 - global config loading)
  - test_config_project.py (Story 1.4 - project override, deep merge)
  - test_config_env.py (Story 1.5 - .env, credentials)
And none of them exceeds 500 lines
And test_config.py is deleted
```

### AC2: Shared fixtures in conftest.py
```gherkin
Given tests use repeating fixtures
When refactoring is complete
Then shared fixtures are in tests/core/conftest.py
And fixtures include: sample configs, tmp directories, env setup
And there is no fixture duplication between files
```

### AC3: All tests pass
```gherkin
Given refactoring is complete
And baseline was measured in Task 1.4
When pytest tests/ is run
Then all 294 tests pass
And there are no new warnings
And execution time remains within ±10% of baseline (Task 1.4)
And test inventory count is identical to baseline
```

### AC4: Coverage unchanged
```gherkin
Given refactoring is complete
When pytest --cov is run
Then coverage on core/config.py >= 95%
And coverage on cli.py >= 95%
And no module lost coverage
```

---

## Future Enhancements (Out of Scope)

### test_cli.py Refactoring
- **Current:** 871 lines (acceptable but large)
- **Future story:** Could be split into test_cli_run.py, test_cli_validation.py, test_cli_wizard.py
- **Benefit:** Improved organization for Epic 2 CLI additions
- **Estimated:** +1 SP if done separately

---

## Tasks / Subtasks

- [x] Task 1: Analyze test_config.py and plan split
  - [x] 1.1 Identify test classes per story
  - [x] 1.2 Identify shared fixtures to extract
  - [x] 1.3 Create mapping: test class → new file
  - [x] 1.4 Create test baseline:
    ```bash
    pytest --collect-only | grep "test_" | wc -l > test_count_before.txt
    pytest tests/ -v --tb=no | tee test_baseline.txt
    pytest tests/ --durations=0 | tee test_timing_baseline.txt
    ```

- [x] Task 2: Create conftest.py with shared fixtures
  - [x] 2.1 Create tests/core/conftest.py
  - [x] 2.2 Move repeating fixtures (sample configs, reset_config, etc.)
  - [x] 2.3 Verify fixtures work with pytest
  - [x] 2.4 Verify: no direct fixture imports after extraction
  - [x] 2.5 Run pytest --setup-show to verify fixture execution order

- [x] Task 3: Split test_config.py
  - [x] 3.1 Create test_config_models.py (Pydantic model tests from Story 1.2)
  - [x] 3.2 Create test_config_loading.py (load_global_config tests from Story 1.3)
  - [x] 3.3 Create test_config_project.py (deep merge, project override tests from Story 1.4)
  - [x] 3.4 Create test_config_env.py (.env, credentials tests from Story 1.5)
  - [x] 3.5 Delete original test_config.py
  - [x] 3.6 Run pytest and fix imports
  - [x] 3.7 Validate test integrity:
    ```bash
    # Compare inventory
    pytest --collect-only | grep "test_" | wc -l > test_count_after.txt
    diff test_count_before.txt test_count_after.txt  # MUST be identical (294)

    # Compare results
    pytest tests/ -v --tb=no | tee test_results_after.txt
    # Compare pass/fail counts with baseline
    ```
  - [x] 3.8 Check circular imports: `python -m py_compile tests/core/*.py`

- [x] Task 4: Final validation
  - [x] 4.1 pytest tests/ - all 294 tests pass
  - [x] 4.2 pytest --cov - coverage >= 95%
  - [x] 4.3 Verify no file > 500 lines: `wc -l tests/**/*.py | sort -n`
  - [x] 4.4 mypy tests/ - no type errors (only import-untyped warnings, expected)
  - [x] 4.5 ruff check tests/ - no linting errors
  - [x] 4.6 Compare execution time:
    ```bash
    pytest tests/ --durations=0 | tee test_timing_after.txt
    # Compare total time with baseline - must be within ±10%
    ```
  - [x] 4.7 Each file runs independently: `pytest tests/core/test_config_models.py` (repeat for each)

---

## Dev Notes

### Rollback Strategy

**Pre-Refactor Safety:**
1. Create feature branch: `git checkout -b feature/story-1.8-test-refactor`
2. Commit current state: `git commit -am "baseline before test refactor"`
3. Document test baseline (Task 1.4)

**Rollback Criteria (Any of these triggers rollback):**
- Test count changes (not 294)
- Any test fails that passed before
- Coverage drops below 95% on any module
- mypy introduces new errors
- Import errors occur

**Rollback Procedure:**
```bash
git checkout main
git branch -D feature/story-1.8-test-refactor
# Analyze what went wrong, start over with better approach
```

### Fixture Extraction Rules

**Extract to conftest.py IF:**
- Fixture is used in 2+ test files
- Fixture provides common test data (sample configs, paths)
- Fixture has no file-specific logic

**Keep in test file IF:**
- Fixture is used in only 1 file
- Fixture is tightly coupled to specific test class
- Fixture contains test-specific mocks

**Example Decision Tree:**
```python
# reset_config_singleton - Used by all config tests → conftest.py ✅
# sample_minimal_config - Used by 4 files → conftest.py ✅
# mock_cli_provider - Used only in test_cli.py → Keep in test_cli.py ❌
```

### Original Test Structure

```
tests/
├── __init__.py              (1 line)
├── conftest.py              (1 line) ← almost empty!
├── test_cli.py              (871 lines) ← for review
└── core/
    ├── __init__.py          (1 line)
    ├── test_config.py       (3003 lines) ← MAIN PROBLEM
    ├── test_config_generator.py (698 lines) ← OK
    └── test_loop.py         (126 lines) ← OK
```

### Target Structure

```
tests/
├── __init__.py
├── conftest.py              ← global fixtures
├── test_cli.py              (< 500 lines) or split
└── core/
    ├── __init__.py
    ├── conftest.py          ← core fixtures (sample configs, reset helpers)
    ├── test_config_models.py    ← Story 1.2 (Pydantic)
    ├── test_config_loading.py   ← Story 1.3 (global loading)
    ├── test_config_project.py   ← Story 1.4 (project override)
    ├── test_config_env.py       ← Story 1.5 (.env)
    ├── test_config_generator.py ← Story 1.7 (unchanged)
    └── test_loop.py             ← Story 1.6 stub (unchanged)
```

### Classes to Move from test_config.py

Based on Story 1.2-1.5, probable split:

**test_config_models.py (Story 1.2):**
- TestProviderConfig
- TestProvidersConfig
- TestPowerPromptsConfig
- TestBmadPathsConfig
- TestConfig
- TestConfigValidation

**test_config_loading.py (Story 1.3):**
- TestLoadYamlFile
- TestLoadGlobalConfig
- TestConfigSingleton

**test_config_project.py (Story 1.4):**
- TestDeepMerge
- TestProjectConfigOverride
- TestLoadConfigWithProject
- TestListReplacement
- TestDictDeepMerge

**test_config_env.py (Story 1.5):**
- TestLoadEnvFile
- TestEnvFilePermissions
- TestCredentialMasking
- TestEnvIntegration
- TestEnvExampleFile
- TestGitignore

### Fixtures to Extract

```python
# tests/core/conftest.py

import pytest
from pathlib import Path
from bmad_assist.core.config import _reset_config

@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset config singleton before each test."""
    _reset_config()
    yield
    _reset_config()

@pytest.fixture
def sample_minimal_config() -> dict:
    """Minimal valid config for testing."""
    return {
        "providers": {
            "master": {
                "provider": "claude",
                "model": "opus_4",
            }
        }
    }

@pytest.fixture
def sample_full_config() -> dict:
    """Full config with all optional fields."""
    return {
        "providers": {
            "master": {
                "provider": "claude",
                "model": "opus_4",
                "settings_file": "/path/to/settings.json",
            },
            "multi": [
                {"provider": "gemini", "model": "gemini_2_5_pro"},
            ],
        },
        "state_path": "~/.bmad-assist/state.yaml",
        "timeout": 300,
    }

@pytest.fixture
def write_config(tmp_path: Path):
    """Factory fixture to write config files."""
    def _write(content: str, filename: str = "config.yaml") -> Path:
        path = tmp_path / filename
        path.write_text(content)
        return path
    return _write
```

### IMPORTANT: Do not change test logic

This story is ONLY structural refactoring:
- DO NOT add new tests
- DO NOT remove existing tests
- DO NOT change assertions
- ONLY move code between files

---

## Technical Requirements

### Dependencies
- pytest >= 7.0
- pytest-cov for coverage

### Validation Commands

```bash
# All tests
pytest tests/ -v

# Coverage
pytest tests/ --cov=src/bmad_assist --cov-report=term-missing

# Only core tests
pytest tests/core/ -v

# Check lines per file
wc -l tests/**/*.py | sort -n

# mypy on tests
mypy tests/

# ruff on tests
ruff check tests/
```

---

## Verification Checklist

- [x] test_config.py deleted
- [x] 10 new test files in tests/core/ (more granular split than planned)
- [x] Each file < 500 lines (verified: max 464 lines)
- [x] conftest.py with shared fixtures (reset_config_singleton, sample_minimal_config, sample_full_config, write_config)
- [x] pytest tests/ - 294 tests PASS
- [x] Coverage >= 95% on core modules (97% achieved)
- [x] mypy tests/ - only import-untyped warnings (expected, no py.typed marker)
- [x] ruff check tests/ - 0 errors

---

## References

- [Source: Story 1.2] - test_config_models.py content
- [Source: Story 1.3] - test_config_loading.py content
- [Source: Story 1.4] - test_config_project.py content
- [Source: Story 1.5] - test_config_env.py content
- [Source: docs/architecture.md#Testing] - Test patterns

---

## Dev Agent Record

### Context Reference
- Story ID: 1.8
- Story Key: 1-8-test-suite-refactoring
- Epic: 1 - Project Foundation & CLI Infrastructure (tech debt cleanup)
- Previous Story: 1.7 (review) - Interactive Config Generation

### Agent Model Used
- Initial implementation: Claude Sonnet 4.5
- Code review synthesis: Claude Opus 4.5 (Master LLM)

### Completion Notes List
- Refactored test_config.py (3003 lines) into 10 focused test modules
- All 294 tests passing (verified with `pytest tests/`)
- Coverage: 97% on core modules (exceeds >=95% requirement)
- Test execution time: 0.96-1.07s (within ±10% tolerance)
- Created conftest.py with 4 shared fixtures:
  - `reset_config_singleton` (autouse=True for test isolation)
  - `sample_minimal_config` (minimal valid YAML config)
  - `sample_full_config` (full config with all optional fields)
  - `write_config` (factory fixture for writing config files)
- All refactored files under 500 lines per AC1 (max: 464 lines)
- No test logic changed - pure refactoring
- Fixed unused variable in test_config_generator.py (ruff F841)
- mypy warnings are expected (import-untyped due to missing py.typed marker)

### File List
**Created:**
- tests/core/conftest.py (97 lines - expanded with shared fixtures)
- tests/core/test_config_models.py (325 lines)
- tests/core/test_config_models_singleton.py (293 lines)
- tests/core/test_config_loading.py (276 lines)
- tests/core/test_config_loading_edge_cases.py (397 lines)
- tests/core/test_config_project.py (363 lines)
- tests/core/test_config_project_errors.py (464 lines)
- tests/core/test_config_project_merge.py (307 lines)
- tests/core/test_config_deep_merge.py (184 lines)
- tests/core/test_config_env.py (393 lines)
- tests/core/test_config_env_edge_cases.py (135 lines)

**Deleted:**
- tests/core/test_config.py (3003 lines)

**Modified:**
- .gitignore (added test baseline artifacts)
- tests/core/test_config_generator.py (fixed unused variable)
