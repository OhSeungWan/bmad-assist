"""Tests for CLI experiment commands - Story 18.11.

Comprehensive tests covering:
- Experiment subcommand group (AC1)
- run command (AC2, AC9, AC11)
- batch command (AC3, AC9, AC11)
- list command (AC4, AC9)
- show command (AC5, AC9)
- compare command (AC6, AC9)
- templates command (AC7, AC9)
- Shared helpers (AC8)
- Error handling (AC9)
"""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from bmad_assist.cli import app
from bmad_assist.cli_utils import (
    EXIT_CONFIG_ERROR,
    EXIT_ERROR,
    EXIT_SUCCESS,
    format_duration_cli,
)
from bmad_assist.commands.experiment import (
    _get_experiments_dir,
    _validate_run_exists,
)

runner = CliRunner()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_experiments_dir(tmp_path: Path) -> Path:
    """Create mock experiments directory structure."""
    experiments = tmp_path / "experiments"

    # Create directories
    (experiments / "configs").mkdir(parents=True)
    (experiments / "loops").mkdir(parents=True)
    (experiments / "patch-sets").mkdir(parents=True)
    (experiments / "fixtures").mkdir(parents=True)
    (experiments / "runs").mkdir(parents=True)

    # Create minimal config template
    (experiments / "configs" / "opus-solo.yaml").write_text("""
name: opus-solo
description: "Test config"
providers:
  master:
    provider: claude
    model: opus
  multi: []
""")

    # Create minimal loop template
    (experiments / "loops" / "standard.yaml").write_text("""
name: standard
description: "Test loop"
sequence:
  - workflow: create-story
    required: true
""")

    # Create minimal patch-set
    (experiments / "patch-sets" / "baseline.yaml").write_text("""
name: baseline
description: "Test patch-set"
patches: {}
""")

    # Create fixture registry
    (experiments / "fixtures" / "registry.yaml").write_text("""
fixtures:
  - id: minimal
    name: "Minimal"
    description: "Test fixture"
    path: ./minimal
    tags: [test]
    difficulty: easy
    estimated_cost: "$0.01"
""")

    # Create minimal fixture directory
    (experiments / "fixtures" / "minimal" / "docs").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def mock_run_dir(mock_experiments_dir: Path) -> Path:
    """Create a mock run directory with manifest."""
    runs_dir = mock_experiments_dir / "experiments" / "runs"
    run_dir = runs_dir / "run-2026-01-09-001"
    run_dir.mkdir(parents=True)

    # Create manifest
    manifest = {
        "run_id": "run-2026-01-09-001",
        "started": "2026-01-09T10:00:00+00:00",
        "completed": "2026-01-09T10:15:00+00:00",
        "status": "completed",
        "schema_version": "1.0",
        "input": {
            "fixture": "minimal",
            "config": "opus-solo",
            "patch_set": "baseline",
            "loop": "standard",
        },
        "resolved": {
            "fixture": {
                "name": "minimal",
                "source": "/path/to/minimal",
                "snapshot": "./fixture-snapshot",
            },
            "config": {
                "name": "opus-solo",
                "source": "/path/to/opus-solo.yaml",
                "providers": {
                    "master": {"provider": "claude", "model": "opus"},
                    "multi": [],
                },
            },
            "patch_set": {
                "name": "baseline",
                "source": "/path/to/baseline.yaml",
                "workflow_overrides": {},
                "patches": {},
            },
            "loop": {
                "name": "standard",
                "source": "/path/to/standard.yaml",
                "sequence": ["create-story"],
            },
        },
        "results": {
            "stories_attempted": 1,
            "stories_completed": 1,
            "stories_failed": 0,
            "phases": [
                {
                    "phase": "create-story",
                    "story": "1.1",
                    "status": "completed",
                    "duration_seconds": 120.5,
                    "tokens": None,
                    "cost": None,
                    "error": None,
                }
            ],
        },
        "metrics": None,
    }

    (run_dir / "manifest.yaml").write_text(yaml.dump(manifest))
    return run_dir


# =============================================================================
# Test: Shared Helpers (AC8)
# =============================================================================


class TestSharedHelpers:
    """Tests for shared helper functions (AC8)."""

    def test_format_duration_seconds_only(self) -> None:
        """AC8: Format duration for seconds only."""
        assert format_duration_cli(45) == "45s"
        assert format_duration_cli(0) == "0s"

    def test_format_duration_minutes_and_seconds(self) -> None:
        """AC8: Format duration for minutes and seconds."""
        assert format_duration_cli(90) == "1m 30s"
        assert format_duration_cli(600) == "10m 0s"

    def test_format_duration_hours_minutes_seconds(self) -> None:
        """AC8: Format duration for hours, minutes, seconds."""
        assert format_duration_cli(3661) == "1h 1m 1s"
        assert format_duration_cli(7200) == "2h 0m 0s"

    def test_get_experiments_dir_exists(self, mock_experiments_dir: Path) -> None:
        """AC8: Returns path when experiments/ exists."""
        result = _get_experiments_dir(mock_experiments_dir)
        assert result == mock_experiments_dir / "experiments"

    def test_get_experiments_dir_not_exists(self, tmp_path: Path) -> None:
        """AC8: Raises typer.Exit when experiments/ doesn't exist."""
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            _get_experiments_dir(tmp_path)
        assert exc_info.value.exit_code == EXIT_ERROR

    def test_validate_run_exists_valid(self, mock_run_dir: Path) -> None:
        """AC8: Returns path when run exists."""
        runs_dir = mock_run_dir.parent
        result = _validate_run_exists(runs_dir, "run-2026-01-09-001")
        assert result == mock_run_dir

    def test_validate_run_exists_invalid(self, mock_experiments_dir: Path) -> None:
        """AC8: Raises typer.Exit when run doesn't exist."""
        import typer

        runs_dir = mock_experiments_dir / "experiments" / "runs"
        with pytest.raises(typer.Exit) as exc_info:
            _validate_run_exists(runs_dir, "nonexistent-run")
        assert exc_info.value.exit_code == EXIT_ERROR


# =============================================================================
# Test: experiment run command (AC2, AC9, AC11)
# =============================================================================


class TestExperimentRun:
    """Tests for experiment run command (AC2, AC9, AC11)."""

    def test_run_dry_run_valid(self, mock_experiments_dir: Path) -> None:
        """AC2, AC11: Dry-run with valid configuration succeeds."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "run",
                "-f",
                "minimal",
                "-c",
                "opus-solo",
                "-P",
                "baseline",
                "-l",
                "standard",
                "-p",
                str(mock_experiments_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Dry run" in result.output
        assert "Configuration valid" in result.output

    def test_run_missing_config_template(self, mock_experiments_dir: Path) -> None:
        """AC2, AC9: Run with missing config template exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "run",
                "-f",
                "minimal",
                "-c",
                "nonexistent",
                "-P",
                "baseline",
                "-l",
                "standard",
                "-p",
                str(mock_experiments_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "not found" in result.output

    def test_run_missing_fixture(self, mock_experiments_dir: Path) -> None:
        """AC2, AC9: Run with missing fixture exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "run",
                "-f",
                "nonexistent",
                "-c",
                "opus-solo",
                "-P",
                "baseline",
                "-l",
                "standard",
                "-p",
                str(mock_experiments_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "not found" in result.output

    def test_run_missing_experiments_dir(self, tmp_path: Path) -> None:
        """AC9: Run fails when experiments/ doesn't exist."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "run",
                "-f",
                "minimal",
                "-c",
                "opus-solo",
                "-P",
                "baseline",
                "-l",
                "standard",
                "-p",
                str(tmp_path),
            ],
        )
        assert result.exit_code == EXIT_ERROR
        assert "experiments/ directory not found" in result.output


# =============================================================================
# Test: experiment batch command (AC3, AC9, AC11)
# =============================================================================


class TestExperimentBatch:
    """Tests for experiment batch command (AC3, AC9, AC11)."""

    def test_batch_dry_run_shows_combinations(self, mock_experiments_dir: Path) -> None:
        """AC3, AC11: Batch dry-run shows all combinations."""
        # Create additional config template
        (mock_experiments_dir / "experiments" / "configs" / "haiku.yaml").write_text(
            """
name: haiku
description: "Haiku config"
providers:
  master:
    provider: claude
    model: haiku
  multi: []
"""
        )

        result = runner.invoke(
            app,
            [
                "experiment",
                "batch",
                "--fixtures",
                "minimal",
                "--configs",
                "opus-solo,haiku",
                "--patch-set",
                "baseline",
                "--loop",
                "standard",
                "-p",
                str(mock_experiments_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Dry run" in result.output
        assert "minimal + opus-solo" in result.output
        assert "minimal + haiku" in result.output

    def test_batch_missing_fixture(self, mock_experiments_dir: Path) -> None:
        """AC3, AC9: Batch with missing fixture exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "batch",
                "--fixtures",
                "minimal,nonexistent",
                "--configs",
                "opus-solo",
                "--patch-set",
                "baseline",
                "--loop",
                "standard",
                "-p",
                str(mock_experiments_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "not found" in result.output

    def test_batch_empty_fixtures(self, mock_experiments_dir: Path) -> None:
        """AC3, AC9: Batch with empty fixtures exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "batch",
                "--fixtures",
                "",
                "--configs",
                "opus-solo",
                "--patch-set",
                "baseline",
                "--loop",
                "standard",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "No fixtures" in result.output


# =============================================================================
# Test: experiment list command (AC4, AC9)
# =============================================================================


class TestExperimentList:
    """Tests for experiment list command (AC4, AC9)."""

    def test_list_empty_runs_dir(self, mock_experiments_dir: Path) -> None:
        """AC4: List with empty runs directory shows message."""
        result = runner.invoke(
            app,
            ["experiment", "list", "-p", str(mock_experiments_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "No runs found" in result.output

    def test_list_with_runs(self, mock_run_dir: Path) -> None:
        """AC4: List with runs shows table."""
        project_dir = mock_run_dir.parent.parent.parent
        result = runner.invoke(
            app,
            ["experiment", "list", "-p", str(project_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "run-2026-01-09-001" in result.output
        assert "completed" in result.output.lower()

    def test_list_filter_by_status(self, mock_run_dir: Path) -> None:
        """AC4: List with status filter works."""
        project_dir = mock_run_dir.parent.parent.parent
        result = runner.invoke(
            app,
            ["experiment", "list", "--status", "completed", "-p", str(project_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "run-2026-01-09-001" in result.output

    def test_list_filter_excludes_non_matching(self, mock_run_dir: Path) -> None:
        """AC4: List with non-matching filter shows no results."""
        project_dir = mock_run_dir.parent.parent.parent
        result = runner.invoke(
            app,
            ["experiment", "list", "--status", "failed", "-p", str(project_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "No runs found" in result.output


# =============================================================================
# Test: experiment show command (AC5, AC9)
# =============================================================================


class TestExperimentShow:
    """Tests for experiment show command (AC5, AC9)."""

    def test_show_valid_run(self, mock_run_dir: Path) -> None:
        """AC5: Show valid run displays details."""
        project_dir = mock_run_dir.parent.parent.parent
        result = runner.invoke(
            app,
            ["experiment", "show", "run-2026-01-09-001", "-p", str(project_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "run-2026-01-09-001" in result.output
        assert "Status" in result.output
        assert "Configuration" in result.output
        assert "Results" in result.output

    def test_show_missing_run(self, mock_experiments_dir: Path) -> None:
        """AC5, AC9: Show missing run exits with error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "show",
                "nonexistent-run",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_ERROR
        assert "not found" in result.output.lower()


# =============================================================================
# Test: experiment compare command (AC6, AC9)
# =============================================================================


class TestExperimentCompare:
    """Tests for experiment compare command (AC6, AC9)."""

    def test_compare_too_few_runs(self, mock_experiments_dir: Path) -> None:
        """AC6, AC9: Compare with fewer than 2 runs exits with config error."""
        result = runner.invoke(
            app,
            ["experiment", "compare", "run-001", "-p", str(mock_experiments_dir)],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "At least 2 runs" in result.output

    def test_compare_too_many_runs(self, mock_experiments_dir: Path) -> None:
        """AC6, AC9: Compare with more than 10 runs exits with config error."""
        run_ids = [f"run-{i:03d}" for i in range(11)]
        result = runner.invoke(
            app,
            ["experiment", "compare", *run_ids, "-p", str(mock_experiments_dir)],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "Maximum" in result.output

    def test_compare_missing_run(self, mock_experiments_dir: Path) -> None:
        """AC6, AC9: Compare with missing run exits with error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "compare",
                "run-001",
                "run-002",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_ERROR
        assert "not found" in result.output.lower()

    def test_compare_two_runs(self, mock_run_dir: Path) -> None:
        """AC6: Compare with 2 valid runs generates report."""
        project_dir = mock_run_dir.parent.parent.parent

        # Create second run
        runs_dir = mock_run_dir.parent
        run2_dir = runs_dir / "run-2026-01-09-002"
        run2_dir.mkdir(parents=True)

        manifest2 = {
            "run_id": "run-2026-01-09-002",
            "started": "2026-01-09T11:00:00+00:00",
            "completed": "2026-01-09T11:20:00+00:00",
            "status": "completed",
            "schema_version": "1.0",
            "input": {
                "fixture": "minimal",
                "config": "opus-solo",
                "patch_set": "baseline",
                "loop": "standard",
            },
            "resolved": {
                "fixture": {
                    "name": "minimal",
                    "source": "/path/to/minimal",
                    "snapshot": "./fixture-snapshot",
                },
                "config": {
                    "name": "opus-solo",
                    "source": "/path/to/opus-solo.yaml",
                    "providers": {
                        "master": {"provider": "claude", "model": "opus"},
                        "multi": [],
                    },
                },
                "patch_set": {
                    "name": "baseline",
                    "source": "/path/to/baseline.yaml",
                    "workflow_overrides": {},
                    "patches": {},
                },
                "loop": {
                    "name": "standard",
                    "source": "/path/to/standard.yaml",
                    "sequence": ["create-story"],
                },
            },
            "results": {
                "stories_attempted": 1,
                "stories_completed": 1,
                "stories_failed": 0,
                "phases": [],
            },
            "metrics": None,
        }
        (run2_dir / "manifest.yaml").write_text(yaml.dump(manifest2))

        result = runner.invoke(
            app,
            [
                "experiment",
                "compare",
                "run-2026-01-09-001",
                "run-2026-01-09-002",
                "-p",
                str(project_dir),
            ],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Comparison Report" in result.output

    def test_compare_invalid_format(self, mock_experiments_dir: Path) -> None:
        """AC6, AC9: Compare with invalid format exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "compare",
                "run-001",
                "run-002",
                "--format",
                "invalid",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "Invalid --format" in result.output


# =============================================================================
# Test: experiment templates command (AC7, AC9)
# =============================================================================


class TestExperimentTemplates:
    """Tests for experiment templates command (AC7, AC9)."""

    def test_templates_all(self, mock_experiments_dir: Path) -> None:
        """AC7: Templates without filter shows all axes."""
        result = runner.invoke(
            app,
            ["experiment", "templates", "-p", str(mock_experiments_dir)],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Config Templates" in result.output
        assert "Loop Templates" in result.output
        assert "Patch-Set" in result.output
        assert "Fixtures" in result.output

    def test_templates_filter_config(self, mock_experiments_dir: Path) -> None:
        """AC7: Templates with --type config shows only configs."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "templates",
                "--type",
                "config",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_SUCCESS
        assert "Config Templates" in result.output
        assert "opus-solo" in result.output
        # Should NOT show other types
        assert "Loop Templates" not in result.output

    def test_templates_invalid_type(self, mock_experiments_dir: Path) -> None:
        """AC7, AC9: Templates with invalid type exits with config error."""
        result = runner.invoke(
            app,
            [
                "experiment",
                "templates",
                "--type",
                "invalid",
                "-p",
                str(mock_experiments_dir),
            ],
        )
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "Invalid --type" in result.output


# =============================================================================
# Test: Experiment subcommand help
# =============================================================================


class TestExperimentHelp:
    """Tests for experiment subcommand group help."""

    def test_experiment_help(self) -> None:
        """AC1: experiment command shows help."""
        result = runner.invoke(app, ["experiment", "--help"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Experiment framework commands" in result.output

    def test_experiment_no_args_shows_help(self) -> None:
        """AC1: experiment with no args shows help (no_args_is_help=True)."""
        result = runner.invoke(app, ["experiment"])
        # Typer's no_args_is_help returns exit code 2 when showing help with no args
        assert result.exit_code == EXIT_CONFIG_ERROR
        assert "experiment" in result.output.lower()
        # Should show commands or usage
        assert "run" in result.output.lower() or "Commands" in result.output
