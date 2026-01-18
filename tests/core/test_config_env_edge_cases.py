"""Edge case tests for .env file loading.

Story 1.5 edge cases for credentials security.

Extracted from test_config.py as part of Story 1.8 (Test Suite Refactoring).
"""

import os
from pathlib import Path

import pytest

from bmad_assist.core.config import load_env_file


class TestEnvFileEdgeCases:
    """Edge cases for .env file loading."""

    def test_env_file_is_directory_returns_false(self, tmp_path: Path) -> None:
        """When .env is a directory, returns False."""
        env_dir = tmp_path / ".env"
        env_dir.mkdir()

        result = load_env_file(project_path=tmp_path)
        assert result is False

    def test_project_path_defaults_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """project_path defaults to current working directory."""
        env_file = tmp_path / ".env"
        env_file.write_text("CWD_DEFAULT_TEST=cwd_value\n")

        # Clean up
        os.environ.pop("CWD_DEFAULT_TEST", None)

        monkeypatch.chdir(tmp_path)

        result = load_env_file()  # No project_path, should use cwd
        assert result is True
        assert os.getenv("CWD_DEFAULT_TEST") == "cwd_value"

        # Cleanup
        os.environ.pop("CWD_DEFAULT_TEST", None)

    def test_tilde_expansion_in_project_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tilde in project_path is expanded."""
        # Create fake home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        env_file = home_dir / ".env"
        env_file.write_text("TILDE_TEST=tilde_value\n")

        # Clean up
        os.environ.pop("TILDE_TEST", None)

        monkeypatch.setenv("HOME", str(home_dir))

        result = load_env_file(project_path="~")
        assert result is True
        assert os.getenv("TILDE_TEST") == "tilde_value"

        # Cleanup
        os.environ.pop("TILDE_TEST", None)

    def test_multiple_env_vars_loaded(self, tmp_path: Path) -> None:
        """Multiple environment variables are loaded from .env."""
        env_file = tmp_path / ".env"
        env_file.write_text("MULTI_VAR_A=value_a\nMULTI_VAR_B=value_b\nMULTI_VAR_C=value_c\n")

        # Clean up
        for var in ["MULTI_VAR_A", "MULTI_VAR_B", "MULTI_VAR_C"]:
            os.environ.pop(var, None)

        result = load_env_file(project_path=tmp_path)

        assert result is True
        assert os.getenv("MULTI_VAR_A") == "value_a"
        assert os.getenv("MULTI_VAR_B") == "value_b"
        assert os.getenv("MULTI_VAR_C") == "value_c"

        # Cleanup
        for var in ["MULTI_VAR_A", "MULTI_VAR_B", "MULTI_VAR_C"]:
            os.environ.pop(var, None)

    def test_env_with_comments_loaded(self, tmp_path: Path) -> None:
        """Comments in .env file are ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\nCOMMENT_TEST_VAR=actual_value\n# Another comment\n"
        )

        # Clean up
        os.environ.pop("COMMENT_TEST_VAR", None)

        result = load_env_file(project_path=tmp_path)

        assert result is True
        assert os.getenv("COMMENT_TEST_VAR") == "actual_value"

        # Cleanup
        os.environ.pop("COMMENT_TEST_VAR", None)

    def test_env_empty_file(self, tmp_path: Path) -> None:
        """Empty .env file returns True (file exists, just nothing to load)."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        result = load_env_file(project_path=tmp_path)
        assert result is True  # File exists and was processed

    def test_env_with_quoted_values(self, tmp_path: Path) -> None:
        """Quoted values in .env are handled correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text('QUOTED_VAR="value with spaces"\n')

        # Clean up
        os.environ.pop("QUOTED_VAR", None)

        result = load_env_file(project_path=tmp_path)

        assert result is True
        # python-dotenv removes quotes
        assert os.getenv("QUOTED_VAR") == "value with spaces"

        # Cleanup
        os.environ.pop("QUOTED_VAR", None)
