"""Retry handler with exponential backoff for LLM calls.

This module provides retry logic for transient failures when calling LLM APIs.
It distinguishes between retriable errors (network, rate limit, timeout) and
non-retriable errors (auth, invalid request).
"""

from __future__ import annotations

import logging
import random
from typing import Any

from bmad_assist.core.exceptions import (
    ProviderError,
    ProviderExitCodeError,
    ProviderTimeoutError,
)
from bmad_assist.providers.base import ExitStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Retry Configuration
# =============================================================================

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0
DEFAULT_MAX_DELAY_SECONDS = 30.0
DEFAULT_JITTER_FACTOR = 0.2  # 0-20% jitter

# Exit statuses that warrant a retry
# Based on AC-2: Retry on RATE_LIMIT, SERVER_ERROR, UNAVAILABLE, TIMEOUT
RETRIABLE_STATUSES: set[ExitStatus] = {
    ExitStatus.ERROR,  # General error (includes 5xx server errors)
}

# Error patterns indicating transient failures (case-insensitive)
TRANSIENT_ERROR_PATTERNS: tuple[str, ...] = (
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
)


# =============================================================================
# Retry Handler
# =============================================================================


class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay_seconds: Initial delay between retries.
        max_delay_seconds: Maximum delay between retries (cap).
        jitter_factor: Random jitter factor (0.0-1.0).

    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
        max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS,
        jitter_factor: float = DEFAULT_JITTER_FACTOR,
    ):
        """Initialize the retry configuration."""
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.jitter_factor = jitter_factor

    def __repr__(self) -> str:
        """Return a string representation of the retry configuration."""
        return (
            f"RetryConfig(retries={self.max_retries}, "
            f"base_delay={self.base_delay_seconds}s, "
            f"max_delay={self.max_delay_seconds}s, "
            f"jitter={self.jitter_factor})"
        )


class RetryHandler:
    """Handler for retry logic with exponential backoff.

    This class determines whether errors are retriable and calculates
    backoff delays with jitter.

    Example:
        >>> handler = RetryHandler(RetryConfig(max_retries=3))
        >>> if handler.should_retry(timeout_error):
        ...     delay = handler.calculate_backoff(attempt=1)
        ...     print(f"Retrying in {delay:.2f}s")

    """

    def __init__(self, config: RetryConfig | None = None):
        """Initialize retry handler.

        Args:
            config: Retry configuration. Uses defaults if None.

        """
        self.config = config or RetryConfig()

    def should_retry(self, error: Exception) -> bool:
        """Determine if an error warrants a retry.

        Retriable errors:
        - ProviderTimeoutError
        - ProviderExitCodeError with retriable status
        - ProviderError with transient patterns in message
        - ConnectionError, TimeoutError

        Non-retriable errors:
        - Auth errors (401, 403)
        - Invalid request (400, 422)
        - Content policy violations

        Args:
            error: The exception that occurred.

        Returns:
            True if the error is retriable, False otherwise.

        """
        # Always retry on timeout
        if isinstance(error, ProviderTimeoutError):
            logger.debug("Retry: ProviderTimeoutError detected")
            return True

        # Retry on specific exit codes
        if isinstance(error, ProviderExitCodeError):
            should_retry = error.exit_status in RETRIABLE_STATUSES
            logger.debug(
                "Retry: ProviderExitCodeError with exit_status=%s, retriable=%s",
                error.exit_status,
                should_retry,
            )
            return should_retry

        # Check for transient patterns in any ProviderError
        if isinstance(error, ProviderError):
            error_str = str(error).lower()
            for pattern in TRANSIENT_ERROR_PATTERNS:
                if pattern in error_str:
                    logger.debug("Retry: Transient pattern '%s' found in error", pattern)
                    return True
            logger.debug("Retry: ProviderError does not match transient patterns")
            return False

        # Network-level errors are retriable
        if isinstance(error, (ConnectionError, TimeoutError)):
            logger.debug("Retry: Network error detected")
            return True

        # All other errors are not retriable
        logger.debug("Retry: Error type %s is not retriable", type(error).__name__)
        return False

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay with exponential increase and jitter.

        Formula: min(base_delay * 2^attempt, max_delay) * (1 + random(0, jitter_factor))

        Args:
            attempt: Zero-based attempt number (0 = first retry after initial failure).

        Returns:
            Delay in seconds.

        Example:
            >>> handler = RetryHandler(RetryConfig(base_delay_seconds=1.0, max_delay_seconds=30.0))
            >>> handler.calculate_backoff(0)  # First retry: ~1.0-1.2s
            >>> handler.calculate_backoff(1)  # Second retry: ~2.0-2.4s
            >>> handler.calculate_backoff(2)  # Third retry: ~4.0-4.8s

        """
        # Exponential increase: base_delay * 2^attempt
        exponential_delay = self.config.base_delay_seconds * (2**attempt)

        # Cap at max_delay
        capped_delay = min(exponential_delay, self.config.max_delay_seconds)

        # Add jitter: random factor between 0 and jitter_factor
        jitter: float = random.uniform(0, self.config.jitter_factor)
        final_delay: float = capped_delay * (1 + jitter)

        logger.debug(
            "Backoff calculation: attempt=%d, exponential=%.2f, capped=%.2f, jitter=%.2f, final=%.2f",
            attempt,
            exponential_delay,
            capped_delay,
            jitter,
            final_delay,
        )

        return final_delay

    def get_retry_context(self, attempt: int, error: Exception) -> dict[str, Any]:
        """Get context for logging retry attempts.

        Args:
            attempt: Current attempt number (0-based).
            error: The error that triggered the retry.

        Returns:
            Dictionary with retry context information.

        """
        return {
            "attempt": attempt + 1,
            "max_attempts": self.config.max_retries + 1,
            "error_type": type(error).__name__,
            "error_message": str(error)[:200],  # Truncate long messages
            "backoff_seconds": self.calculate_backoff(attempt),
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def is_retriable_error(error: Exception) -> bool:
    """Quick check if an error is retriable.

    Args:
        error: The exception to check.

    Returns:
        True if the error is retriable.

    Example:
        >>> try:
        ...     result = provider.invoke(prompt)
        ... except ProviderError as e:
        ...     if is_retriable_error(e):
        ...         retry_count += 1

    """
    handler = RetryHandler()
    return handler.should_retry(error)


def calculate_retry_delay(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: float = DEFAULT_MAX_DELAY_SECONDS,
    jitter: float = DEFAULT_JITTER_FACTOR,
) -> float:
    """Calculate retry delay without creating a RetryHandler.

    Args:
        attempt: Zero-based attempt number.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        jitter: Jitter factor (0.0-1.0).

    Returns:
        Delay in seconds.

    """
    config = RetryConfig(
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        jitter_factor=jitter,
    )
    handler = RetryHandler(config)
    return handler.calculate_backoff(attempt)
