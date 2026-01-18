"""Tests for sharding security module."""

from __future__ import annotations

from pathlib import Path

import pytest

from bmad_assist.bmad.sharding.security import (
    DuplicateEpicError,
    SecurityError,
    validate_sharded_path,
)
from bmad_assist.core.exceptions import BmadAssistError


class TestSecurityError:
    """Tests for SecurityError exception."""

    def test_inherits_from_bmad_assist_error(self) -> None:
        """SecurityError should inherit from BmadAssistError."""
        assert issubclass(SecurityError, BmadAssistError)

    def test_can_be_raised_and_caught(self) -> None:
        """SecurityError can be raised and caught."""
        with pytest.raises(SecurityError, match="test message"):
            raise SecurityError("test message")


class TestDuplicateEpicError:
    """Tests for DuplicateEpicError exception."""

    def test_inherits_from_bmad_assist_error(self) -> None:
        """DuplicateEpicError should inherit from BmadAssistError."""
        assert issubclass(DuplicateEpicError, BmadAssistError)

    def test_can_be_raised_and_caught(self) -> None:
        """DuplicateEpicError can be raised and caught."""
        with pytest.raises(DuplicateEpicError, match="duplicate"):
            raise DuplicateEpicError("duplicate epic_id 1")


class TestValidateShardedPath:
    """Tests for validate_sharded_path function."""

    def test_valid_path_within_base(self, tmp_path: Path) -> None:
        """Valid path within base directory returns True."""
        file_path = tmp_path / "docs" / "epics" / "epic-1.md"
        file_path.parent.mkdir(parents=True)
        file_path.touch()

        result = validate_sharded_path(tmp_path, file_path)
        assert result is True

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Path traversal attempts raise SecurityError."""
        base = tmp_path / "docs"
        base.mkdir()
        malicious_path = base / ".." / ".." / "etc" / "passwd"

        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_sharded_path(base, malicious_path)

    def test_path_outside_base_rejected(self, tmp_path: Path) -> None:
        """Paths outside base directory raise SecurityError."""
        base = tmp_path / "docs" / "epics"
        base.mkdir(parents=True)
        outside = tmp_path / "other" / "file.md"
        outside.parent.mkdir(parents=True)
        outside.touch()

        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_sharded_path(base, outside)

    def test_base_path_itself_is_valid(self, tmp_path: Path) -> None:
        """Base path itself is considered valid."""
        base = tmp_path / "docs"
        base.mkdir()

        result = validate_sharded_path(base, base)
        assert result is True

    def test_nested_valid_path(self, tmp_path: Path) -> None:
        """Deeply nested path within base is valid."""
        base = tmp_path / "docs"
        nested = base / "epics" / "v1" / "chapter" / "epic-1.md"
        nested.parent.mkdir(parents=True)
        nested.touch()

        result = validate_sharded_path(base, nested)
        assert result is True

    def test_symlink_escape_rejected(self, tmp_path: Path) -> None:
        """Symlinks pointing outside base are rejected."""
        base = tmp_path / "docs"
        base.mkdir()
        outside = tmp_path / "outside" / "secret.md"
        outside.parent.mkdir(parents=True)
        outside.touch()

        # Create symlink inside base pointing outside
        symlink = base / "escape.md"
        symlink.symlink_to(outside)

        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_sharded_path(base, symlink)

    def test_relative_path_resolved(self, tmp_path: Path) -> None:
        """Relative paths are properly resolved."""
        base = tmp_path / "docs"
        (base / "epics").mkdir(parents=True)
        file_path = base / "epics" / ".." / "epics" / "epic-1.md"
        (base / "epics" / "epic-1.md").touch()

        result = validate_sharded_path(base, file_path)
        assert result is True

    def test_double_dot_normalized(self, tmp_path: Path) -> None:
        """Multiple .. are properly normalized and validated."""
        base = tmp_path / "docs" / "epics"
        base.mkdir(parents=True)
        # Path stays within base after normalization
        safe_path = base / "subdir" / ".." / "epic-1.md"
        (base / "subdir").mkdir()
        (base / "epic-1.md").touch()

        result = validate_sharded_path(base, safe_path)
        assert result is True
