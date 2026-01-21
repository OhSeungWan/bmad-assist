"""Tests for get_original_cwd() function in core/io.py."""

from pathlib import Path

import pytest

from bmad_assist.core.io import BMAD_ORIGINAL_CWD_ENV, get_original_cwd


class TestGetOriginalCwd:
    """Tests for get_original_cwd() function."""

    def test_returns_path_from_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When BMAD_ORIGINAL_CWD is set, returns that path."""
        test_path = "/some/original/path"
        monkeypatch.setenv(BMAD_ORIGINAL_CWD_ENV, test_path)

        result = get_original_cwd()

        assert result == Path(test_path)

    def test_returns_cwd_when_env_var_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When BMAD_ORIGINAL_CWD is not set, returns current working directory."""
        monkeypatch.delenv(BMAD_ORIGINAL_CWD_ENV, raising=False)

        result = get_original_cwd()

        assert result == Path.cwd()

    def test_returns_cwd_when_env_var_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When BMAD_ORIGINAL_CWD is empty string, returns current working directory."""
        monkeypatch.setenv(BMAD_ORIGINAL_CWD_ENV, "")

        result = get_original_cwd()

        # Empty string is falsy, so should fall back to cwd()
        assert result == Path.cwd()

    def test_env_var_name_is_correct(self) -> None:
        """Verify the env var name constant is as expected."""
        assert BMAD_ORIGINAL_CWD_ENV == "BMAD_ORIGINAL_CWD"
