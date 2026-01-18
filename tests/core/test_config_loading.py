"""Tests for global configuration loading.

Story 1.3 tests (AC1-AC6):
- AC1: Global config file loading
- AC2: Missing optional fields use defaults
- AC3: ConfigError for malformed YAML
- AC4: ConfigError when file missing
- AC5: Path expansion in loaded config
- AC6: Integration with existing singleton

Note: Tests for AC7-AC10 (edge cases) are in test_config_loading_edge_cases.py.
Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

from pathlib import Path

import pytest

from bmad_assist.core.config import (
    GLOBAL_CONFIG_PATH,
    Config,
    get_config,
    load_global_config,
)
from bmad_assist.core.exceptions import ConfigError


class TestGlobalConfigConstants:
    """Tests for Story 1.3: Global config constants."""

    def test_global_config_path_is_in_home_directory(self) -> None:
        """GLOBAL_CONFIG_PATH points to ~/.bmad-assist/config.yaml."""
        assert Path.home() / ".bmad-assist" / "config.yaml" == GLOBAL_CONFIG_PATH


# === AC1: Global Config File Loading ===


class TestGlobalConfigLoading:
    """Tests for AC1: Global config file loading."""

    def test_load_valid_yaml_config(self, tmp_path: Path) -> None:
        """Valid YAML config file is loaded and validated."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        config = load_global_config(path=config_file)
        assert config.providers.master.provider == "claude"
        assert config.providers.master.model == "opus_4"

    def test_load_config_populates_singleton(self, tmp_path: Path) -> None:
        """load_global_config populates the singleton."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: codex
    model: o3
"""
        )
        load_global_config(path=config_file)
        retrieved = get_config()
        assert retrieved.providers.master.provider == "codex"

    def test_load_config_returns_config_instance(self, tmp_path: Path) -> None:
        """load_global_config returns Config instance."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        config = load_global_config(path=config_file)
        assert isinstance(config, Config)


# === AC2: Missing Optional Fields Use Defaults ===


class TestDefaultValuesFromFile:
    """Tests for AC2: Missing optional fields use defaults from Story 1.2."""

    def test_minimal_config_gets_defaults(self, tmp_path: Path) -> None:
        """Minimal config with only required fields gets defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        config = load_global_config(path=config_file)

        # Verify defaults from Story 1.2
        assert config.providers.multi == []
        assert config.power_prompts.set_name is None
        assert config.power_prompts.variables == {}
        assert config.bmad_paths.prd is None
        assert config.bmad_paths.architecture is None
        assert config.bmad_paths.epics is None
        assert config.bmad_paths.stories is None

    def test_state_path_default_is_expanded(self, tmp_path: Path) -> None:
        """Default state_path is None; get_state_path() resolves to default."""
        from bmad_assist.core.state import get_state_path

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        config = load_global_config(path=config_file)
        # Default state_path is None, get_state_path() provides resolved default
        assert config.state_path is None
        resolved = get_state_path(config)
        assert "~" not in str(resolved)
        assert str(resolved).endswith(".bmad-assist/state.yaml")


# === AC3: ConfigError for Malformed YAML ===


class TestMalformedYaml:
    """Tests for AC3: ConfigError for malformed YAML."""

    def test_invalid_yaml_syntax_raises_error(self, tmp_path: Path) -> None:
        """Invalid YAML syntax raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: syntax:")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        # Error message should mention YAML
        error_msg = str(exc_info.value).lower()
        assert "yaml" in error_msg

    def test_unclosed_bracket_raises_error(self, tmp_path: Path) -> None:
        """Unclosed bracket in YAML raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: [unclosed")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert "yaml" in str(exc_info.value).lower()

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        """Error message includes file path."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: [unclosed")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert str(config_file) in str(exc_info.value)


# === AC4: ConfigError When File Missing ===


class TestMissingConfigFile:
    """Tests for AC4: ConfigError when file missing."""

    def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
        """Missing config file raises ConfigError."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=nonexistent)

        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg

    def test_error_includes_file_path(self, tmp_path: Path) -> None:
        """Error message includes the missing file path."""
        nonexistent = tmp_path / "missing_config.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=nonexistent)

        assert "missing_config.yaml" in str(exc_info.value)

    def test_error_suggests_init_command(self, tmp_path: Path) -> None:
        """Error message suggests running 'bmad-assist init'."""
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=nonexistent)

        assert "init" in str(exc_info.value).lower()


# === AC5: Path Expansion in Loaded Config ===


class TestPathExpansionFromFile:
    """Tests for AC5: Path expansion in loaded config."""

    def test_state_path_tilde_expanded_from_file(self, tmp_path: Path) -> None:
        """State path with ~ from file is expanded."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
state_path: ~/.bmad-assist/state.yaml
"""
        )
        config = load_global_config(path=config_file)
        assert "~" not in config.state_path
        assert config.state_path.startswith("/")

    def test_state_path_without_tilde_preserved(self, tmp_path: Path) -> None:
        """State path without ~ is preserved."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
state_path: /absolute/path/state.yaml
"""
        )
        config = load_global_config(path=config_file)
        assert config.state_path == "/absolute/path/state.yaml"


# === AC6: Integration with Existing Singleton ===


class TestSingletonIntegrationFromFile:
    """Tests for AC6: Integration with existing singleton."""

    def test_get_config_after_load_global(self, tmp_path: Path) -> None:
        """get_config returns config after load_global_config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: gemini
    model: gemini_2_5_pro
"""
        )
        loaded = load_global_config(path=config_file)
        retrieved = get_config()
        assert loaded is retrieved

    def test_singleton_is_same_instance(self, tmp_path: Path) -> None:
        """Multiple get_config() calls return same instance after load_global_config."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        load_global_config(path=config_file)
        first = get_config()
        second = get_config()
        assert first is second
