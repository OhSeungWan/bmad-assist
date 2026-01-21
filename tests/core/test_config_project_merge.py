"""Tests for project configuration merge behavior.

Story 1.4 tests (AC7-AC10):
- AC7: List override (not merge) for providers.multi
- AC8: Dictionary deep merge for power_prompts.variables
- AC9: Path fields from project config
- AC10: Singleton updated with merged config

Note: Tests for AC11-AC12 (error handling) are in test_config_project_errors.py.
Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

from pathlib import Path

from bmad_assist.core.config import (
    get_config,
    load_config_with_project,
)

# === Tests for AC7: List override (not merge) for providers.multi ===


class TestListReplacement:
    """Tests for AC7: List override (not merge) for providers.multi."""

    def test_multi_list_replaced_not_merged(self, tmp_path: Path) -> None:
        """Project multi list replaces global, not appends."""
        global_config = tmp_path / "config.yaml"
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
  multi:
    - provider: codex
      model: o3
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert len(config.providers.multi) == 1
        assert config.providers.multi[0].provider == "codex"
        assert config.providers.multi[0].model == "o3"

    def test_global_multi_not_preserved_when_project_overrides(self, tmp_path: Path) -> None:
        """Global providers.multi is NOT preserved when project overrides it."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
  multi:
    - provider: gemini
      model: gemini_2_5_pro
    - provider: claude
      model: sonnet_4
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
providers:
  multi:
    - provider: codex
      model: o3
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        # Only codex should be in multi, gemini and claude from global should NOT be there
        assert len(config.providers.multi) == 1
        providers_in_multi = [p.provider for p in config.providers.multi]
        assert "codex" in providers_in_multi
        assert "gemini" not in providers_in_multi
        assert "claude" not in providers_in_multi


# === Tests for AC8: Dictionary deep merge for power_prompts.variables ===


class TestDictDeepMerge:
    """Tests for AC8: Dictionary deep merge for power_prompts.variables."""

    def test_variables_deep_merged(self, tmp_path: Path) -> None:
        """power_prompts.variables dict is deep merged."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: python-cli
  variables:
    project_type: cli
    language: python
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
power_prompts:
  variables:
    project_type: web-app
    framework: react
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.power_prompts.set_name == "python-cli"
        assert config.power_prompts.variables["project_type"] == "web-app"
        assert config.power_prompts.variables["language"] == "python"
        assert config.power_prompts.variables["framework"] == "react"

    def test_variables_global_keys_preserved(self, tmp_path: Path) -> None:
        """Global variables keys are preserved when project adds new ones."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  variables:
    global_key: global_value
"""
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text(
            """
power_prompts:
  variables:
    project_key: project_value
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.power_prompts.variables["global_key"] == "global_value"
        assert config.power_prompts.variables["project_key"] == "project_value"


# === Tests for AC9: Path fields from project config ===


class TestPathFieldsFromProject:
    """Tests for AC9: Path fields from project config."""

    def test_paths_preserved_as_is(self, tmp_path: Path) -> None:
        """Path fields from project config are preserved as-is."""
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
        project_config.write_text(
            """
bmad_paths:
  prd: ./docs/prd.md
  architecture: ./docs/architecture.md
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.bmad_paths.prd == "./docs/prd.md"
        assert config.bmad_paths.architecture == "./docs/architecture.md"

    def test_relative_paths_remain_relative(self, tmp_path: Path) -> None:
        """Relative paths remain relative (not expanded)."""
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
        project_config.write_text(
            """
bmad_paths:
  prd: relative/path/prd.md
  stories: ../stories/
"""
        )

        config = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        assert config.bmad_paths.prd == "relative/path/prd.md"
        assert config.bmad_paths.stories == "../stories/"


# === Tests for AC10: Singleton updated with merged config ===


class TestSingletonIntegrationProject:
    """Tests for AC10: Singleton updated with merged config."""

    def test_get_config_after_project_load(self, tmp_path: Path) -> None:
        """get_config returns merged config after load_config_with_project."""
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
        project_config.write_text(
            """
state_path: /project/state.yaml
"""
        )

        loaded = load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        retrieved = get_config()
        assert loaded is retrieved
        assert retrieved.state_path == "/project/state.yaml"

    def test_singleton_reflects_merged_values(self, tmp_path: Path) -> None:
        """Singleton contains merged values from both configs."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text(
            """
providers:
  master:
    provider: claude
    model: opus_4
power_prompts:
  set_name: global-set
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

        load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
            cwd_config_path=False,
        )
        config = get_config()
        assert config.providers.master.provider == "claude"
        assert config.power_prompts.set_name == "global-set"
        assert config.state_path == "/project/state.yaml"
