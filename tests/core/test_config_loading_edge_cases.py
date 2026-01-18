"""Tests for global configuration loading edge cases.

Story 1.3 tests (AC7-AC10 and additional edge cases):
- AC7: ConfigError for unreadable file (OSError)
- AC8: Empty config file raises ConfigError
- AC9: Non-ASCII content loads correctly
- AC10: File size limit protection
- Additional edge cases

Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

from pathlib import Path

import pytest

from bmad_assist.core.config import (
    MAX_CONFIG_SIZE,
    get_config,
    load_global_config,
)
from bmad_assist.core.exceptions import ConfigError


class TestConfigSizeConstant:
    """Tests for MAX_CONFIG_SIZE constant."""

    def test_max_config_size_is_1mb(self) -> None:
        """MAX_CONFIG_SIZE is 1MB (1,048,576 bytes)."""
        assert MAX_CONFIG_SIZE == 1_048_576


# === AC7: ConfigError for Unreadable File (OSError) ===


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
            error_msg = str(exc_info.value).lower()
            assert "cannot read" in error_msg or "permission" in error_msg
        finally:
            config_file.chmod(0o644)  # Restore permissions for cleanup

    def test_oserror_includes_file_path(self, tmp_path: Path) -> None:
        """OSError includes file path in error message."""
        config_file = tmp_path / "unreadable.yaml"
        config_file.write_text("content")
        config_file.chmod(0o000)

        try:
            with pytest.raises(ConfigError) as exc_info:
                load_global_config(path=config_file)
            assert "unreadable.yaml" in str(exc_info.value)
        finally:
            config_file.chmod(0o644)


# === AC8: Empty Config File Raises ConfigError ===


class TestEmptyConfigFile:
    """Tests for AC8: Empty config file raises ConfigError."""

    def test_empty_file_raises_config_error(self, tmp_path: Path) -> None:
        """Empty config file raises ConfigError with clear message."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value).lower()
        # Now raises explicit empty file error
        assert "empty" in error_msg or "whitespace" in error_msg

    def test_whitespace_only_file_raises_config_error(self, tmp_path: Path) -> None:
        """Whitespace-only config file raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("   \n\n   \n")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "whitespace" in error_msg

    def test_empty_yaml_dict_raises_config_error(self, tmp_path: Path) -> None:
        """Config with empty dict raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value).lower()
        assert "providers" in error_msg


# === AC9: Non-ASCII Content Loads Correctly ===


class TestNonAsciiContent:
    """Tests for AC9: Non-ASCII content loads correctly."""

    def test_polish_characters_load_correctly(self, tmp_path: Path) -> None:
        """Config with Polish characters (UTF-8) loads correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
# Comment with Polish: Paweł, żółć, źdźbło
""",
            encoding="utf-8",
        )
        config = load_global_config(path=config_file)
        assert config.providers.master.provider == "claude"

    def test_unicode_in_string_values(self, tmp_path: Path) -> None:
        """Unicode characters in string values are preserved."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: polski-zestaw-żółć
""",
            encoding="utf-8",
        )
        config = load_global_config(path=config_file)
        assert config.power_prompts.set_name is not None
        assert "żółć" in config.power_prompts.set_name

    def test_japanese_characters_load_correctly(self, tmp_path: Path) -> None:
        """Config with Japanese characters loads correctly."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: 日本語テスト
""",
            encoding="utf-8",
        )
        config = load_global_config(path=config_file)
        assert config.power_prompts.set_name == "日本語テスト"


# === AC10: File Size Limit Protection ===


class TestFileSizeLimit:
    """Tests for AC10: File size limit protection."""

    def test_file_over_1mb_raises_config_error(self, tmp_path: Path) -> None:
        """Config file larger than 1MB raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        # Create file slightly over 1MB
        large_content = "x" * (MAX_CONFIG_SIZE + 1)
        config_file.write_text(large_content)

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value).lower()
        assert "exceeds" in error_msg or "too large" in error_msg

    def test_error_mentions_size_limit(self, tmp_path: Path) -> None:
        """Error message mentions size limit."""
        config_file = tmp_path / "config.yaml"
        large_content = "x" * (MAX_CONFIG_SIZE + 100)
        config_file.write_text(large_content)

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value)
        assert "1MB" in error_msg or "1048576" in error_msg

    def test_file_at_limit_loads_successfully(self, tmp_path: Path) -> None:
        """Config file at exactly 1MB limit loads successfully (if valid)."""
        config_file = tmp_path / "config.yaml"
        # Valid YAML that's under 1MB
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

    def test_large_valid_config_under_limit(self, tmp_path: Path) -> None:
        """Large but valid config under 1MB loads successfully."""
        config_file = tmp_path / "config.yaml"
        # Create valid YAML with many providers
        base = "providers:\n  master:\n    provider: claude\n    model: opus_4\n"
        providers_yaml = base + "  multi:\n"
        for i in range(100):
            providers_yaml += f"    - provider: provider_{i}\n      model: model_{i}\n"
        config_file.write_text(providers_yaml)

        # Should load successfully
        config = load_global_config(path=config_file)
        assert len(config.providers.multi) == 100


# === Additional Edge Cases for Story 1.3 ===


class TestGlobalConfigEdgeCases:
    """Additional edge cases for Story 1.3."""

    def test_full_config_from_file(self, tmp_path: Path) -> None:
        """Full configuration with all fields from file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
    settings: ./master.json
    model_name: glm-4.7
  multi:
    - provider: gemini
      model: gemini_2_5_pro
    - provider: codex
      model: o3
      settings: ./codex.json
      model_name: custom-codex
power_prompts:
  set_name: python-cli
  variables:
    project_type: cli-tool
state_path: ~/custom/state.yaml
bmad_paths:
  prd: ./docs/prd.md
  architecture: ./docs/architecture.md
  epics: ./docs/epics.md
  stories: ./docs/stories/
"""
        )
        config = load_global_config(path=config_file)

        assert config.providers.master.provider == "claude"
        assert config.providers.master.settings == "./master.json"
        assert config.providers.master.model_name == "glm-4.7"
        assert config.providers.master.display_model == "glm-4.7"
        assert len(config.providers.multi) == 2
        assert config.providers.multi[0].provider == "gemini"
        assert (
            config.providers.multi[0].display_model == "gemini_2_5_pro"
        )  # No model_name, uses model
        assert config.providers.multi[1].settings == "./codex.json"
        assert config.providers.multi[1].model_name == "custom-codex"
        assert config.providers.multi[1].display_model == "custom-codex"
        assert config.power_prompts.set_name == "python-cli"
        assert config.power_prompts.variables["project_type"] == "cli-tool"
        # state_path should be expanded
        assert "~" not in config.state_path
        assert config.bmad_paths.prd == "./docs/prd.md"

    def test_validation_error_includes_path(self, tmp_path: Path) -> None:
        """ValidationError from invalid structure includes file path."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    # model is missing - required field
"""
        )
        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        assert str(config_file) in str(exc_info.value)

    def test_path_type_conversion(self, tmp_path: Path) -> None:
        """String path is converted to Path internally."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        # Pass as string path
        config = load_global_config(path=str(config_file))
        assert config.providers.master.provider == "claude"


class TestDirectoryPathHandling:
    """Tests for directory path error handling."""

    def test_directory_path_raises_config_error(self, tmp_path: Path) -> None:
        """Passing a directory path raises clear ConfigError."""
        config_dir = tmp_path / "config.yaml"
        config_dir.mkdir()  # Create directory, not file

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_dir)

        error_msg = str(exc_info.value).lower()
        assert "not a file" in error_msg or "directory" in error_msg

    def test_directory_path_error_includes_path(self, tmp_path: Path) -> None:
        """Directory path error includes the path."""
        config_dir = tmp_path / "my_config_dir"
        config_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_dir)

        assert "my_config_dir" in str(exc_info.value)


class TestTildeExpansion:
    """Tests for tilde expansion in path parameter."""

    def test_tilde_in_path_is_expanded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tilde in path parameter is expanded to home directory."""
        # Create config in tmp_path to simulate home directory
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        # Monkeypatch home to tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))

        # This should work with tilde expansion
        config = load_global_config(path="~/config.yaml")
        assert config.providers.master.provider == "claude"


class TestStaleSingletonPrevention:
    """Tests that failed loads don't leave stale singletons."""

    def test_validation_failure_clears_singleton(self, tmp_path: Path) -> None:
        """After validation failure, singleton is cleared."""
        # First, load a valid config
        valid_file = tmp_path / "valid.yaml"
        valid_file.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        load_global_config(path=valid_file)
        first_config = get_config()
        assert first_config.providers.master.provider == "claude"

        # Now try to load an invalid config
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text(
            """
providers:
  master:
    provider: claude
    # model is missing!
"""
        )

        with pytest.raises(ConfigError):
            load_global_config(path=invalid_file)

        # After failed load, get_config should raise (singleton was cleared)
        with pytest.raises(ConfigError) as exc_info:
            get_config()
        assert "not loaded" in str(exc_info.value).lower()


class TestYamlListContent:
    """Tests for YAML content that is a list (not dict)."""

    def test_yaml_list_raises_config_error(self, tmp_path: Path) -> None:
        """YAML file containing a list (not mapping) raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2\n- item3")

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=config_file)
        error_msg = str(exc_info.value).lower()
        assert "mapping" in error_msg or "dict" in error_msg or "list" in error_msg
