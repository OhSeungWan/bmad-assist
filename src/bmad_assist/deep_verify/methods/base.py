"""Base class for all Deep Verify verification methods.

This module defines the abstract base class that all verification methods
(Pattern Match, Boundary Analysis, Assumption Surfacing, etc.) must implement.

The ABC pattern ensures consistent interfaces across all methods while allowing
for method-specific implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bmad_assist.deep_verify.core.types import Finding, MethodId


class BaseVerificationMethod(ABC):
    """Abstract base class for Deep Verify verification methods.

    All verification methods (Pattern Match #153, Boundary Analysis #154, etc.)
    must inherit from this class and implement the analyze() method.

    Attributes:
        method_id: Unique method identifier (e.g., "#153", "#154").

    Example:
        >>> class PatternMatchMethod(BaseVerificationMethod):
        ...     method_id = MethodId("#153")
        ...
        ...     async def analyze(
        ...         self,
        ...         artifact_text: str,
        ...         **kwargs: dict[str, object]
        ...     ) -> list[Finding]:
        ...         # Method-specific implementation
        ...         return findings

    """

    method_id: MethodId

    @abstractmethod
    async def analyze(
        self,
        artifact_text: str,
        **kwargs: dict[str, object],
    ) -> list[Finding]:
        """Analyze artifact text and return findings.

        Args:
            artifact_text: The text content to analyze.
            **kwargs: Additional context including:
                - domains: Optional list of ArtifactDomain to filter patterns
                - config: Optional DeepVerifyConfig for method configuration
                - context: Optional additional context for analysis

        Returns:
            List of Finding objects with method-prefixed temporary IDs.
            The DeepVerifyEngine will reassign final sequential IDs (F1, F2, ...).

        Raises:
            Exception: Method implementations should handle their own errors
                gracefully and return empty list on failure.

        """
        ...

    def __repr__(self) -> str:
        """Return a string representation of the method."""
        method_id = getattr(self, "method_id", "unknown")
        return f"{self.__class__.__name__}(method_id={method_id!r})"
