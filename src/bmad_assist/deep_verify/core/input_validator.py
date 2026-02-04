"""Input validation for Deep Verify.

This module provides input validation for artifacts being verified,
including size limits and line count limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bmad_assist.deep_verify.config import ResourceLimitConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of input validation.

    Attributes:
        is_valid: Whether the input passed validation.
        error_message: Error message if validation failed, None otherwise.
        size_bytes: Size of the artifact in bytes.
        line_count: Number of lines in the artifact.

    """

    is_valid: bool
    error_message: str | None
    size_bytes: int
    line_count: int

    def __repr__(self) -> str:
        """Return string representation."""
        if self.is_valid:
            return f"ValidationResult(valid, size={self.size_bytes}B, lines={self.line_count})"
        return (
            f"ValidationResult(invalid: {self.error_message}, "
            f"size={self.size_bytes}B, lines={self.line_count})"
        )


class InputValidator:
    """Validates artifact input against resource limits.

    This class checks artifact size and line count against configured
    limits to prevent OOM and performance issues.

    Attributes:
        _config: Resource limit configuration.

    Example:
        >>> from bmad_assist.deep_verify.config import ResourceLimitConfig
        >>> config = ResourceLimitConfig(
        ...     max_artifact_size_bytes=102400,
        ...     max_line_count=5000,
        ... )
        >>> validator = InputValidator(config)
        >>> result = validator.validate("def test(): pass")
        >>> print(result.is_valid)
        True

    """

    def __init__(self, config: ResourceLimitConfig) -> None:
        """Initialize the input validator.

        Args:
            config: Resource limit configuration with size and line limits.

        """
        self._config = config

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"InputValidator("
            f"max_size={self._config.max_artifact_size_bytes}B, "
            f"max_lines={self._config.max_line_count})"
        )

    def validate(self, text: str) -> ValidationResult:
        r"""Validate artifact text against resource limits.

        Checks:
        1. Artifact size in bytes (must be <= max_artifact_size_bytes)
        2. Line count (must be <= max_line_count)

        Args:
            text: The artifact text to validate.

        Returns:
            ValidationResult with is_valid flag and metrics.

        Example:
            >>> result = validator.validate("def test():\n    pass")
            >>> result.is_valid
            True
            >>> result.size_bytes
            17
            >>> result.line_count
            2

        """
        # Calculate metrics
        size_bytes = len(text.encode("utf-8"))
        line_count = text.count("\n") + 1 if text else 0

        # Check size limit
        if size_bytes > self._config.max_artifact_size_bytes:
            error_msg = (
                f"Artifact size {size_bytes} bytes exceeds limit "
                f"{self._config.max_artifact_size_bytes} bytes "
                f"({self._config.max_artifact_size_bytes / 1024:.0f}KB)"
            )
            logger.warning(
                "Input validation failed: size %d > limit %d",
                size_bytes,
                self._config.max_artifact_size_bytes,
            )
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                size_bytes=size_bytes,
                line_count=line_count,
            )

        # Check line count limit
        if line_count > self._config.max_line_count:
            error_msg = (
                f"Artifact line count {line_count} exceeds limit {self._config.max_line_count}"
            )
            logger.warning(
                "Input validation failed: lines %d > limit %d",
                line_count,
                self._config.max_line_count,
            )
            return ValidationResult(
                is_valid=False,
                error_message=error_msg,
                size_bytes=size_bytes,
                line_count=line_count,
            )

        # Validation passed
        logger.debug(
            "Input validation passed: size=%d bytes, lines=%d",
            size_bytes,
            line_count,
        )
        return ValidationResult(
            is_valid=True,
            error_message=None,
            size_bytes=size_bytes,
            line_count=line_count,
        )

    def get_limits(self) -> dict[str, int]:
        """Get current validation limits.

        Returns:
            Dictionary with limit names and values.

        """
        return {
            "max_artifact_size_bytes": self._config.max_artifact_size_bytes,
            "max_line_count": self._config.max_line_count,
        }
