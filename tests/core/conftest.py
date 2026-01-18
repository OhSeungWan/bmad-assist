"""Pytest fixtures for bmad_assist.core tests.

Shared fixtures for configuration tests extracted from test_config.py
as part of Story 1.8 (Test Suite Refactoring).

State fixtures added as part of test_state.py refactoring.

Fixture Organization:
- reset_config_singleton: Auto-reset for test isolation (autouse=True)
- sample_minimal_config: Minimal valid YAML config string
- sample_full_config: Full config with all optional fields
- write_config: Factory fixture to write config files to tmp_path
- default_state: State with default values
- populated_state: State with all fields populated
- state_as_dict: State data as dict (simulating YAML load)
- state_for_persistence: State for persistence tests
- temp_state_file: Temporary file path for state tests
- saved_state_file: Pre-saved state file for load tests
- corrupted_yaml_file: Invalid YAML syntax file
- invalid_schema_file: Valid YAML but invalid State schema

Usage in tests:
    def test_something(write_config, sample_minimal_config):
        config_path = write_config(sample_minimal_config)
        # ... use config_path
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from bmad_assist.core.config import _reset_config
from bmad_assist.core.state import Phase, State, save_state


@pytest.fixture(autouse=True)
def reset_config_singleton() -> None:
    """Reset config singleton before and after each test.

    This fixture ensures test isolation by clearing the config singleton
    state. The autouse=True makes it run automatically for all tests
    in the core directory.
    """
    _reset_config()
    yield
    _reset_config()


@pytest.fixture
def sample_minimal_config() -> str:
    """Minimal valid config YAML for testing.

    Contains only required fields for a valid configuration.
    """
    return """\
providers:
  master:
    provider: claude
    model: opus_4
"""


@pytest.fixture
def sample_full_config() -> str:
    """Full config YAML with all optional fields.

    Contains master, multi providers, and all optional settings.
    """
    return """\
providers:
  master:
    provider: claude
    model: opus_4
    settings: /path/to/settings.json
  multi:
    - provider: gemini
      model: gemini_2_5_pro
    - provider: codex
      model: gpt_5_1
state_path: ~/.bmad-assist/state.yaml
timeout: 300
"""


@pytest.fixture
def write_config(tmp_path: Path) -> Callable[[str, str], Path]:
    """Create a config file writer for temporary directory.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        A function that writes content to a file and returns the path.

    """

    def _write(content: str, filename: str = "config.yaml") -> Path:
        path = tmp_path / filename
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True)
        path.write_text(content)
        return path

    return _write


# =============================================================================
# State Fixtures (from test_state.py refactoring)
# =============================================================================


@pytest.fixture
def default_state() -> State:
    """Create State with default values."""
    return State()


@pytest.fixture
def populated_state() -> State:
    """Create State with all fields populated."""
    return State(
        current_epic=3,
        current_story="3.1",
        current_phase=Phase.DEV_STORY,
        completed_stories=["1.1", "1.2", "2.1", "2.2", "2.3"],
        started_at=datetime(2025, 12, 10, 8, 0, 0),
        updated_at=datetime(2025, 12, 10, 14, 30, 0),
    )


@pytest.fixture
def state_as_dict() -> dict:
    """State data as dict (simulating YAML load)."""
    return {
        "current_epic": 2,
        "current_story": "2.3",
        "current_phase": "code_review",
        "completed_stories": ["1.1", "1.2"],
        "started_at": "2025-12-10T08:00:00",
        "updated_at": "2025-12-10T14:30:00",
    }


@pytest.fixture
def state_for_persistence() -> State:
    """Create State with all fields for persistence tests."""
    return State(
        current_epic=3,
        current_story="3.1",
        current_phase=Phase.DEV_STORY,
        completed_stories=["1.1", "1.2", "2.1"],
        started_at=datetime(2025, 12, 10, 8, 0, 0),
        updated_at=datetime(2025, 12, 10, 14, 30, 0),
    )


@pytest.fixture
def temp_state_file(tmp_path: Path) -> Path:
    """Provide temporary file path for state tests."""
    return tmp_path / "state.yaml"


@pytest.fixture
def saved_state_file(tmp_path: Path) -> tuple[Path, State]:
    """Create a state file with typical values for load tests."""
    state = State(
        current_epic=3,
        current_story="3.1",
        current_phase=Phase.DEV_STORY,
        completed_stories=["1.1", "1.2", "2.1"],
        started_at=datetime(2025, 12, 10, 8, 0, 0),
        updated_at=datetime(2025, 12, 10, 14, 30, 0),
    )
    path = tmp_path / "state.yaml"
    save_state(state, path)
    return path, state


@pytest.fixture
def corrupted_yaml_file(tmp_path: Path) -> Path:
    """Create a file with invalid YAML syntax."""
    path = tmp_path / "corrupted.yaml"
    path.write_text("invalid: yaml: content: [", encoding="utf-8")
    return path


@pytest.fixture
def invalid_schema_file(tmp_path: Path) -> Path:
    """Create a file with valid YAML but invalid State schema."""
    path = tmp_path / "invalid_schema.yaml"
    data = {
        "current_epic": "not-an-int",
        "current_phase": "invalid_phase",
    }
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path
