"""Tests for project configuration override.

Story 1.4 tests (AC1-AC6):
- AC1: Project config overrides global values
- AC2: Deep merge for nested structures
- AC3: Project config only (no global)
- AC4: Global config only (no project)
- AC5: Neither config exists
- AC6: Project config path resolution

Note: Tests for _deep_merge helper are in test_config_deep_merge.py.
Note: Tests for AC7-AC12 (merge behavior) are in test_config_project_merge.py.
Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

from pathlib import Path

import pytest

from bmad_assist.core.config import (
    PROJECT_CONFIG_NAME,
    load_config_with_project,
)
from bmad_assist.core.exceptions import ConfigError


class TestProjectConfigConstant:
    """Tests for Story 1.4: Project config constant."""

    def test_project_config_name_is_bmad_assist_yaml(self) -> None:
        """PROJECT_CONFIG_NAME is bmad-assist.yaml."""
        assert PROJECT_CONFIG_NAME == "bmad-assist.yaml"


# === Tests for AC1: Project config overrides global values ===


class TestProjectConfigOverridesGlobal:
    """Tests for AC1: Project config overrides global values."""

    def test_project_overrides_scalar_value(self, tmp_path: Path) -> None:
        """Project config scalar values override global."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
state_path: /global/state.yaml
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
state_path: /project/state.yaml
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.state_path == "/project/state.yaml"
        assert config.providers.master.provider == "claude"

    def test_non_overridden_global_values_preserved(self, tmp_path: Path) -> None:
        """Non-overridden global values are preserved."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: python-cli
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
state_path: /project/state.yaml
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.power_prompts.set_name == "python-cli"


# === Tests for AC2: Deep merge for nested structures ===


class TestDeepMergeNestedStructures:
    """Tests for AC2: Deep merge for nested structures."""

    def test_providers_master_partial_override(self, tmp_path: Path) -> None:
        """Override just model, keep provider from global."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
    settings: /global/settings.json
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
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.providers.master.provider == "claude"
        assert config.providers.master.model == "sonnet_4"
        assert config.providers.master.settings == "/global/settings.json"

    def test_providers_multi_preserved_when_not_overridden(self, tmp_path: Path) -> None:
        """providers.multi list is preserved from global when not overridden."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
  multi:
    - provider: gemini
      model: gemini_2_5_pro
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
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert len(config.providers.multi) == 1
        assert config.providers.multi[0].provider == "gemini"


# === Tests for AC3: Project config only (no global) ===


class TestProjectConfigOnly:
    """Tests for AC3: Project config only (no global)."""

    def test_project_only_loads_successfully(self, tmp_path: Path) -> None:
        """Project config alone is sufficient when global doesn't exist."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
providers:
  master:
    provider: codex
    model: o3
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=nonexistent_global,
        )
        assert config.providers.master.provider == "codex"
        assert config.providers.master.model == "o3"

    def test_project_only_no_error_about_missing_global(self, tmp_path: Path) -> None:
        """No error is raised about missing global config when project exists."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
providers:
  master:
    provider: gemini
    model: gemini_2_5_pro
"""
        )

        # Should not raise any exception
        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=nonexistent_global,
        )
        assert config is not None


# === Tests for AC4: Global config only (no project) ===


class TestGlobalConfigOnlyProject:
    """Tests for AC4: Global config only (no project)."""

    def test_global_only_loads_successfully(self, tmp_path: Path) -> None:
        """Global config alone is sufficient when project doesn't exist."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: gemini
    model: gemini_2_5_pro
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # No bmad-assist.yaml in project

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.providers.master.provider == "gemini"

    def test_global_only_no_error_about_missing_project(self, tmp_path: Path) -> None:
        """No error is raised about missing project config when global exists."""
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

        # Should not raise any exception
        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config is not None


# === Tests for AC5: Neither config exists ===


class TestNeitherConfigExists:
    """Tests for AC5: Neither config exists."""

    def test_neither_raises_config_error(self, tmp_path: Path) -> None:
        """Error when neither global nor project config exists."""
        nonexistent_global = tmp_path / "nonexistent" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        # No bmad-assist.yaml in project

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=nonexistent_global,
            )
        assert "init" in str(exc_info.value).lower()

    def test_error_suggests_bmad_assist_init(self, tmp_path: Path) -> None:
        """Error message suggests running 'bmad-assist init'."""
        nonexistent_global = tmp_path / "no_global" / "config.yaml"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=nonexistent_global,
            )
        error_msg = str(exc_info.value)
        assert "bmad-assist init" in error_msg.lower() or "init" in error_msg.lower()


# === Tests for AC6: Project config path resolution ===


class TestProjectConfigPathResolution:
    """Tests for AC6: Project config path resolution."""

    def test_project_config_path_resolved_from_project_path(self, tmp_path: Path) -> None:
        """Project config is loaded from {project_path}/bmad-assist.yaml."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
state_path: /project/custom/state.yaml
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
        assert config.state_path == "/project/custom/state.yaml"

    def test_project_path_defaults_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """project_path defaults to current working directory."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
"""
        )
        project_dir = tmp_path / "cwd_project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
state_path: /cwd/state.yaml
"""
        )

        monkeypatch.chdir(project_dir)

        config = load_config_with_project(
            project_path=None,  # Defaults to cwd
            global_config_path=global_config,
        )
        assert config.state_path == "/cwd/state.yaml"
