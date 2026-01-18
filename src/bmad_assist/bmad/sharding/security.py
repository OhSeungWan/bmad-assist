"""Security utilities for sharded documentation loading.

This module provides path validation to prevent directory traversal attacks
when loading files from sharded documentation directories.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bmad_assist.core.exceptions import BmadAssistError

logger = logging.getLogger(__name__)


class SecurityError(BmadAssistError):
    """Security violation in sharded documentation loading.

    Raised when:
    - Path traversal is detected (e.g., ../../../etc/passwd)
    - File path escapes project boundary
    - Symlink leads outside allowed directory
    """

    pass


class DuplicateEpicError(BmadAssistError):
    """Duplicate epic ID detected in sharded directory.

    Raised when multiple files in a sharded epics directory
    have the same epic_id in their frontmatter.
    """

    pass


def validate_sharded_path(base_path: Path, file_path: Path) -> bool:
    """Validate that file_path is within base_path boundary.

    Resolves both paths to absolute paths and verifies that file_path
    is contained within base_path. This prevents directory traversal
    attacks via relative paths like '../../../etc/passwd'.

    Args:
        base_path: Project docs directory (boundary).
        file_path: Path to validate.

    Returns:
        True if path is safe.

    Raises:
        SecurityError: If path traversal detected.

    Examples:
        >>> validate_sharded_path(Path("/docs"), Path("/docs/epics/epic-1.md"))
        True
        >>> validate_sharded_path(Path("/docs"), Path("/docs/../../../etc/passwd"))
        SecurityError: Path traversal detected

    """
    try:
        resolved_base = base_path.resolve()
        resolved_file = file_path.resolve()

        if not resolved_file.is_relative_to(resolved_base):
            logger.error(
                "SECURITY: Path traversal detected - %s escapes %s",
                file_path,
                base_path,
            )
            raise SecurityError(f"Path traversal detected: {file_path}")

        return True
    except OSError as e:
        # Handle cases where path resolution fails (broken symlinks, etc.)
        logger.error("SECURITY: Path resolution failed for %s: %s", file_path, e)
        raise SecurityError(f"Path resolution failed: {file_path}") from e
