"""Exceptions for Deep Verify module.

This module provides the exception hierarchy for the Deep Verify module,
including specialized exceptions for input validation, resource limits,
and domain detection errors.
"""

from __future__ import annotations

import asyncio
from enum import Enum

from bmad_assist.core.exceptions import BmadAssistError


class DeepVerifyError(BmadAssistError):
    """Base exception for Deep Verify module.

    All Deep Verify specific exceptions inherit from this class.
    """

    pass


class InputValidationError(DeepVerifyError):
    """Input validation error.

    Raised when:
    - Artifact size exceeds maximum limit
    - Line count exceeds maximum limit
    - Input format is invalid

    Attributes:
        size_bytes: Size of the artifact in bytes (if applicable).
        line_count: Number of lines in the artifact (if applicable).
        limit: The limit that was exceeded.

    """

    def __init__(
        self,
        message: str,
        size_bytes: int | None = None,
        line_count: int | None = None,
        limit: int | None = None,
    ) -> None:
        """Initialize InputValidationError with context.

        Args:
            message: Human-readable error message.
            size_bytes: Size of the artifact in bytes.
            line_count: Number of lines in the artifact.
            limit: The limit that was exceeded.

        """
        super().__init__(message)
        self.size_bytes = size_bytes
        self.line_count = line_count
        self.limit = limit


class ResourceLimitError(DeepVerifyError):
    """Resource limit exceeded error.

    Raised when:
    - Number of findings per method exceeds limit
    - Total number of findings exceeds limit
    - Regex execution times out
    - Memory limits are exceeded

    Attributes:
        resource_type: Type of resource that hit the limit.
        current_value: Current value that exceeded the limit.
        limit: The limit that was exceeded.

    """

    def __init__(
        self,
        message: str,
        resource_type: str,
        current_value: int,
        limit: int,
    ) -> None:
        """Initialize ResourceLimitError with context.

        Args:
            message: Human-readable error message.
            resource_type: Type of resource (e.g., "findings_per_method").
            current_value: Current value that exceeded the limit.
            limit: The limit that was exceeded.

        """
        super().__init__(message)
        self.resource_type = resource_type
        self.current_value = current_value
        self.limit = limit


class DomainDetectionError(DeepVerifyError):
    """Domain detection failure error.

    Raised when:
    - LLM-based domain detection fails
    - JSON parsing of domain detection response fails
    - Domain detection returns ambiguous results

    Attributes:
        fallback_reason: Reason for using fallback detection.
        original_error: The original exception that caused the failure.

    """

    def __init__(
        self,
        message: str,
        fallback_reason: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize DomainDetectionError with context.

        Args:
            message: Human-readable error message.
            fallback_reason: Reason for using fallback detection.
            original_error: The original exception that caused the failure.

        """
        super().__init__(message)
        self.fallback_reason = fallback_reason
        self.original_error = original_error


# =============================================================================
# Error Categorization
# =============================================================================


class ErrorCategory(str, Enum):
    """Error categories for classification.

    Categories determine retry behavior and error handling:
    - RETRYABLE_TRANSIENT: Temporary issues that may resolve on retry
    - RETRYABLE_TIMEOUT: Timeout errors that may succeed on retry
    - FATAL_AUTH: Authentication/authorization failures (don't retry)
    - FATAL_INVALID: Invalid requests or configuration (don't retry)
    - FATAL_UNKNOWN: Uncategorized fatal errors (don't retry)
    """

    RETRYABLE_TRANSIENT = "retryable_transient"
    RETRYABLE_TIMEOUT = "retryable_timeout"
    FATAL_AUTH = "fatal_auth"
    FATAL_INVALID = "fatal_invalid"
    FATAL_UNKNOWN = "fatal_unknown"


class CategorizedError:
    """Categorized error with metadata.

    Attributes:
        error: The original exception.
        category: The error category.
        method_id: The method ID where the error occurred (if applicable).
        is_fatal: Whether this is a fatal error (non-retriable).
        message: Human-readable error message.

    """

    def __init__(
        self,
        error: Exception,
        category: ErrorCategory,
        method_id: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize CategorizedError.

        Args:
            error: The original exception.
            category: The error category.
            method_id: The method ID where the error occurred.
            message: Human-readable error message (defaults to str(error)).

        """
        self.error = error
        self.category = category
        self.method_id = method_id
        self.is_fatal = category in (
            ErrorCategory.FATAL_AUTH,
            ErrorCategory.FATAL_INVALID,
            ErrorCategory.FATAL_UNKNOWN,
        )
        self.message = message or str(error)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"CategorizedError("
            f"category={self.category.value!r}, "
            f"method_id={self.method_id!r}, "
            f"is_fatal={self.is_fatal}, "
            f"message={self.message[:50]!r}...)"
        )


class ErrorCategorizer:
    """Categorizes exceptions for error handling.

    This class maps exceptions to ErrorCategory values, determining
    whether errors are retriable and how they should be handled.

    Example:
        >>> categorizer = ErrorCategorizer()
        >>> try:
        ...     result = provider.invoke(prompt)
        ... except ProviderError as e:
        ...     categorized = categorizer.classify(e, method_id="#153")
        ...     if categorized.is_fatal:
        ...         print(f"Fatal error: {categorized.message}")
        ...     else:
        ...         print(f"Retryable error: {categorized.message}")

    """

    def __init__(self) -> None:
        """Initialize the error categorizer."""
        # Import here to avoid circular imports
        from bmad_assist.core.exceptions import (
            ProviderError,
            ProviderExitCodeError,
            ProviderTimeoutError,
        )
        from bmad_assist.providers.base import ExitStatus

        self._ProviderError = ProviderError
        self._ProviderExitCodeError = ProviderExitCodeError
        self._ProviderTimeoutError = ProviderTimeoutError
        self._ExitStatus = ExitStatus

    def classify(
        self,
        error: Exception,
        method_id: str | None = None,
    ) -> CategorizedError:
        """Classify an exception into an ErrorCategory.

        Args:
            error: The exception to classify.
            method_id: Optional method ID for context.

        Returns:
            CategorizedError with category and metadata.

        """
        category = self._determine_category(error)
        return CategorizedError(
            error=error,
            category=category,
            method_id=method_id,
        )

    def _determine_category(self, error: Exception) -> ErrorCategory:
        """Determine the category for an exception.

        Args:
            error: The exception to categorize.

        Returns:
            The appropriate ErrorCategory.

        """
        # Timeout errors are retryable
        if isinstance(error, self._ProviderTimeoutError):
            return ErrorCategory.RETRYABLE_TIMEOUT

        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return ErrorCategory.RETRYABLE_TIMEOUT

        # Exit code errors - check specific codes
        if isinstance(error, self._ProviderExitCodeError):
            return self._categorize_exit_code(error)

        # Provider errors - check message content for transient patterns
        if isinstance(error, self._ProviderError):
            return self._categorize_provider_error(error)

        # Pattern library errors are fatal (configuration issues)
        if isinstance(error, ImportError) and "pattern" in str(error).lower():
            return ErrorCategory.FATAL_INVALID

        # Regex errors are fatal (invalid patterns)
        import re

        if isinstance(error, re.error):
            return ErrorCategory.FATAL_INVALID

        # Deep Verify specific errors
        if isinstance(error, InputValidationError):
            return ErrorCategory.FATAL_INVALID

        if isinstance(error, ResourceLimitError):
            return ErrorCategory.FATAL_INVALID

        # Domain detection errors are retryable (can use fallback)
        if isinstance(error, DomainDetectionError):
            return ErrorCategory.RETRYABLE_TRANSIENT

        # Unknown errors are fatal by default
        return ErrorCategory.FATAL_UNKNOWN

    def _categorize_exit_code(self, error: Exception) -> ErrorCategory:
        """Categorize based on exit code.

        Args:
            error: The ProviderExitCodeError to categorize.

        Returns:
            The appropriate ErrorCategory.

        """
        exit_code = getattr(error, "exit_code", None)
        if exit_code is None:
            return ErrorCategory.FATAL_UNKNOWN

        # Rate limit (429) - retryable
        if exit_code == 429:
            return ErrorCategory.RETRYABLE_TRANSIENT

        # Server errors (500, 502, 503, 504) - retryable
        if exit_code in (500, 502, 503, 504):
            return ErrorCategory.RETRYABLE_TRANSIENT

        # Auth errors (401, 403) - fatal
        if exit_code in (401, 403):
            return ErrorCategory.FATAL_AUTH

        # Bad request (400) - fatal
        if exit_code == 400:
            return ErrorCategory.FATAL_INVALID

        # Not found (404) - fatal
        if exit_code == 404:
            return ErrorCategory.FATAL_INVALID

        # Check exit status if available
        if hasattr(error, "exit_status"):
            status = error.exit_status
            if status == self._ExitStatus.ERROR:
                return ErrorCategory.RETRYABLE_TRANSIENT

        # Default: treat as fatal
        return ErrorCategory.FATAL_UNKNOWN

    def _categorize_provider_error(self, error: Exception) -> ErrorCategory:
        """Categorize based on ProviderError message content.

        Args:
            error: The ProviderError to categorize.

        Returns:
            The appropriate ErrorCategory.

        """
        error_str = str(error).lower()

        # Transient error patterns
        transient_patterns = [
            "rate limit",
            "429",
            "503",
            "502",
            "504",
            "service unavailable",
            "temporarily unavailable",
            "timeout",
            "timed out",
            "connection reset",
            "connection refused",
            "connection error",
            "network error",
            "internal server error",
            "500",
        ]

        for pattern in transient_patterns:
            if pattern in error_str:
                return ErrorCategory.RETRYABLE_TRANSIENT

        # Auth patterns
        auth_patterns = [
            "unauthorized",
            "forbidden",
            "authentication",
            "invalid api key",
            "invalid token",
        ]

        for pattern in auth_patterns:
            if pattern in error_str:
                return ErrorCategory.FATAL_AUTH

        # Invalid request patterns
        invalid_patterns = [
            "bad request",
            "invalid request",
            "validation error",
            "malformed",
        ]

        for pattern in invalid_patterns:
            if pattern in error_str:
                return ErrorCategory.FATAL_INVALID

        # Default: unknown
        return ErrorCategory.FATAL_UNKNOWN
