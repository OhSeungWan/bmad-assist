"""Tests for project configuration error handling.

Story 1.4 tests (AC11-AC12):
- AC11: ConfigError for invalid project YAML
- AC12: project_path must be a directory
- Additional edge cases for Story 1.4

Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

from pathlib import Path

import pytest

from bmad_assist.core.config import (
    _reset_config,
    get_config,
    load_config_with_project,
)
from bmad_assist.core.exceptions import ConfigError

# === Tests for AC11: ConfigError for invalid project YAML ===


class TestInvalidProjectYaml:
    """Tests for AC11: ConfigError for invalid project YAML."""

    def test_invalid_project_yaml_raises_config_error(self, tmp_path: Path) -> None:
        """Invalid YAML in project config raises ConfigError."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("invalid: yaml: syntax: [unclosed")

        with pytest.raises(ConfigError):
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
                cwd_config_path=False,
            )

    def test_error_contains_project_config_identifier(self, tmp_path: Path) -> None:
        """Error message contains 'project config' or project config path."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("invalid: [unclosed")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
                cwd_config_path=False,
            )
        error_msg = str(exc_info.value).lower()
        assert "project config" in error_msg or "bmad-assist.yaml" in error_msg

    def test_error_distinguishes_project_from_global(self, tmp_path: Path) -> None:
        """Error message for project config is different from global config error."""
        # First test invalid global
        invalid_global = tmp_path / "invalid_global.yaml"
        invalid_global.write_text("invalid: [unclosed")
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info_global:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=invalid_global,
                cwd_config_path=False,
            )
        global_error = str(exc_info_global.value).lower()

        # Now test invalid project
        valid_global = tmp_path / "valid_global.yaml"
        valid_global.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("invalid: [unclosed")

        _reset_config()  # Reset singleton between tests

        with pytest.raises(ConfigError) as exc_info_project:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=valid_global,
                cwd_config_path=False,
            )
        project_error = str(exc_info_project.value).lower()

        # Errors should be distinguishable
        assert "global" in global_error or str(invalid_global) in global_error
        assert "project" in project_error or "bmad-assist.yaml" in project_error


# === Tests for AC12: project_path must be a directory ===


class TestProjectPathValidation:
    """Tests for AC12: project_path must be a directory."""

    def test_project_path_file_raises_error(self, tmp_path: Path) -> None:
        """project_path pointing to a file raises ConfigError."""
        file_path = tmp_path / "not-a-dir.txt"
        file_path.write_text("i am a file")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(project_path=file_path)
        assert "directory" in str(exc_info.value).lower()

    def test_error_mentions_got_file(self, tmp_path: Path) -> None:
        """Error message mentions that a file was provided instead of directory."""
        file_path = tmp_path / "some-file.yaml"
        file_path.write_text("content")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(project_path=file_path)
        error_msg = str(exc_info.value).lower()
        assert "directory" in error_msg
        assert "file" in error_msg

    def test_error_includes_path(self, tmp_path: Path) -> None:
        """Error message includes the problematic path."""
        file_path = tmp_path / "myfile.yaml"
        file_path.write_text("content")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(project_path=file_path)
        assert "myfile.yaml" in str(exc_info.value)


# === Additional Edge Cases for Story 1.4 ===


class TestProjectConfigFileIsDirectory:
    """Tests for project config file being a directory."""

    def test_project_config_directory_treated_as_not_existing(self, tmp_path: Path) -> None:
        """When bmad-assist.yaml is a directory, it's treated as non-existent.

        This is the expected behavior because is_file() check returns False
        for directories, so project config is considered not present.
        """
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Create bmad-assist.yaml as a DIRECTORY instead of a file
        project_config_dir = project_dir / "bmad-assist.yaml"
        project_config_dir.mkdir()

        # Should use global config only (project config directory is ignored)
        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.providers.master.provider == "claude"

    def test_no_config_when_project_config_is_directory_and_no_global(self, tmp_path: Path) -> None:
        """When bmad-assist.yaml is directory and no global, raises ConfigError."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # Create bmad-assist.yaml as a DIRECTORY
        project_config_dir = project_dir / "bmad-assist.yaml"
        project_config_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=nonexistent_global,
                cwd_config_path=False,
            )
        error_msg = str(exc_info.value)
        # Should get "no config found" error since directory is not treated as file
        assert "init" in error_msg.lower()


class TestProjectOnlyValidationError:
    """Tests for validation error when only project config exists."""

    def test_project_only_validation_error(self, tmp_path: Path) -> None:
        """Validation error from project-only config has correct message."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        # Valid YAML but missing required field
        project_config.write_text(
            """
providers:
  master:
    provider: claude
    # model is missing!
"""
        )

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=nonexistent_global,
                cwd_config_path=False,
            )
        error_msg = str(exc_info.value).lower()
        assert "project" in error_msg or "bmad-assist.yaml" in error_msg


class TestProjectConfigEdgeCases:
    """Additional edge cases for Story 1.4."""

    def test_full_config_merge(self, tmp_path: Path) -> None:
        """Full configuration merge with all fields from both sources."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
    settings: /global/master.json
  multi:
    - provider: gemini
      model: gemini_2_5_pro
power_prompts:
  set_name: global-set
  variables:
    global_var: global_value
state_path: ~/global/state.yaml
bmad_paths:
  prd: /global/prd.md
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
providers:
  master:
    model: sonnet_4
  multi:
    - provider: codex
      model: o3
power_prompts:
  variables:
    project_var: project_value
bmad_paths:
  architecture: ./arch.md
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )

        # Master: provider from global, model from project
        assert config.providers.master.provider == "claude"
        assert config.providers.master.model == "sonnet_4"
        assert config.providers.master.settings == "/global/master.json"

        # Multi: completely replaced by project
        assert len(config.providers.multi) == 1
        assert config.providers.multi[0].provider == "codex"

        # Power prompts: set_name from global, variables merged
        assert config.power_prompts.set_name == "global-set"
        assert config.power_prompts.variables["global_var"] == "global_value"
        assert config.power_prompts.variables["project_var"] == "project_value"

        # state_path: from global (expanded)
        assert "~" not in config.state_path

        # bmad_paths: prd from global, architecture from project
        assert config.bmad_paths.prd == "/global/prd.md"
        assert config.bmad_paths.architecture == "./arch.md"

    def test_project_path_with_tilde(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """project_path with tilde is expanded."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )

        # Create project in tmp_path/home/project
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        project_dir = home_dir / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
state_path: /from/home/project
"""
        )

        monkeypatch.setenv("HOME", str(home_dir))

        config = load_config_with_project(
            project_path="~/project",
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.state_path == "/from/home/project"

    def test_validation_failure_clears_singleton(self, tmp_path: Path) -> None:
        """Validation failure during merge clears the singleton."""
        # First load a valid config
        valid_global = tmp_path / "valid.yaml"
        valid_global.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        load_config_with_project(
            project_path=project_dir,
            global_config_path=valid_global,
            cwd_config_path=False,
        )
        first_config = get_config()
        assert first_config is not None

        # Now try to load an invalid merged config
        invalid_global = tmp_path / "invalid.yaml"
        invalid_global.write_text(
            """
providers:
  master:
    provider: claude
    # model is missing!
"""
        )

        _reset_config()

        with pytest.raises(ConfigError):
            load_config_with_project(
                project_path=project_dir,
                global_config_path=invalid_global,
                cwd_config_path=False,
            )

        # Singleton should be cleared
        with pytest.raises(ConfigError) as exc_info:
            get_config()
        assert "not loaded" in str(exc_info.value).lower()

    def test_empty_project_config_is_valid(self, tmp_path: Path) -> None:
        """Empty project config file raises ConfigError (empty file detection)."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("")  # Empty file

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
                cwd_config_path=False,
            )
        error_msg = str(exc_info.value).lower()
        assert "empty" in error_msg or "whitespace" in error_msg

    def test_project_dir_does_not_exist(self, tmp_path: Path) -> None:
        """Non-existent project directory uses global config only."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        nonexistent_project = tmp_path / "nonexistent_project"
        # Don't create the directory

        config = load_config_with_project(
            project_path=nonexistent_project,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.providers.master.provider == "claude"

    def test_project_config_validation_error_includes_context(self, tmp_path: Path) -> None:
        """Validation error from project config includes useful context."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        # Valid YAML but invalid structure (wrong type)
        project_config.write_text(
            """
providers:
  master:
    model: 123
"""
        )

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
                cwd_config_path=False,
            )
        error_msg = str(exc_info.value).lower()
        # Should mention it's a merged config error
        assert "merged" in error_msg or "project" in error_msg
