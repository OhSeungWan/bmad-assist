"""Testarch module for Test Architect integration.

This module provides ATDD (Acceptance Test Driven Development) capabilities
for the bmad-assist development loop.

Note:
    ATDDHandler is NOT imported here to avoid circular imports.
    Import directly: `from bmad_assist.testarch.handlers import ATDDHandler`

"""

from bmad_assist.testarch.config import (
    EligibilityConfig,
    PreflightConfig,
    TestarchConfig,
)
from bmad_assist.testarch.eligibility import (
    API_KEYWORDS,
    SKIP_KEYWORDS,
    UI_KEYWORDS,
    ATDDEligibilityDetector,
    ATDDEligibilityResult,
    KeywordScorer,
)
from bmad_assist.testarch.preflight import (
    PreflightChecker,
    PreflightResult,
    PreflightStatus,
)

__all__ = [
    "EligibilityConfig",
    "PreflightConfig",
    "TestarchConfig",
    "KeywordScorer",
    "UI_KEYWORDS",
    "API_KEYWORDS",
    "SKIP_KEYWORDS",
    "ATDDEligibilityResult",
    "ATDDEligibilityDetector",
    "PreflightChecker",
    "PreflightResult",
    "PreflightStatus",
]
