"""Tests for effective config snapshot functionality.

Tech-spec: tech-spec-effective-config-snapshot.md
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from bmad_assist import __version__
from bmad_assist.core.config import Config, load_config
from bmad_assist.core.loop.runner import (
    _get_dangerous_field_paths,
    _redact_secrets,
    _save_effective_config,
)


class TestGetDangerousFieldPaths:
    """Tests for _get_dangerous_field_paths() helper."""

    def test_finds_top_level_dangerous_field(self) -> None:
        """Detects state_path marked as dangerous on Config."""
        paths = _get_dangerous_field_paths(Config)
        assert "state_path" in paths

    def test_finds_nested_dangerous_fields(self) -> None:
        """Detects nested dangerous fields like providers.master.settings."""
        paths = _get_dangerous_field_paths(Config)
        # providers.master.settings is marked dangerous
        assert "providers.master.settings" in paths

    def test_returns_set(self) -> None:
        """Returns a set of paths, not a list."""
        paths = _get_dangerous_field_paths(Config)
        assert isinstance(paths, set)
        assert len(paths) > 0

    def test_finds_dangerous_fields_in_list_items(self) -> None:
        """Detects dangerous fields in list[BaseModel] types like providers.multi."""
        paths = _get_dangerous_field_paths(Config)
        # providers.multi is list[MultiProviderConfig], which has settings marked dangerous
        assert "providers.multi.settings" in paths


class TestRedactSecrets:
    """Tests for _redact_secrets() helper."""

    def test_redacts_top_level_field(self) -> None:
        """Redacts top-level dangerous field."""
        config_dict: dict[str, Any] = {
            "state_path": "/secret/path/state.yaml",
            "timeout": 300,
        }
        dangerous = {"state_path"}
        result = _redact_secrets(config_dict, dangerous)
        assert result["state_path"] == "***REDACTED***"
        assert result["timeout"] == 300

    def test_redacts_nested_field(self) -> None:
        """Redacts nested dangerous field."""
        config_dict: dict[str, Any] = {
            "providers": {
                "master": {
                    "provider": "claude",
                    "settings": "/secret/settings.json",
                }
            }
        }
        dangerous = {"providers.master.settings"}
        result = _redact_secrets(config_dict, dangerous)
        assert result["providers"]["master"]["settings"] == "***REDACTED***"
        assert result["providers"]["master"]["provider"] == "claude"

    def test_redacts_in_list_items(self) -> None:
        """Redacts fields in list items (e.g., providers.multi)."""
        config_dict: dict[str, Any] = {
            "providers": {
                "multi": [
                    {"provider": "gemini", "settings": "/path/one.json"},
                    {"provider": "codex", "settings": "/path/two.json"},
                ]
            }
        }
        dangerous = {"providers.multi.settings"}
        result = _redact_secrets(config_dict, dangerous)
        assert result["providers"]["multi"][0]["settings"] == "***REDACTED***"
        assert result["providers"]["multi"][1]["settings"] == "***REDACTED***"
        assert result["providers"]["multi"][0]["provider"] == "gemini"

    def test_preserves_non_dangerous_fields(self) -> None:
        """Does not modify fields not in dangerous set."""
        config_dict: dict[str, Any] = {
            "timeout": 300,
            "workflow_variant": "default",
        }
        result = _redact_secrets(config_dict, set())
        assert result == config_dict

    def test_returns_new_dict(self) -> None:
        """Returns a new dict, doesn't modify original."""
        config_dict: dict[str, Any] = {"state_path": "/secret/path"}
        dangerous = {"state_path"}
        result = _redact_secrets(config_dict, dangerous)
        assert config_dict["state_path"] == "/secret/path"  # Original unchanged
        assert result["state_path"] == "***REDACTED***"


class TestSaveEffectiveConfig:
    """Tests for _save_effective_config() function."""

    @pytest.fixture
    def valid_config(self) -> Config:
        """Create a valid Config object for testing."""
        config_data = {
            "providers": {
                "master": {
                    "provider": "claude",
                    "model": "opus_4",
                }
            },
            "state_path": "/secret/state.yaml",
        }
        return load_config(config_data)

    def test_effective_config_saved_on_fresh_start(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC1: Fresh run creates _bmad-output/effective-config-{timestamp}.yaml."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)
        _save_effective_config(valid_config, tmp_path, started_at)

        output_dir = tmp_path / "_bmad-output"
        expected_file = output_dir / "effective-config-2026-01-26T12-34-56-123456.yaml"
        assert expected_file.exists()

    def test_effective_config_timestamp_matches_state(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC2: Timestamp in filename derived from State.started_at with microseconds."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 789012)
        _save_effective_config(valid_config, tmp_path, started_at)

        # Filename should include microseconds for uniqueness
        output_dir = tmp_path / "_bmad-output"
        expected_file = output_dir / "effective-config-2026-01-26T12-34-56-789012.yaml"
        assert expected_file.exists()

    def test_effective_config_contains_header(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC3: File contains header with bmad-assist version, timestamp, project_name."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)
        _save_effective_config(valid_config, tmp_path, started_at)

        output_file = tmp_path / "_bmad-output" / "effective-config-2026-01-26T12-34-56-123456.yaml"
        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert data["bmad_assist_version"] == __version__
        assert data["snapshot_timestamp"] == "2026-01-26T12:34:56.123456"
        assert data["project_name"] == tmp_path.name

    def test_effective_config_contains_all_sections(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC4: Full Config serialized (providers, paths, timeouts, etc.)."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)
        _save_effective_config(valid_config, tmp_path, started_at)

        output_file = tmp_path / "_bmad-output" / "effective-config-2026-01-26T12-34-56-123456.yaml"
        with open(output_file) as f:
            data = yaml.safe_load(f)

        config_section = data["config"]
        assert "providers" in config_section
        assert "timeout" in config_section
        assert config_section["providers"]["master"]["provider"] == "claude"

    def test_effective_config_paths_as_strings(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC5: Path objects serialized as strings (not PosixPath(...))."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)
        _save_effective_config(valid_config, tmp_path, started_at)

        output_file = tmp_path / "_bmad-output" / "effective-config-2026-01-26T12-34-56-123456.yaml"
        content = output_file.read_text()
        # Should not contain "PosixPath" or "WindowsPath"
        assert "PosixPath" not in content
        assert "WindowsPath" not in content

    def test_effective_config_failure_logs_warning(
        self, valid_config: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC6: Write failure logs warning, does NOT interrupt run."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)

        # Make tmp_path read-only to cause write failure
        with (
            patch("builtins.open", side_effect=PermissionError("No write access")),
            caplog.at_level(logging.WARNING),
        ):
            # Should not raise
            _save_effective_config(valid_config, tmp_path, started_at)

        # Check warning was logged
        assert any("Failed to save effective config" in r.message for r in caplog.records)

    def test_effective_config_redacts_secrets(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC9: Fields with security: dangerous are redacted as ***REDACTED***."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)
        _save_effective_config(valid_config, tmp_path, started_at)

        output_file = tmp_path / "_bmad-output" / "effective-config-2026-01-26T12-34-56-123456.yaml"
        with open(output_file) as f:
            data = yaml.safe_load(f)

        # state_path is marked as security: dangerous
        assert data["config"]["state_path"] == "***REDACTED***"

    def test_effective_config_temp_file_cleaned_on_failure(
        self, valid_config: Config, tmp_path: Path
    ) -> None:
        """AC8: Temp file cleaned up in finally block (no orphans on failure)."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)

        # Mock os.replace to simulate failure after temp file is written
        with patch("os.replace", side_effect=OSError("Simulated replace failure")):
            _save_effective_config(valid_config, tmp_path, started_at)

        # Temp file should be cleaned up (check both project root and _bmad-output)
        temp_files = list(tmp_path.glob("**/*.tmp"))
        assert len(temp_files) == 0

    def test_effective_config_yaml_error_logs_warning(
        self, valid_config: Config, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """F5 fix: yaml.YAMLError is caught and logged, doesn't interrupt run."""
        started_at = datetime(2026, 1, 26, 12, 34, 56, 123456)

        # Mock yaml.dump to raise YAMLError
        with (
            patch("yaml.dump", side_effect=yaml.YAMLError("Simulated YAML error")),
            caplog.at_level(logging.WARNING),
        ):
            # Should not raise
            _save_effective_config(valid_config, tmp_path, started_at)

        # Check warning was logged
        assert any("Failed to save effective config" in r.message for r in caplog.records)


class TestSaveEffectiveConfigIntegration:
    """Integration tests for _save_effective_config() without mocks."""

    def test_effective_config_integration(self, tmp_path: Path) -> None:
        """Integration test: real Config, verify full flow without mocks."""
        # Create a realistic config
        config_data = {
            "providers": {
                "master": {
                    "provider": "claude-subprocess",
                    "model": "opus",
                    "settings": "/home/user/.claude/secret-settings.json",
                },
                "multi": [
                    {"provider": "gemini", "model": "flash"},
                    {"provider": "codex", "model": "o1-mini"},
                ],
            },
            "state_path": "/secret/project/state.yaml",
            "timeout": 600,
            "workflow_variant": "experiment-v2",
        }
        config = load_config(config_data)
        started_at = datetime.now(UTC).replace(tzinfo=None)

        # Execute
        _save_effective_config(config, tmp_path, started_at)

        # Find the output file in _bmad-output/
        output_dir = tmp_path / "_bmad-output"
        output_files = list(output_dir.glob("effective-config-*.yaml"))
        assert len(output_files) == 1

        output_file = output_files[0]
        with open(output_file) as f:
            data = yaml.safe_load(f)

        # Verify structure
        assert "bmad_assist_version" in data
        assert "snapshot_timestamp" in data
        assert "project_name" in data
        assert "config" in data

        # Verify secrets are redacted
        assert data["config"]["state_path"] == "***REDACTED***"
        assert data["config"]["providers"]["master"]["settings"] == "***REDACTED***"

        # Verify non-secrets are preserved
        assert data["config"]["timeout"] == 600
        assert data["config"]["workflow_variant"] == "experiment-v2"
        assert data["config"]["providers"]["master"]["provider"] == "claude-subprocess"
